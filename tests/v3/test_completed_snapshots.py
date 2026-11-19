import base64
import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from test_fixture_policy_loader import signed

from v3.offline.calendar_completion import (
    ClockDenied,
    DataVerdict,
    ReplayClock,
    assess_snapshot,
)
from v3.offline.data_intake_schema import load_snapshot_fixture

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/stage_a/a2"


def record():
    return json.loads((FIXTURE / "payload.json").read_text())


def load(value=None):
    return load_snapshot_fixture(
        *signed(
            policy=record() if value is None else value,
            manifest_updates={"max_bytes": 65536, "max_nodes": 256},
        )
    )


def assess(value=None):
    snapshot = load(value)
    return assess_snapshot(snapshot, snapshot.binding, ReplayClock(snapshot.clock.at))


def test_authenticated_snapshot_completion_and_lineage_are_not_entry_permission():
    public = json.loads((ROOT / "evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json").read_text())
    snapshot = load_snapshot_fixture(
        (FIXTURE / "payload.json").read_bytes(),
        (FIXTURE / "manifest.json").read_bytes(),
        bytes.fromhex((FIXTURE / "manifest.sig").read_text()),
        bytes.fromhex(public["public_key_hex"]),
    )
    result = assess_snapshot(snapshot, snapshot.binding, ReplayClock(snapshot.clock.at))
    assert result.verdict is DataVerdict.COMPLETED_FIXTURE_ONLY
    assert (
        result.lineage.snapshot_sha256
        == hashlib.sha256((FIXTURE / "payload.json").read_bytes()).hexdigest()
    )
    assert result.lineage.feature_row_sha256 == "3" * 64
    assert result.lineage.feature_schema_sha256 == snapshot.binding.feature_schema_sha256
    assert result == assess_snapshot(snapshot, snapshot.binding, ReplayClock(snapshot.clock.at))
    assert not hasattr(result, "entry_permit")
    with pytest.raises(FrozenInstanceError):
        result.verdict = DataVerdict.UNKNOWN_DENY


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "REAL_MARKET_DATA"),
        ("account_id", "REAL_ACCOUNT"),
        ("currency", "usd"),
        ("policy_sha256", "bad"),
        ("feature_schema_sha256", 1),
        ("timezone_tzif_base64", "!"),
        ("timezone_tzif_base64", "VFp"),
        ("timezone_tzif_base64", base64.b64encode(b"X" * 44).decode()),
        ("timezone_tzif_base64", base64.b64encode(b"TZif" + b"x" * 16384).decode()),
        ("session_open", "2027-03-15T08:00:00"),
        ("bar", []),
        ("interval_seconds", True),
        ("max_age_seconds", "60"),
        ("extra", True),
    ],
)
def test_bad_signed_snapshot_schema_never_becomes_a_data_result(field, value):
    with pytest.raises(ValueError):
        load(record() | {field: value})


def test_missing_root_fields_and_boolean_completion_are_denied():
    value = record()
    del value["source_id"]
    with pytest.raises(ValueError):
        load(value)
    value = record()
    value["bar"]["complete"] = 1
    with pytest.raises(ValueError):
        load(value)


@pytest.mark.parametrize("price", ["0", "-1", "NaN", "1e2", "1.1234567890123", 1, True])
def test_prices_are_finite_positive_fixed_point_not_float_or_implicit(price):
    value = record()
    value["bar"]["price"] = price
    with pytest.raises(ValueError):
        load(value)


@pytest.mark.parametrize(
    "field",
    [
        "run_id",
        "account_id",
        "instrument_id",
        "source_id",
        "source_version",
        "price_unit",
        "currency",
        "timezone_version",
    ],
)
def test_cross_run_instrument_source_policy_and_unit_swaps_deny(field):
    snapshot = load()
    changed = replace(snapshot.binding, **{field: "WRONG"})
    assert (
        assess_snapshot(snapshot, changed, ReplayClock(snapshot.clock.at)).verdict
        is DataVerdict.INVALID_DENY
    )


@pytest.mark.parametrize("field", ["bar", "max_age_seconds", "max_publication_delay_seconds"])
def test_missing_bar_or_selected_policy_is_unknown_not_prior_close(field):
    value = record() | {field: None}
    result = assess(value)
    assert result.verdict is DataVerdict.UNKNOWN_DENY
    assert "MISSING" in result.reason
    assert not hasattr(result, "price")


