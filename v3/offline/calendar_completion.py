"""Pure fixture-clock primitives for original unit 06 / SourceSnapshotLoader.

Only standard-library datetime/dataclass imports are allowed here. Caller-supplied
UTC instants are the trust boundary: no wall clock, I/O, timer or broker authority.
Clock progression is immutable, monotonic and replay-idempotent. Completed-bar,
source calendar and market-session predicates remain separate, unfinished Stage A work.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


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
