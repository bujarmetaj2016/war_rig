"""Unit-01 restriction-only fixture tier resolution; no owner-policy or IG authority.

Stdlib, typed identities and the signed fixture/schema boundary are allowed.
T1 checks cannot disappear, T3 cannot widen T2 sets/bounds or edit protection,
and UNSELECTED fields deny. Successful resolution validates synthetic parameters
only; it is neither eligibility nor a signed send/stop/close permit.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from v3.offline.calendar_completion import require_utc
from v3.offline.data_intake_schema import digest, object_fields, utc
from v3.offline.fixture_policy_loader import (
    JsonValue,
    _identity,
    _integer,
    _parse,
    _text,
    authenticate_fixture,
)
from v3.offline.intent_identity import (
    Digest,
    InstrumentId,
    PolicyId,
    RunContext,
    RunId,
    SimulatedAccountId,
)

T1_REQUIRED_CHECKS = frozenset({"SIGNATURE", "COMPLETED_DATA", "SOURCE_BINDING"})


class OfflinePermission(StrEnum):
    """The offline permission domain cannot represent an IG or real monetary grant."""

    DENIED = "DENIED"
    FIXTURE_ONLY = "FIXTURE_ONLY"


@dataclass(frozen=True)
class NumericBounds:
    """Signed exact lower-exclusive/upper-inclusive synthetic parameter envelope."""

    lower_exclusive: Decimal
    upper_inclusive: Decimal

    def accepts(self, value: Decimal) -> bool:
        """Check finite Decimal values and ordered limits without coercion or clamping."""
        return (
            isinstance(value, Decimal)
            and value.is_finite()
            and isinstance(self.lower_exclusive, Decimal)
            and isinstance(self.upper_inclusive, Decimal)
            and self.lower_exclusive.is_finite()
            and self.upper_inclusive.is_finite()
            and Decimal(0) <= self.lower_exclusive < value <= self.upper_inclusive
        )


@dataclass(frozen=True)
class DirectionalFloors:
    """Explicit side-specific RR floors; missing/unselected values stay absent."""

    bullish: Decimal | None
    bearish: Decimal | None


@dataclass(frozen=True)
class T3Restrictions:
    """Instrument-local restrictions; protection and mandatory-check edits have no fields."""

    directions: tuple[str, ...]
    entry_types: tuple[str, ...]
    minimum_rr: DirectionalFloors
    deny_market_entry: bool


@dataclass(frozen=True)
class FixtureTierPolicy:
    """Distinct signed fixture-policy type, with scope/seed/scenario and finite expiry."""

    policy_id: PolicyId
    run_id: RunId
    account_id: SimulatedAccountId
    instrument_ids: tuple[InstrumentId, ...]
    valid_from: datetime
    valid_until: datetime
    scenario_sha256: Digest
    seed: int
    required_checks: tuple[str, ...]
    directions: tuple[str, ...]
    entry_types: tuple[str, ...]
    minimum_rr: DirectionalFloors
    rr_bounds: NumericBounds | None
    evaluation_budget_seconds: Decimal | None
    budget_bounds: NumericBounds | None
    required_strategy_entry_type: str
    restrictions: T3Restrictions
    payload_sha256: Digest
    signer_sha256: Digest


@dataclass(frozen=True)
class PolicyResolution:
    """Immutable bounded fixture parameters or explicit denial, never entry eligibility."""

    permission: OfflinePermission
    reason: str
    directions: tuple[str, ...] = ()
    entry_types: tuple[str, ...] = ()
    minimum_rr: tuple[tuple[str, Decimal], ...] = ()


def _decimal(value: JsonValue) -> Decimal | None:
    if value is None:
        return None
    text = _text(value)
    if not re.fullmatch(r"(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,12})?", text):
        raise ValueError("Expected bounded exact nonnegative policy decimal")
    return Decimal(text)


def _bounds(value: JsonValue) -> NumericBounds | None:
    if value is None:
        return None
    record = object_fields(value, {"lower_exclusive", "upper_inclusive"})
    lower, upper = _decimal(record["lower_exclusive"]), _decimal(record["upper_inclusive"])
    if lower is None or upper is None:
        raise ValueError("Explicit numeric bounds are required")
    return NumericBounds(lower, upper)


def _strings(value: JsonValue) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("A nonempty declared set is required")
    result = tuple(_identity(item) for item in value)
    if len(set(result)) != len(result):
        raise ValueError("Duplicate policy set member")
    return result


def _rr(value: JsonValue) -> DirectionalFloors:
    record = object_fields(value, {"BULLISH", "BEARISH"})
    return DirectionalFloors(_decimal(record["BULLISH"]), _decimal(record["BEARISH"]))


def load_fixture_tiers(
    payload: bytes, manifest: bytes, signature: bytes, public_key: bytes
) -> FixtureTierPolicy:
    """Authenticate and strictly type a fixture tier policy, or raise; no I/O/defaults."""
    verified = authenticate_fixture(payload, manifest, signature, public_key)
    fields = {
        "kind",
        "scope",
        "policy_id",
        "run_id",
        "account_id",
        "instrument_ids",
        "valid_from",
        "valid_until",
        "scenario_sha256",
        "seed",
        "required_checks",
        "directions",
        "entry_types",
        "minimum_rr",
        "rr_bounds",
        "evaluation_budget_seconds",
        "budget_bounds",
        "required_strategy_entry_type",
        "t3",
    }
    record = object_fields(_parse(verified.payload, verified.bounds), fields)
    if record["kind"] != "FIXTURE_TIER_POLICY_V1" or record["scope"] != "FIXTURE_ONLY":
        raise ValueError("Not a fixture-only tier policy")
    restriction = object_fields(
        record["t3"], {"directions", "entry_types", "minimum_rr", "deny_market_entry"}
    )
    if type(restriction["deny_market_entry"]) is not bool:
        raise ValueError("Instrument restriction must be boolean")
    seed = _integer(record["seed"])
    if seed < 0:
        raise ValueError("A synthetic scenario seed is required")
    return FixtureTierPolicy(
        PolicyId(_identity(record["policy_id"])),
        RunId(_identity(record["run_id"])),
        SimulatedAccountId(_identity(record["account_id"])),
        tuple(InstrumentId(item) for item in _strings(record["instrument_ids"])),
        utc(record["valid_from"]),
        utc(record["valid_until"]),
        Digest(digest(record["scenario_sha256"])),
        seed,
        _strings(record["required_checks"]),
        _strings(record["directions"]),
        _strings(record["entry_types"]),
        _rr(record["minimum_rr"]),
        _bounds(record["rr_bounds"]),
        _decimal(record["evaluation_budget_seconds"]),
        _bounds(record["budget_bounds"]),
        _identity(record["required_strategy_entry_type"]),
        T3Restrictions(
            _strings(restriction["directions"]),
            _strings(restriction["entry_types"]),
            _rr(restriction["minimum_rr"]),
            restriction["deny_market_entry"],
        ),
        Digest(verified.payload_sha256),
        Digest(verified.signer_sha256),
    )


def resolve_fixture_tiers(
    policy: FixtureTierPolicy, context: RunContext, at: datetime
) -> PolicyResolution:
    """Intersect selected T2/T3 restrictions or deny explicitly; never clamp or grant entry."""
    require_utc(at)
    deny = OfflinePermission.DENIED
    if (
        context.run != policy.run_id
        or context.account != policy.account_id
        or context.policy != policy.policy_id
        or context.policy_sha256 != policy.payload_sha256
        or context.instrument not in policy.instrument_ids
        or not policy.valid_from <= at < policy.valid_until
        or not context.valid_from <= at < context.valid_until
    ):
        return PolicyResolution(deny, "SCOPE_OR_VALIDITY_MISMATCH")
    t3 = policy.restrictions
    if (
        not T1_REQUIRED_CHECKS <= set(policy.required_checks)
        or not set(t3.directions) <= set(policy.directions) <= {"BULLISH", "BEARISH"}
        or not set(t3.entry_types) <= set(policy.entry_types) <= {"MARKET"}
        or policy.required_strategy_entry_type != "MARKET"
        or t3.deny_market_entry
    ):
        return PolicyResolution(deny, "MANDATORY_CHECK_OR_TIER_SET_VIOLATION")
    if (
        policy.rr_bounds is None
        or policy.budget_bounds is None
        or policy.evaluation_budget_seconds is None
        or not policy.budget_bounds.accepts(policy.evaluation_budget_seconds)
    ):
        return PolicyResolution(deny, "UNSELECTED_OR_INVALID_SIGNED_BOUNDS")
    owner_rr, local_rr = policy.minimum_rr, t3.minimum_rr
    effective = []
    for direction in sorted(set(policy.directions) & set(t3.directions)):
        floor = owner_rr.bullish if direction == "BULLISH" else owner_rr.bearish
        tighter = local_rr.bullish if direction == "BULLISH" else local_rr.bearish
        if (
            floor is None
            or tighter is None
            or not policy.rr_bounds.accepts(floor)
            or not policy.rr_bounds.accepts(tighter)
            or tighter < floor
        ):
            return PolicyResolution(deny, "UNSELECTED_OR_WIDENED_DIRECTIONAL_RR")
        effective.append((direction, max(floor, tighter)))
    if not effective or not t3.entry_types:
        return PolicyResolution(deny, "EMPTY_EFFECTIVE_POLICY")
    return PolicyResolution(
        OfflinePermission.FIXTURE_ONLY,
        "BOUNDED_FIXTURE_PARAMETERS_NOT_ELIGIBILITY",
        tuple(side for side, _ in effective),
        tuple(sorted(t3.entry_types)),
        tuple(effective),
    )