def test_missing_price_does_not_impute_zero_or_prior_close():
    value = record()
    value["bar"]["price"] = None
    assert assess(value).verdict is DataVerdict.UNKNOWN_DENY


@pytest.mark.parametrize("quality", ["EXPECTED_STALE", "FAILED", "UNKNOWN"])
def test_expected_stale_and_failed_source_are_distinct_but_neither_is_success(quality):
    result = assess(record() | {"source_quality": quality})
    assert result.verdict is DataVerdict.UNKNOWN_DENY
    assert result.reason == "SOURCE_" + quality
    with pytest.raises(ValueError):
        load(record() | {"source_quality": "NEUTRAL"})


@pytest.mark.parametrize(
    "field", ["interval_seconds", "max_age_seconds", "max_publication_delay_seconds"]
)
def test_oversized_signed_time_quantities_deny_instead_of_overflowing(field):
    assert assess(record() | {field: 10**100}).verdict is DataVerdict.INVALID_DENY


@pytest.mark.parametrize(
    "field,value",
    [
        ("interval_seconds", 0),
        ("max_age_seconds", -1),
        ("max_publication_delay_seconds", -1),
        ("session_open", "2027-03-15T13:00:00Z"),
        ("session_close", "2027-03-15T11:59:59Z"),
    ],
)
def test_invalid_or_closed_session_cannot_be_fresh(field, value):
    assert assess(record() | {field: value}).verdict is DataVerdict.INVALID_DENY


def test_bar_outside_session_and_wrong_lineage_deny():
    value = record()
    value["bar"]["start"] = "2027-03-15T07:55:00Z"
    assert assess(value).verdict is DataVerdict.INVALID_DENY
    for field in ("bar_start", "bar_end"):
        assert (
            assess(record() | {field: "2027-03-15T11:59:00Z"}).verdict is DataVerdict.INVALID_DENY
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"complete": False},
        {"end": "2027-03-15T11:55:00Z"},
        {"start": "2027-03-15T11:54:00Z"},
        {"end": "2027-03-15T12:05:00Z"},
    ],
)
def test_forming_wrong_interval_or_prior_bar_cannot_substitute(changes):
    value = record()
    value["bar"].update(changes)
    assert assess(value).verdict is DataVerdict.INVALID_DENY


@pytest.mark.parametrize(
    "field,value",
    [
        ("published_at", "2027-03-15T11:59:59Z"),
        ("published_at", "2027-03-15T12:00:06Z"),
        ("observed_at", "2027-03-15T12:00:06Z"),
        ("vintage_available_at", "2027-03-15T12:00:06Z"),
        ("revision_available_at", "2027-03-15T12:00:06Z"),
    ],
)
def test_post_decision_or_pre_completion_evidence_is_not_available(field, value):
    data = record()
    data["bar"][field] = value
    assert assess(data).verdict is DataVerdict.UNKNOWN_DENY


def test_exact_age_and_publication_boundaries_are_inclusive_not_mtime_based():
    value = record() | {"max_age_seconds": 5, "max_publication_delay_seconds": 2}
    assert assess(value).verdict is DataVerdict.COMPLETED_FIXTURE_ONLY
    assert assess(value | {"max_age_seconds": 4}).verdict is DataVerdict.UNKNOWN_DENY
    assert assess(value | {"max_publication_delay_seconds": 1}).verdict is DataVerdict.UNKNOWN_DENY


def test_future_completed_bar_is_still_denied():
    value = record()
    value["clock"]["at"] = "2027-03-15T11:59:59Z"
    assert assess(value).verdict is DataVerdict.INVALID_DENY


def daily_record(
    start="2027-03-15T00:00:00Z",
    end="2027-03-15T22:00:00Z",
    local_close="2027-03-15T22:00:00+0000",
    age=300,
):
    value = record()
    opened, closed = datetime.fromisoformat(start), datetime.fromisoformat(end)
    value.update(
        session_open=start,
        session_close=end,
        expected_close=end,
        expected_local_close=local_close,
        bar_start=start,
        bar_end=end,
        interval_seconds=int((closed - opened).total_seconds()),
        max_age_seconds=600,
    )
    value["bar"].update(
        start=start,
        end=end,
        published_at=end,
        observed_at=end,
        vintage_available_at=end,
        revision_available_at=end,
    )
    value["clock"]["at"] = (closed + timedelta(seconds=age)).isoformat()
    return value


