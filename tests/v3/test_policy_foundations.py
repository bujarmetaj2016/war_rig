import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from test_completed_snapshots import load as snapshot
from test_fixture_policy_loader import signed

from v3.offline.effective_policy import (
    NumericBounds,
    OfflinePermission,
    load_fixture_tiers,
    resolve_fixture_tiers,
)
from v3.offline.intent_identity import (
    Digest,
    EventId,
    Identity,
    InstrumentId,
    MarketId,
    PolicyId,
    PriceUnit,
    ReplayCursor,
    RunContext,
    RunId,
    SimulatedAccountId,
)

ROOT = Path(__file__).resolve().parents[2]
AT = datetime(2027, 3, 15, 12, 0, 5, tzinfo=UTC)


def record():
    return json.loads((ROOT / "fixtures/stage_a/a3/payload.json").read_text())


def load(value=None):
    return load_fixture_tiers(
        *signed(
            policy=record() if value is None else value,
            manifest_updates={"max_nodes": 256},
        )
    )


def context(policy):
    return RunContext(
        RunId("SYNTHETIC_RUN_001"),
        SimulatedAccountId("SIMULATED_ACCOUNT"),
        MarketId("SYNTHETIC_MARKET"),
        InstrumentId("EURUSD"),
        PolicyId("SYNTHETIC_TIER_POLICY"),
        policy.payload_sha256,
        Digest("a" * 64),
        Digest("b" * 64),
        Digest("2" * 64),
        Identity("REPLAY_CLOCK_001"),
        datetime(2027, 1, 1, tzinfo=UTC),
        datetime(2028, 1, 1, tzinfo=UTC),
    )


def resolve(value=None):
    policy = load(value)
    return resolve_fixture_tiers(policy, context(policy), AT)


def test_committed_signed_policy_and_restriction_only_resolution():
    directory = ROOT / "fixtures/stage_a/a3"
    public = json.loads((ROOT / "evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json").read_text())
    policy = load_fixture_tiers(
        (directory / "payload.json").read_bytes(),
        (directory / "manifest.json").read_bytes(),
        bytes.fromhex((directory / "manifest.sig").read_text()),
        bytes.fromhex(public["public_key_hex"]),
    )
    assert (
        policy.payload_sha256.value
        == hashlib.sha256((directory / "payload.json").read_bytes()).hexdigest()
    )
    result = resolve_fixture_tiers(policy, context(policy), AT)
    assert result.permission is OfflinePermission.FIXTURE_ONLY
    assert result.directions == ("BULLISH",)
    assert result.entry_types == ("MARKET",)
    assert result.minimum_rr == (("BULLISH", Decimal("3")),)
    assert not hasattr(result, "send_permit") and not hasattr(result, "eligible")
    with pytest.raises(FrozenInstanceError):
        result.reason = "enable"
    for grant in ("IG", "LIVE", "DEMO", "OWNER_POLICY"):
        with pytest.raises(ValueError):
            OfflinePermission(grant)


@pytest.mark.parametrize("kind", [MarketId, InstrumentId, PolicyId, EventId, RunId, Identity])
def test_typed_ids_are_immutable_distinct_and_bounded(kind):
    assert kind("A") == kind("A")
    assert MarketId("A") != InstrumentId("A")
    with pytest.raises(FrozenInstanceError):
        kind("A").value = "B"
    for invalid in ("", "../escape", "a" * 65, True):
        with pytest.raises(ValueError):
            kind(invalid)


def test_account_hash_units_context_and_replay_foundations():
    with pytest.raises(ValueError):
        SimulatedAccountId("REAL_ACCOUNT")
    for value in ("bad", 42):
        with pytest.raises(ValueError):
            Digest(value)
    unit = PriceUnit(Identity("SOURCE_POINT"), "USD", 5, Decimal("0.00001"))
    assert unit.check(Decimal("1.23456")) == Decimal("1.23456")
    for price in (Decimal("NaN"), Decimal("0"), Decimal("1.234567"), 1.2):
        with pytest.raises(ValueError):
            unit.check(price)
    policy = load()
    run = context(policy)
    assert len(run.sha256) == 64 and run.sha256 == context(policy).sha256
    assert replace(run, instrument=InstrumentId("GBPUSD")).sha256 != run.sha256
    with pytest.raises(ValueError):
        replace(run, valid_until=run.valid_from)
    with pytest.raises(ValueError):
        replace(run, valid_from=run.valid_from.replace(tzinfo=None))
    clock = snapshot().clock
    first = ReplayCursor(Identity("SOURCE_STREAM"), 1, EventId("ONE"), Digest("1" * 64), clock)
    assert first.advance(first) is first
    second = replace(
        first,
        sequence=2,
        event=EventId("TWO"),
        event_sha256=Digest("2" * 64),
        clock=replace(
            clock,
            at=clock.at + timedelta(seconds=1),
            monotonic_ns=clock.monotonic_ns + 1_000_000_000,
        ),
    )
    assert first.advance(second) == second
    for changed in (
        replace(second, stream=Identity("OTHER")),
        replace(second, sequence=3),
        replace(second, event=first.event),
        replace(first, event_sha256=Digest("3" * 64)),
    ):
        with pytest.raises(ValueError):
            first.advance(changed)
    for sequence in (0, True):
        with pytest.raises(ValueError):
            replace(first, sequence=sequence)


