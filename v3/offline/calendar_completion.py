"""Pure fixture-clock primitives for original unit 06 / SourceSnapshotLoader.

Only stdlib deterministic calculations over authenticated fixture evidence are
allowed. There is no wall clock, filesystem, network or operational timer authority.
TZif bytes come from a signed, version-pinned calendar, never a host timezone lookup.
Completion, publication, revision and session predicates cannot reuse a prior close.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from io import BytesIO
from struct import error as StructError
from zoneinfo import ZoneInfo


class ClockDenied(ValueError):
    """Report invalid UTC evidence or clock reversal; never substitute wall time."""


def require_utc(value: datetime) -> datetime:
    """Return an aware zero-offset instant unchanged, or raise ClockDenied; no effects."""
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ClockDenied("An explicit UTC instant is required")
    return value


def parse_utc(value: str) -> datetime:
    """Parse an explicit UTC ISO-8601 fixture timestamp; raise ClockDenied on failure."""
    try:
        instant = datetime.fromisoformat(value)
    except ValueError as error:
        raise ClockDenied("Invalid ISO-8601 fixture timestamp") from error
    return require_utc(instant).astimezone(UTC)


@dataclass(frozen=True)
class ReplayClock:
    """An immutable UTC simulator instant, not an operational D1-D3/E1-E3 timer."""

    at: datetime

    def __post_init__(self) -> None:
        """Reject absent/ambiguous timezone evidence before the clock can be used."""
        require_utc(self.at)

    def advance(self, to: datetime) -> "ReplayClock":
        """Return a clock at a nondecreasing UTC instant; raise ClockDenied on rewind."""
        require_utc(to)
        if to < self.at:
            raise ClockDenied("Replay clock cannot move backwards")
        return ReplayClock(to)


@dataclass(frozen=True)
class VerifiedEventClock:
    """Signed synthetic event time; monotonic nanoseconds compare within one domain only."""

    at: datetime
    monotonic_ns: int
    domain: str
    source_clock_id: str
    skew_bound_microseconds: int
    evidence_sha256: str

    def elapsed_to(self, other: "VerifiedEventClock") -> int:
        """Return elapsed ns or raise ClockDenied for rewind, skew or untrusted domains."""
        require_utc(self.at)
        require_utc(other.at)
        if (
            self.domain != "SIMULATED_REPLAY"
            or other.domain != self.domain
            or other.source_clock_id != self.source_clock_id
            or not self.evidence_sha256
            or not other.evidence_sha256
            or self.monotonic_ns < 0
            or other.monotonic_ns < self.monotonic_ns
            or self.skew_bound_microseconds < 0
            or other.skew_bound_microseconds < 0
            or other.at < self.at
        ):
            raise ClockDenied("Unproven clock domain or non-monotonic event evidence")
        delta = other.monotonic_ns - self.monotonic_ns
        utc_delta = (other.at - self.at) // timedelta(microseconds=1)
        if (
            abs(delta - utc_delta * 1000)
            > (self.skew_bound_microseconds + other.skew_bound_microseconds) * 1000
        ):
            raise ClockDenied("UTC and monotonic evidence exceed the signed skew bound")
        return delta


@dataclass(frozen=True)
class SnapshotBinding:
    """Exact source/run/policy/price identity expected by the fixture consumer."""

    run_id: str
    account_id: str
    instrument_id: str
    source_id: str
    source_version: str
    policy_sha256: str
    feature_schema_sha256: str
    price_unit: str
    currency: str
    timezone: str
    timezone_version: str


@dataclass(frozen=True)
class CompletedBar:
    """One explicitly supplied source bar; fixed-point price is not an executable quote."""

    start: datetime
    end: datetime
    price: Decimal | None
    complete: bool
    published_at: datetime
    observed_at: datetime
    vintage_available_at: datetime
    revision_available_at: datetime


@dataclass(frozen=True)
class CalendarPolicy:
    """Signed synthetic UTC session/window, IANA TZif and finite freshness thresholds."""

    tzif: bytes
    session_open: datetime
    session_close: datetime
    expected_close: datetime
    expected_local_close: str
    interval_seconds: int
    max_age_seconds: int | None
    max_publication_delay_seconds: int | None


@dataclass(frozen=True)
class FeatureLineage:
    """Pre-outcome source/snapshot/bar/feature fingerprints, never a model prediction."""

    snapshot_id: str
    source_event_id: str
    snapshot_sha256: str
    feature_row_sha256: str
    feature_schema_sha256: str
    bar_start: datetime
    bar_end: datetime


@dataclass(frozen=True)
class SignedSnapshot:
    """Typed authenticated snapshot and provenance; absence remains explicitly absent."""

    binding: SnapshotBinding
    calendar: CalendarPolicy
    clock: VerifiedEventClock
    lineage: FeatureLineage
    bar: CompletedBar | None
    manifest_sha256: str
    signer_sha256: str
    quality: "InputQuality"


class InputQuality(StrEnum):
    """Source-declared availability; an expected closure is not a successful input."""

    COMPLETE = "COMPLETE"
    EXPECTED_STALE = "EXPECTED_STALE"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class DataVerdict(StrEnum):
    """Fixture data assessment only; no member represents entry or broker permission."""

    COMPLETED_FIXTURE_ONLY = "COMPLETED_FIXTURE_ONLY"
    UNKNOWN_DENY = "UNKNOWN_DENY"
    INVALID_DENY = "INVALID_DENY"


@dataclass(frozen=True)
class DataAssessment:
    """Explicit assessment and reason bound to the exact snapshot and feature lineage."""

    verdict: DataVerdict
    reason: str
    lineage: FeatureLineage


def assess_snapshot(
    snapshot: SignedSnapshot, expected: SnapshotBinding, replay: ReplayClock
) -> DataAssessment:
    """Check PIT completion/session evidence without effects or fallback; return denial."""
    calendar, bar = snapshot.calendar, snapshot.bar

    def result(verdict: DataVerdict, reason: str) -> DataAssessment:
        return DataAssessment(verdict, reason, snapshot.lineage)

    if snapshot.binding != expected:
        return result(DataVerdict.INVALID_DENY, "SOURCE_RUN_POLICY_OR_UNIT_MISMATCH")
    if snapshot.quality is not InputQuality.COMPLETE:
        return result(DataVerdict.UNKNOWN_DENY, "SOURCE_" + snapshot.quality)
    try:
        snapshot.clock.elapsed_to(snapshot.clock)
        if snapshot.clock.at != replay.at:
            raise ClockDenied("Event/replay clock mismatch")
        zone = ZoneInfo.from_file(BytesIO(calendar.tzif), key=expected.timezone)
    except (ClockDenied, ValueError, StructError, EOFError) as error:
        return result(DataVerdict.INVALID_DENY, f"CLOCK_OR_CALENDAR:{error}")
    if (
        calendar.max_age_seconds is None
        or calendar.max_publication_delay_seconds is None
        or bar is None
        or bar.price is None
    ):
        return result(DataVerdict.UNKNOWN_DENY, "MISSING_BAR_PRICE_OR_SELECTED_POLICY")
    if (
        calendar.interval_seconds <= 0
        or calendar.interval_seconds > timedelta.max.days * 86400
        or calendar.max_age_seconds < 0
        or calendar.max_age_seconds > timedelta.max.days * 86400
        or calendar.max_publication_delay_seconds < 0
        or calendar.max_publication_delay_seconds > timedelta.max.days * 86400
        or not calendar.session_open <= replay.at < calendar.session_close
        or not calendar.session_open <= bar.start < bar.end <= calendar.session_close
    ):
        return result(DataVerdict.INVALID_DENY, "INVALID_OR_CLOSED_SESSION")
    if (
        not bar.complete
        or bar.end != calendar.expected_close
        or bar.end - bar.start != timedelta(seconds=calendar.interval_seconds)
        or bar.end > replay.at
        or calendar.expected_close.astimezone(zone).strftime("%Y-%m-%dT%H:%M:%S%z")
        != calendar.expected_local_close
        or snapshot.lineage.bar_start != bar.start
        or snapshot.lineage.bar_end != bar.end
    ):
        return result(DataVerdict.INVALID_DENY, "FORMING_WRONG_BAR_OR_DST_ALIGNMENT")
    if (
        not bar.end <= bar.published_at <= bar.observed_at <= replay.at
        or not bar.end <= bar.vintage_available_at <= replay.at
        or not bar.end <= bar.revision_available_at <= replay.at
        or replay.at - bar.end > timedelta(seconds=calendar.max_age_seconds)
        or bar.published_at - bar.end > timedelta(seconds=calendar.max_publication_delay_seconds)
    ):
        return result(DataVerdict.UNKNOWN_DENY, "UNAVAILABLE_STALE_OR_LATE_PUBLICATION")
    return result(DataVerdict.COMPLETED_FIXTURE_ONLY, "ALL_REQUIRED_FIXTURE_DATA_PROVEN")