@pytest.mark.parametrize("age", [0, 1, 300, 600])
def test_daily_bar_at_session_close_is_available_after_close_within_max_age(age):
    result = assess(daily_record(age=age))
    assert result.verdict is DataVerdict.COMPLETED_FIXTURE_ONLY
    assert result.reason == "ALL_REQUIRED_FIXTURE_DATA_PROVEN"
    assert not hasattr(result, "entry_permit")


def test_daily_bar_denies_before_close_and_when_stale_or_still_forming():
    before = assess(daily_record(age=-1))
    assert before.verdict is DataVerdict.INVALID_DENY
    assert before.reason == "FORMING_WRONG_BAR_OR_DST_ALIGNMENT"
    stale = assess(daily_record(age=601))
    assert stale.verdict is DataVerdict.UNKNOWN_DENY
    assert stale.reason == "UNAVAILABLE_STALE_OR_LATE_PUBLICATION"
    forming = daily_record()
    forming["bar"]["complete"] = False
    assert assess(forming).verdict is DataVerdict.INVALID_DENY


@pytest.mark.parametrize(
    "field", ["published_at", "observed_at", "vintage_available_at", "revision_available_at"]
)
def test_post_close_decision_still_requires_each_publication_and_vintage(field):
    value = daily_record()
    value["bar"][field] = "2027-03-15T22:05:01Z"
    assert assess(value).verdict is DataVerdict.UNKNOWN_DENY


@pytest.mark.parametrize(
    "start,end,local_close,seconds",
    [
        ("2027-03-28T00:00:00Z", "2027-03-28T23:00:00Z", "2027-03-29T00:00:00+0100", 82800),
        ("2027-10-30T23:00:00Z", "2027-11-01T00:00:00Z", "2027-11-01T00:00:00+0000", 90000),
    ],
)
def test_daily_post_close_dst_uses_signed_local_close_and_actual_utc_duration(
    start, end, local_close, seconds
):
    value = daily_record(start, end, local_close)
    assert value["interval_seconds"] == seconds
    assert assess(value).verdict is DataVerdict.COMPLETED_FIXTURE_ONLY
    value["expected_local_close"] = local_close[:-5] + (
        "+0000" if local_close.endswith("+0100") else "+0100"
    )
    assert assess(value).verdict is DataVerdict.INVALID_DENY


@pytest.mark.parametrize(
    "invalid",
    [
        {"domain": "REAL_BROKER"},
        {"source_clock_id": "OTHER"},
        {"evidence_sha256": ""},
        {"monotonic_ns": -1},
        {"skew_bound_microseconds": -1},
        {"at": datetime(2027, 3, 15, 11, 59, tzinfo=UTC)},
    ],
)
def test_event_clock_rejects_untrusted_domains_or_rewind(invalid):
    clock = load().clock
    with pytest.raises(ClockDenied):
        clock.elapsed_to(replace(clock, **invalid))


def test_event_clock_uses_its_own_domain_and_does_not_make_synthetic_proof_real():
    clock = load().clock
    assert clock.elapsed_to(clock) == 0
    later = replace(
        clock, at=clock.at + timedelta(seconds=1), monotonic_ns=clock.monotonic_ns + 1_000_000_000
    )
    assert clock.elapsed_to(later) == 1_000_000_000
    with pytest.raises(ClockDenied):
        clock.elapsed_to(replace(later, monotonic_ns=later.monotonic_ns + 1))
    assert (
        clock.elapsed_to(
            replace(later, monotonic_ns=later.monotonic_ns + 1000, skew_bound_microseconds=1)
        )
        == 1_000_001_000
    )
    with pytest.raises(ClockDenied):
        replace(clock, domain="UNKNOWN").elapsed_to(clock)
    with pytest.raises(ClockDenied):
        replace(clock, evidence_sha256="").elapsed_to(clock)
    with pytest.raises(ClockDenied):
        replace(clock, monotonic_ns=-1).elapsed_to(clock)
    with pytest.raises(ClockDenied):
        replace(clock, skew_bound_microseconds=-1).elapsed_to(clock)
    with pytest.raises(ClockDenied):
        clock.elapsed_to(replace(clock, monotonic_ns=clock.monotonic_ns - 1))


