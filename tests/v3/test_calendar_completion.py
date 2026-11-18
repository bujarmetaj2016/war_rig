from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest

from v3.offline.calendar_completion import ClockDenied, ReplayClock, parse_utc, require_utc

NOW = datetime(2026, 11, 18, 12, tzinfo=UTC)


def test_utc_clock_is_immutable_monotonic_and_replayable() -> None:
    clock = ReplayClock(NOW)
    assert clock.advance(NOW) == clock
    later = clock.advance(NOW + timedelta(seconds=1))
    assert later.at == NOW + timedelta(seconds=1)
    assert clock.at == NOW
    with pytest.raises(FrozenInstanceError):
        clock.at = later.at
    with pytest.raises(ClockDenied, match="backwards"):
        later.advance(NOW)


@pytest.mark.parametrize(
    "instant",
    [NOW.replace(tzinfo=None), NOW.astimezone(timezone(timedelta(hours=1)))],
)
def test_invalid_utc_never_becomes_a_clock(instant: datetime) -> None:
    for action in (require_utc, ReplayClock, ReplayClock(NOW).advance):
        with pytest.raises(ClockDenied, match="explicit UTC"):
            action(instant)


@pytest.mark.parametrize("text", ["2026-11-18T12:00:00Z", "2026-11-18T12:00:00+00:00"])
def test_parse_normalizes_explicit_utc(text: str) -> None:
    assert parse_utc(text) == NOW
    assert parse_utc(text).tzinfo is UTC


@pytest.mark.parametrize("text", ["not-a-time", "", "2026-99-99", "2026-11-18T12:00:60Z"])
def test_bad_timestamp_is_explicit_denial(text: str) -> None:
    with pytest.raises(ClockDenied, match="Invalid ISO"):
        parse_utc(text)


@pytest.mark.parametrize("text", ["2026-11-18", "2026-11-18T12:00", "2026-11-18T12:00+01:00"])
def test_naive_or_non_utc_timestamp_is_not_reinterpreted(text: str) -> None:
    with pytest.raises(ClockDenied, match="explicit UTC"):
        parse_utc(text)
