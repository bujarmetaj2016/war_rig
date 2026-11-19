import copy
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal

import pytest
from test_fixture_policy_loader import signed
from test_prediction_pipeline import load_feature, pipeline, signal

from v3.offline.macro_features import (
    EVENTS,
    INVERTED,
    PAIRS,
    PredictionDenied,
    attach_observation,
    compute_macro_observation,
)


def macro_body(*, instrument="EURUSD", trend=0):
    row = load_feature(instrument=instrument)
    entry = row.available_at
    closes = [
        entry.replace(hour=18, minute=0, second=0, microsecond=0) - timedelta(days=260 - i)
        for i in range(260)
    ]
    series = {}
    for pair in PAIRS:
        if pair == instrument:
            continue
        prices = []
        for i, close in enumerate(closes):
            change = Decimal("1.001") ** (i * trend)
            price = Decimal(100) / change if pair in INVERTED else Decimal(100) * change
            prices.append(
                {
                    "close_at": str(close),
                    "available_at": str(close + timedelta(minutes=1)),
                    "vintage_at": str(close),
                    "value": str(price.quantize(Decimal("0.00000001"))),
                }
            )
        series[pair] = prices
    schedules = [
        {
            "event_type": kind,
            "published_at": str(entry - timedelta(days=2)),
            "coverage_start": str(entry - timedelta(days=7)),
            "coverage_end": str(entry + timedelta(days=7)),
            "source_sha256": "1" * 64,
        }
        for kind in sorted(EVENTS)
    ]
    return {
        "kind": "SIGNED_MACRO_OBSERVATIONS_V1",
        "instrument": instrument,
        "direction": "BULLISH",
        "entry_at": str(entry),
        "snapshot_sha256": row.snapshot_sha256,
        "expected_closes": list(map(str, closes)),
        "series": series,
        "events": [],
        "schedules": schedules,
        "freshness_seconds": 86400 * 3,
    }, row


def observe(body, row):
    return compute_macro_observation(
        *signed(
            policy=body,
            manifest_updates={"max_bytes": 1048576, "max_nodes": 10000, "max_depth": 12},
        ),
        instrument=row.context.instrument.value,
        direction=body["direction"],
        entry_at=row.available_at,
        snapshot_sha256=row.snapshot_sha256,
    )


@pytest.mark.parametrize("instrument", ["EURUSD", "GBPUSD"])
@pytest.mark.parametrize(
    "trend,bullish,bearish",
    [(1, "AGAINST", "WITH"), (-1, "WITH", "AGAINST"), (0, "NEUTRAL", "NEUTRAL")],
)
def test_ex_own_currency_equal_weight_signs_and_sample_std(instrument, trend, bullish, bearish):
    body, row = macro_body(instrument=instrument, trend=trend)
    result = observe(body, row)
    assert result.basket == bullish
    assert result.basket_sigma >= 0
    assert result.basket_reason == "PIT_COMPLETE_REV4_SAMPLE_STD_DDOF1"
    assert result.event_proximity == "NO_EVENT"
    assert result.encoded == observe(body, row).encoded
    body["direction"] = "BEARISH"
    assert observe(body, row).basket == bearish
    # Excluded leg is never consumed, even if unusable. Role stays observational.
    body["series"][instrument] = [{"value": "NaN"}]
    assert observe(body, row).basket == bearish
    assert result.role == "COMPUTE_AND_LOG_ONLY"
    with pytest.raises(FrozenInstanceError):
        result.basket = "WITH"


@pytest.mark.parametrize("instrument", ["XAUUSD", "GER40", "US500"])
def test_baskets_not_silently_adopted_for_other_three_instruments(instrument):
    body, row = macro_body(instrument=instrument)
    assert observe(body, row).basket_reason == "NOT_ADOPTED_FOR_THIS_INSTRUMENT"