@pytest.mark.parametrize(
    "updates",
    [
        {"currency": "usd"},
        {"currency": 1},
        {"precision": True},
        {"precision": 13},
        {"increment": 1.2},
        {"increment": Decimal("NaN")},
        {"increment": Decimal("0")},
        {"increment": Decimal("0.000001")},
    ],
)
def test_invalid_quote_dimensions_never_coerce_or_round(updates):
    with pytest.raises(ValueError):
        PriceUnit(
            **(
                {
                    "name": Identity("POINT"),
                    "currency": "USD",
                    "precision": 5,
                    "increment": Decimal("0.00001"),
                }
                | updates
            )
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"kind": "OWNER_POLICY"},
        {"scope": "LIVE"},
        {"account_id": "REAL_ACCOUNT"},
        {"seed": -1},
        {"seed": True},
        {"extra": True},
        {"directions": []},
        {"directions": "BULLISH"},
        {"directions": ["BULLISH", "BULLISH"]},
        {"rr_bounds": {"lower_exclusive": None, "upper_inclusive": "10"}},
        {"evaluation_budget_seconds": "NaN"},
        {"evaluation_budget_seconds": True},
    ],
)
def test_closed_policy_schema_does_not_infer_defaults(updates):
    with pytest.raises(ValueError):
        load(record() | updates)


def test_t3_cannot_edit_mandatory_checks_protection_or_broker_policy():
    for key in (
        "required_checks",
        "break_even_trigger_pct",
        "trail_atr_multiple",
        "broker",
        "risk_policy",
    ):
        value = record()
        value["t3"][key] = False
        with pytest.raises(ValueError):
            load(value)
    value = record()
    value["t3"]["deny_market_entry"] = 1
    with pytest.raises(ValueError):
        load(value)


@pytest.mark.parametrize(
    "updates",
    [
        {"required_checks": ["SIGNATURE"]},
        {"directions": ["UNRECOGNIZED"]},
        {"entry_types": ["LIMIT"]},
        {"required_strategy_entry_type": "LIMIT"},
        {"rr_bounds": None},
        {"budget_bounds": None},
        {"evaluation_budget_seconds": None},
        {"evaluation_budget_seconds": "0"},
        {"evaluation_budget_seconds": "6"},
    ],
)
def test_t1_and_unselected_or_unsupported_t2_parameters_deny(updates):
    result = resolve(record() | updates)
    assert result.permission is OfflinePermission.DENIED and result.reason
    assert result.minimum_rr == () and result.directions == ()


@pytest.mark.parametrize(
    "updates",
    [
        {"directions": ["BEARISH"], "minimum_rr": {"BULLISH": None, "BEARISH": "3"}},
        {"directions": ["BULLISH", "BEARISH"], "minimum_rr": {"BULLISH": "3", "BEARISH": "4"}},
    ],
)
def test_other_signed_side_subsets_use_the_same_resolver(updates):
    value = record()
    value["t3"].update(updates)
    result = resolve(value)
    assert result.permission is OfflinePermission.FIXTURE_ONLY
    assert result.minimum_rr[-1][1] in (Decimal("3"), Decimal("4"))


@pytest.mark.parametrize(
    "updates",
    [
        {"entry_types": ["LIMIT"]},
        {"directions": ["OTHER"]},
        {"deny_market_entry": True},
        {"minimum_rr": {"BULLISH": "1", "BEARISH": None}},
        {"minimum_rr": {"BULLISH": None, "BEARISH": None}},
        {"minimum_rr": {"BULLISH": "11", "BEARISH": None}},
    ],
)
def test_t3_widening_or_absent_side_floor_denies_without_clamping(updates):
    value = record()
    value["t3"].update(updates)
    assert resolve(value).permission is OfflinePermission.DENIED


def test_owner_floor_empty_intersection_bounds_and_context_scope_fail_closed():
    value = record()
    value["minimum_rr"]["BULLISH"] = None
    assert resolve(value).permission is OfflinePermission.DENIED
    value["minimum_rr"]["BULLISH"] = "11"
    assert resolve(value).permission is OfflinePermission.DENIED
    policy = load()
    run = context(policy)
    for field, new in [
        ("run", RunId("OTHER")),
        ("account", SimulatedAccountId("SIMULATED_OTHER")),
        ("instrument", InstrumentId("OTHER")),
        ("policy", PolicyId("OTHER")),
        ("policy_sha256", Digest("0" * 64)),
        ("valid_until", AT),
    ]:
        assert (
            resolve_fixture_tiers(policy, replace(run, **{field: new}), AT).permission
            is OfflinePermission.DENIED
        )
    assert (
        resolve_fixture_tiers(policy, run, policy.valid_until).permission
        is OfflinePermission.DENIED
    )
    for changed in (
        replace(policy.restrictions, directions=()),
        replace(policy.restrictions, entry_types=()),
    ):
        assert (
            resolve_fixture_tiers(replace(policy, restrictions=changed), run, AT).permission
            is OfflinePermission.DENIED
        )
    for lower, upper, number in [
        (Decimal("NaN"), Decimal(10), Decimal(1)),
        (Decimal(0), Decimal("Infinity"), Decimal(1)),
        (Decimal(0), Decimal(10), Decimal("NaN")),
        (Decimal(0), Decimal(10), True),
        (0, Decimal(10), Decimal(1)),
        (Decimal(0), 10, Decimal(1)),
    ]:
        assert not NumericBounds(lower, upper).accepts(number)


@given(st.integers(min_value=0, max_value=1999))
def test_any_t3_rr_below_signed_owner_floor_denies(milli):
    value = copy.deepcopy(record())
    value["t3"]["minimum_rr"]["BULLISH"] = str(Decimal(milli) / 1000)
    assert resolve(value).permission is OfflinePermission.DENIED