def test_invalid_clock_replay_or_calendar_evidence_returns_explicit_data_denial():
    snapshot = load()
    replay = ReplayClock(snapshot.clock.at)
    assert (
        assess_snapshot(
            snapshot, snapshot.binding, replay.advance(replay.at + timedelta(seconds=1))
        ).verdict
        is DataVerdict.INVALID_DENY
    )
    assert (
        assess_snapshot(
            replace(snapshot, clock=replace(snapshot.clock, domain="UNKNOWN")),
            snapshot.binding,
            replay,
        ).verdict
        is DataVerdict.INVALID_DENY
    )
    assert (
        assess_snapshot(
            replace(snapshot, calendar=replace(snapshot.calendar, tzif=b"invalid")),
            snapshot.binding,
            replay,
        ).verdict
        is DataVerdict.INVALID_DENY
    )


@pytest.mark.parametrize(
    "zone,date,offset",
    [
        ("Europe/London", "2027-03-15", "+0000"),
        ("America/New_York", "2027-03-15", "-0400"),
        ("Europe/London", "2027-11-01", "+0000"),
        ("America/New_York", "2027-11-01", "-0400"),
        ("Europe/Berlin", "2027-03-29", "+0200"),
    ],
)
def test_signed_iana_dst_mismatch_windows_from_g1r_06_b(zone, date, offset):
    source = json.loads((ROOT / "fixtures/stage_a/calendar_sources/payload.json").read_text())
    value = copy.deepcopy(record())
    value["timezone"] = zone
    value["timezone_tzif_base64"] = source["tzif_by_name"][zone]
    for field in ("session_open", "session_close", "expected_close", "bar_start", "bar_end"):
        value[field] = date + value[field][10:]
    for field in (
        "start",
        "end",
        "published_at",
        "observed_at",
        "vintage_available_at",
        "revision_available_at",
    ):
        value["bar"][field] = date + value["bar"][field][10:]
    value["clock"]["at"] = date + value["clock"]["at"][10:]
    hours = {"+0000": "12", "-0400": "08", "+0200": "14"}
    value["expected_local_close"] = date + "T" + hours[offset] + ":00:00" + offset
    assert assess(value).verdict is DataVerdict.COMPLETED_FIXTURE_ONLY
    value["expected_local_close"] = date + "T12:00:00+9999"
    assert assess(value).verdict is DataVerdict.INVALID_DENY


def test_dst_fold_requires_explicit_utc_and_correct_offset_not_ambiguous_wall_time():
    value = record()
    value["bar"]["end"] = "2027-10-31T01:30:00"
    with pytest.raises(ValueError):
        load(value)


@pytest.mark.parametrize("hour,offset", [(0, "+0100"), (1, "+0000")])
def test_both_london_fall_back_occurrences_have_distinct_utc_proof(hour, offset):
    value = record()
    end = datetime(2027, 10, 31, hour, 30, tzinfo=UTC)
    start = end - timedelta(minutes=5)
    value.update(
        session_open="2027-10-31T00:00:00Z",
        session_close="2027-10-31T04:00:00Z",
        expected_close=end.isoformat(),
        expected_local_close="2027-10-31T01:30:00" + offset,
        bar_start=start.isoformat(),
        bar_end=end.isoformat(),
    )
    value["bar"].update(
        start=start.isoformat(),
        end=end.isoformat(),
        published_at=(end + timedelta(seconds=2)).isoformat(),
        observed_at=(end + timedelta(seconds=4)).isoformat(),
        vintage_available_at=(end + timedelta(seconds=2)).isoformat(),
        revision_available_at=(end + timedelta(seconds=2)).isoformat(),
    )
    value["clock"]["at"] = (end + timedelta(seconds=5)).isoformat()
    assert assess(value).verdict is DataVerdict.COMPLETED_FIXTURE_ONLY
    value["expected_local_close"] = "2027-10-31T01:30:00" + ("+0000" if hour == 0 else "+0100")
    assert assess(value).verdict is DataVerdict.INVALID_DENY


@given(st.integers(min_value=6, max_value=10000))
def test_all_ages_above_signed_threshold_deny_without_fallback(age):
    value = record() | {"max_age_seconds": 5}
    value["clock"]["at"] = (
        datetime(2027, 3, 15, 12, tzinfo=UTC) + timedelta(seconds=age)
    ).isoformat()
    assert assess(value).verdict is DataVerdict.UNKNOWN_DENY