@pytest.mark.parametrize(
    "change,reason",
    [
        ("missing", "MISSING_LEG"),
        ("short", "INCOMPLETE_OR_MISMATCHED"),
        ("calendar", "INCOMPLETE_OR_MISMATCHED"),
        ("stale", "STALE_LEG"),
        ("unselected", "FRESHNESS_POLICY_UNSELECTED"),
        ("null", "MISSING_OR_PIT_UNPROVEN"),
        ("same_day", "MISSING_OR_PIT_UNPROVEN"),
        ("future", "MISSING_OR_PIT_UNPROVEN"),
    ],
)
def test_unknown_is_not_a_neutral_or_success_fallback(change, reason):
    body, row = macro_body()
    leg = body["series"]["USDJPY"]
    if change == "missing":
        del body["series"]["USDJPY"]
    elif change == "short":
        body["series"]["USDJPY"] = leg[:-1]
    elif change == "calendar":
        leg[0]["close_at"] = str(row.available_at - timedelta(days=300))
    elif change == "stale":
        body["freshness_seconds"] = 1
    elif change == "unselected":
        body["freshness_seconds"] = None
    elif change == "null":
        leg[0]["value"] = None
    elif change == "same_day":
        leg[0]["vintage_at"] = str(row.available_at)
    else:
        leg[0]["available_at"] = str(row.available_at + timedelta(days=1))
    result = observe(body, row)
    assert result.basket == "UNKNOWN" and result.basket_s is None
    assert result.basket_reason.startswith(reason)


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "LIVE"),
        ("instrument", "OTHER"),
        ("direction", "NONE"),
        ("snapshot_sha256", "9" * 64),
        ("entry_at", "2020-01-01T00:00:00Z"),
        ("expected_closes", "yesterday"),
        ("series", {}),
        ("freshness_seconds", 0),
        ("freshness_seconds", 31536001),
        ("freshness_seconds", True),
    ],
)
def test_invalid_macro_schema_and_binding_explicitly_deny(field, value):
    body, row = macro_body()
    body[field] = value
    if field == "series":
        assert observe(body, row).basket == "UNKNOWN"
    else:
        with pytest.raises(ValueError):
            observe(body, row)


def test_unapproved_or_corrupt_series_are_not_consumed():
    body, row = macro_body()
    body["series"]["EVIL"] = []
    with pytest.raises(PredictionDenied):
        observe(body, row)
    body, row = macro_body()
    body["series"]["USDJPY"][0]["value"] = "0"
    with pytest.raises(PredictionDenied):
        observe(body, row)
    body, row = macro_body()
    body["expected_closes"][1] = body["expected_closes"][0]
    with pytest.raises(PredictionDenied):
        observe(body, row)


@pytest.mark.parametrize(
    "hours,result",
    [
        (24, "EVENT_WINDOW"),
        (1, "EVENT_WINDOW"),
        (0, "NO_EVENT"),
        (-1, "NO_EVENT"),
        (25, "NO_EVENT"),
    ],
)
@pytest.mark.parametrize("instrument", ["EURUSD", "GBPUSD", "XAUUSD", "GER40", "US500"])
def test_all_five_instruments_event_window_boundary_is_strictly_before_release(
    instrument, hours, result
):
    body, row = macro_body(instrument=instrument)
    body["events"] = [
        {"event_type": "US_CPI", "scheduled_at": str(row.available_at + timedelta(hours=hours))}
    ]
    assert observe(body, row).event_proximity == result


def test_missing_date_only_stale_same_day_incomplete_and_positive_only_schedule_evidence():
    body, row = macro_body()
    body["events"] = [{"event_type": "FOMC", "scheduled_at": None}]
    assert observe(body, row).event_proximity == "UNKNOWN"
    body["schedules"] = []
    assert observe(body, row).event_proximity == "UNKNOWN"
    original, row = macro_body()
    for change in ("same_day", "stale", "short_coverage"):
        body = copy.deepcopy(original)
        if change == "same_day":
            body["schedules"][0]["published_at"] = str(row.available_at)
        elif change == "stale":
            body["schedules"][0]["published_at"] = str(row.available_at - timedelta(days=4))
        else:
            body["schedules"][0]["coverage_end"] = str(row.available_at)
        assert observe(body, row).event_proximity == "UNKNOWN"
    body = copy.deepcopy(original)
    body["schedules"] = [s for s in body["schedules"] if s["event_type"] == "US_NFP"]
    body["events"] = [
        {"event_type": "US_NFP", "scheduled_at": str(row.available_at + timedelta(hours=1))}
    ]
    assert observe(body, row).event_proximity == "EVENT_WINDOW"


