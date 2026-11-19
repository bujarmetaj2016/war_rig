"""EXT-03 adopted USD/event observations only; no entry, risk, exit or gate API.

REV4 Part 4 and OWNER_DECISION_20261117 §1/3/4 govern signs and role.
Signed fixture history is the sole input; missing/stale/PIT-unproven stays UNKNOWN.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import stdev

from v3.offline.calendar_completion import require_utc
from v3.offline.data_intake_schema import digest, object_fields, utc
from v3.offline.fixture_policy_loader import JsonValue, _identity, _integer
from v3.offline.offline_scenario_runner import (
    PredictionDenied,
    SignalScore,
    canonical,
    number,
    signed_record,
)

PAIRS = ("USDJPY", "GBPUSD", "USDCAD", "USDCHF", "AUDUSD", "EURUSD")
INVERTED = frozenset({"GBPUSD", "AUDUSD", "EURUSD"})
EVENTS = frozenset({"FOMC", "ECB", "BOE", "US_CPI", "US_NFP"})
INSTRUMENTS = frozenset({"XAUUSD", "GER40", "US500", "EURUSD", "GBPUSD"})


@dataclass(frozen=True)
class MacroObservation:
    """Immutable pre-outcome telemetry, deliberately without any decision/authority field."""

    instrument: str
    direction: str
    entry_at: datetime
    source_sha256: str
    snapshot_sha256: str
    basket: str
    basket_s: Decimal | None
    basket_sigma: Decimal | None
    basket_reason: str
    event_proximity: str
    event_reason: str
    role: str = "COMPUTE_AND_LOG_ONLY"

    @property
    def encoded(self) -> bytes:
        """Return deterministic attach/log bytes before any outcome exists."""
        from dataclasses import asdict

        return canonical(asdict(self))


@dataclass(frozen=True)
class ObservedPrediction:
    """Attach telemetry alongside, never inside, the immutable prediction decision."""

    prediction: SignalScore
    observation: MacroObservation


def _list(value: JsonValue) -> list[JsonValue]:
    if not isinstance(value, list):
        raise PredictionDenied("Explicit macro list required")
    return value


def _basket(
    series: JsonValue,
    expected_closes: tuple[datetime, ...],
    instrument: str,
    direction: str,
    entry: datetime,
    freshness: int | None,
) -> tuple[str, Decimal | None, Decimal | None, str]:
    if instrument not in ("EURUSD", "GBPUSD"):
        return "UNKNOWN", None, None, "NOT_ADOPTED_FOR_THIS_INSTRUMENT"
    if series is None:
        return "UNKNOWN", None, None, "MISSING_BASKET_HISTORY"
    if not isinstance(series, dict) or set(series) - set(PAIRS):
        raise PredictionDenied("Unapproved macro basket leg")
    legs = tuple(pair for pair in PAIRS if pair != instrument)
    if freshness is None:
        return "UNKNOWN", None, None, "FRESHNESS_POLICY_UNSELECTED"
    if not expected_closes:
        return "UNKNOWN", None, None, "EXPECTED_CLOSE_CALENDAR_UNAVAILABLE"
    histories: list[tuple[Decimal, ...]] = []
    for pair in legs:
        if pair not in series:
            return "UNKNOWN", None, None, "MISSING_LEG:" + pair
        history = []
        closes = []
        for value in _list(series[pair]):
            record = object_fields(value, {"close_at", "available_at", "vintage_at", "value"})
            if any(record[field] is None for field in ("close_at", "available_at", "vintage_at")):
                return "UNKNOWN", None, None, "MISSING_OR_PIT_UNPROVEN:" + pair
            close, available, vintage = (
                utc(record["close_at"]),
                utc(record["available_at"]),
                utc(record["vintage_at"]),
            )
            if (
                record["value"] is None
                or not close <= available < entry
                or not vintage <= available
                or vintage.date() >= entry.date()
                or close.date() >= entry.date()
            ):
                return "UNKNOWN", None, None, "MISSING_OR_PIT_UNPROVEN:" + pair
            price = number(record["value"])
            if price <= 0:
                raise PredictionDenied("Nonpositive macro close")
            closes.append(close)
            history.append(price)
        if tuple(closes) != expected_closes or len(history) < 260:
            return "UNKNOWN", None, None, "INCOMPLETE_OR_MISMATCHED_CALENDAR:" + pair
        if entry - closes[-1] > timedelta(seconds=freshness):
            return "UNKNOWN", None, None, "STALE_LEG:" + pair
        returns = tuple(
            (right / left).ln() * (-1 if pair in INVERTED else 1)
            for left, right in zip(history, history[1:], strict=False)
        )
        histories.append(returns)
    daily = tuple(sum(values) / len(legs) for values in zip(*histories, strict=True))
    changes = tuple(sum(daily[i - 9 : i + 1]) for i in range(9, len(daily)))[-250:]
    current, sigma = changes[-1], stdev(changes)
    if current > sigma / 2:
        classification = "WITH" if direction == "BEARISH" else "AGAINST"
    elif current < -sigma / 2:
        classification = "WITH" if direction == "BULLISH" else "AGAINST"
    else:
        classification = "NEUTRAL"
    return classification, current, sigma, "PIT_COMPLETE_REV4_SAMPLE_STD_DDOF1"


def _events(
    events: JsonValue,
    schedules: JsonValue,
    entry: datetime,
    freshness: int | None,
) -> tuple[str, str]:
    if events is None or schedules is None:
        return "UNKNOWN", "MISSING_PRE_ENTRY_EVENT_OR_SCHEDULE_EVIDENCE"
    verified = {}
    seen = set()
    for value in _list(schedules):
        schedule = object_fields(
            value, {"event_type", "published_at", "coverage_start", "coverage_end", "source_sha256"}
        )
        kind = _identity(schedule["event_type"])
        if kind not in EVENTS or kind in seen:
            raise PredictionDenied("Unapproved/duplicate event schedule")
        seen.add(kind)
        if any(
            schedule[field] is None
            for field in (
                "published_at",
                "coverage_start",
                "coverage_end",
                "source_sha256",
            )
        ):
            continue
        digest(schedule["source_sha256"])
        published = utc(schedule["published_at"])
        start, end = utc(schedule["coverage_start"]), utc(schedule["coverage_end"])
        if end <= start:
            raise PredictionDenied("Invalid schedule coverage")
        if (
            published.date() < entry.date()
            and published < entry
            and freshness is not None
            and entry - published <= timedelta(seconds=freshness)
        ):
            verified[kind] = (start, end)
    uncertain_timing = False
    for value in _list(events):
        event = object_fields(value, {"event_type", "scheduled_at"})
        kind = _identity(event["event_type"])
        if kind not in EVENTS:
            raise PredictionDenied("Unapproved macro event")
        scheduled = None if event["scheduled_at"] is None else utc(event["scheduled_at"])
        if scheduled is None:
            uncertain_timing = True
        if (
            kind in verified
            and scheduled is not None
            and verified[kind][0] <= scheduled <= verified[kind][1]
            and timedelta(0) < scheduled - entry <= timedelta(hours=24)
        ):
            return "EVENT_WINDOW", "PROVEN_PRE_ENTRY_OFFICIAL_SCHEDULE_FIXTURE"
    if (
        not uncertain_timing
        and set(verified) == EVENTS
        and all(
            start <= entry and end >= entry + timedelta(hours=24)
            for start, end in verified.values()
        )
    ):
        return "NO_EVENT", "COMPLETE_FIVE_SCHEDULE_PIT_COVERAGE"
    return "UNKNOWN", "INCOMPLETE_OR_STALE_PRE_ENTRY_SCHEDULE_COVERAGE"


def compute_macro_observation(
    payload: bytes,
    manifest: bytes,
    signature: bytes,
    key: bytes,
    *,
    instrument: str,
    direction: str,
    entry_at: datetime,
    snapshot_sha256: str,
) -> MacroObservation:
    """Compute only adopted signed PIT telemetry; no outcomes, inference or mutation."""
    require_utc(entry_at)
    record = object_fields(
        signed_record(payload, manifest, signature, key),
        {
            "kind",
            "instrument",
            "direction",
            "entry_at",
            "snapshot_sha256",
            "expected_closes",
            "series",
            "events",
            "schedules",
            "freshness_seconds",
        },
    )
    if (
        record["kind"] != "SIGNED_MACRO_OBSERVATIONS_V1"
        or instrument not in INSTRUMENTS
        or direction not in ("BULLISH", "BEARISH")
        or record["instrument"] != instrument
        or record["direction"] != direction
        or utc(record["entry_at"]) != entry_at
        or digest(record["snapshot_sha256"]) != snapshot_sha256
    ):
        raise PredictionDenied("Macro run/instrument/side/snapshot binding mismatch")
    freshness = (
        None if record["freshness_seconds"] is None else _integer(record["freshness_seconds"])
    )
    if freshness is not None and not 0 < freshness <= 31536000:
        raise PredictionDenied("Invalid signed macro freshness policy")
    closes = (
        ()
        if record["expected_closes"] is None
        else tuple(utc(value) for value in _list(record["expected_closes"]))
    )
    if any(left >= right for left, right in zip(closes, closes[1:], strict=False)):
        raise PredictionDenied("Duplicated/nonmonotonic expected daily calendar")
    basket, current, sigma, reason = _basket(
        record["series"], closes, instrument, direction, entry_at, freshness
    )
    event, event_reason = _events(record["events"], record["schedules"], entry_at, freshness)
    return MacroObservation(
        instrument,
        direction,
        entry_at,
        hashlib.sha256(payload).hexdigest(),
        snapshot_sha256,
        basket,
        current,
        sigma,
        reason,
        event,
        event_reason,
    )


def attach_observation(score: SignalScore, observation: MacroObservation) -> ObservedPrediction:
    """Bind telemetry without recomputing or touching the prediction, grade or risk cap."""
    if (
        score.snapshot_sha256 != observation.snapshot_sha256
        or score.direction != observation.direction
        or score.instrument != observation.instrument
        or score.created_at != observation.entry_at
    ):
        raise PredictionDenied("Cannot attach observations to a different prediction")
    return ObservedPrediction(score, observation)