def test_bad_event_kinds_duplicates_and_reversed_coverage_deny():
    body, row = macro_body()
    for kind in ("OTHER",):
        body["events"] = [{"event_type": kind, "scheduled_at": str(row.available_at)}]
        with pytest.raises(PredictionDenied):
            observe(body, row)
    body, row = macro_body()
    body["schedules"] += body["schedules"][:1]
    with pytest.raises(PredictionDenied):
        observe(body, row)
    body, row = macro_body()
    body["schedules"][0]["coverage_end"] = body["schedules"][0]["coverage_start"]
    with pytest.raises(PredictionDenied):
        observe(body, row)


def test_observation_mutations_cannot_change_existing_prediction_decision_or_risk_caps():
    row, source, run, policy = pipeline(instrument="EURUSD")
    score = signal(row, source, run, policy)
    body, macro_row = macro_body()
    observation = observe(body, macro_row)
    # Independent macro source can be attached only after exact side/snapshot binding.
    with pytest.raises(PredictionDenied):
        attach_observation(score, replace(observation, snapshot_sha256="9" * 64))
    bound = observation
    for classification in ("WITH", "AGAINST", "NEUTRAL", "UNKNOWN"):
        changed = replace(bound, basket=classification, event_proximity="EVENT_WINDOW")
        observed = attach_observation(score, changed)
        assert observed.prediction is score
        assert observed.prediction.encoded == score.encoded
        assert observed.prediction.direction == source.direction
        assert not hasattr(observed, "entry_permit")
        assert not hasattr(observed, "stop") and not hasattr(observed, "stake")
        assert not hasattr(changed, "gate") and not hasattr(changed, "size_multiplier")
    with pytest.raises(PredictionDenied):
        attach_observation(score, replace(bound, direction="BEARISH"))


@pytest.mark.parametrize(
    "field", ["published_at", "coverage_start", "coverage_end", "source_sha256"]
)
def test_missing_schedule_evidence_does_not_establish_no_event(field):
    body, row = macro_body()
    body["schedules"][0][field] = None
    assert observe(body, row).event_proximity == "UNKNOWN"


@pytest.mark.parametrize("field", ["close_at", "available_at", "vintage_at"])
def test_missing_observation_timestamps_are_unknown_not_neutral(field):
    body, row = macro_body()
    body["series"]["USDJPY"][0][field] = None
    assert observe(body, row).basket == "UNKNOWN"


@pytest.mark.parametrize("field", ["events", "schedules", "series"])
def test_absent_signed_macro_history_remains_explicitly_unknown(field):
    body, row = macro_body()
    body[field] = None
    result = observe(body, row)
    if field == "series":
        assert result.basket == "UNKNOWN" and result.basket_reason == "MISSING_BASKET_HISTORY"
    else:
        assert result.event_proximity == "UNKNOWN"


@pytest.mark.parametrize("calendar", [None, []])
def test_missing_expected_calendar_cannot_prove_completed_basket_history(calendar):
    body, row = macro_body()
    body["expected_closes"] = calendar
    result = observe(body, row)
    assert result.basket == "UNKNOWN"
    assert result.basket_reason == "EXPECTED_CLOSE_CALENDAR_UNAVAILABLE"


def test_unverified_schedule_cannot_be_silently_superseded_by_duplicate():
    body, row = macro_body()
    body["schedules"].insert(0, body["schedules"][0] | {"published_at": None})
    with pytest.raises(PredictionDenied):
        observe(body, row)
