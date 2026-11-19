"""EXT-13 exact fixture listing evidence and EXT-01 configuration-only registration.

No field can certify a real broker or grant a monetary permission. The in-memory
schema registry serializes signed fixture commands; operational durable authority,
ledger transactions and promotions belong to later stages and are not supplied.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from threading import RLock

from v3.offline.calendar_completion import require_utc
from v3.offline.data_intake_schema import digest, object_fields, utc
from v3.offline.effective_policy import _decimal
from v3.offline.fixture_policy_loader import (
    JsonValue,
    _identity,
    _integer,
    _parse,
    _text,
    authenticate_fixture,
)
from v3.offline.instrument_definition import InstrumentDefinition
from v3.offline.intent_identity import (
    Digest,
    Identity,
    InstrumentId,
    RunContext,
    SimulatedAccountId,
)

ECONOMICS_FIELDS = frozenset(
    {
        "size_unit",
        "stake_increment",
        "min_stake",
        "point_value",
        "min_stop_distance",
        "margin_factor",
        "margin_currency",
        "settlement_currency",
        "contract_size",
        "price_step",
        "spread",
        "fee",
        "stop_capability",
        "market_status",
        "expiry_timestamp",
        "last_trade_timestamp",
        "margin_treatment",
        "session",
    }
)
_NONNEGATIVE = {"min_stake", "margin_factor", "spread", "fee"}
_POSITIVE = {"stake_increment", "point_value", "min_stop_distance", "contract_size", "price_step"}


def _hash(record: dict[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


@dataclass(frozen=True)
class ListingAssessment:
    """Verified fixture-only values or explicit UNKNOWN; never executable sizing/entry."""

    complete_fixture_data: bool
    reason: str
    listing_sha256: Digest | None = None
    values: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True)
class FixtureOutcomeEvidence:
    """Forward-only schema-replay outcome, explicitly neither performance nor approval."""

    definition_sha256: Digest
    listing_sha256: Digest
    input_sha256: Digest
    policy_sha256: Digest
    build_sha256: Digest
    available_at: datetime
    payload_sha256: Digest


def load_fixture_outcome(
    payload: bytes,
    manifest: bytes,
    signature: bytes,
    public_key: bytes,
    definition: InstrumentDefinition,
    listing: ListingAssessment,
    context: RunContext,
    at: datetime,
) -> FixtureOutcomeEvidence:
    """Bind subsequent immutable outputs to exact prior inputs/family/listing; no cyclic refs."""
    require_utc(at)
    verified = authenticate_fixture(payload, manifest, signature, public_key)
    record = object_fields(
        _parse(verified.payload, verified.bounds),
        {
            "kind",
            "qualification",
            "definition_sha256",
            "listing_sha256",
            "input_sha256",
            "policy_sha256",
            "build_sha256",
            "observed_at",
            "available_at",
        },
    )
    if (
        record["kind"] != "FIXTURE_SCHEMA_OUTCOME_V1"
        or record["qualification"] != "SCHEMA_REPLAY_NOT_PERFORMANCE_NOT_APPROVAL"
        or not listing.complete_fixture_data
        or listing.listing_sha256 is None
        or digest(record["definition_sha256"]) != definition.effective_config_sha256.value
        or digest(record["listing_sha256"]) != listing.listing_sha256.value
        or digest(record["input_sha256"]) != definition.input_sha256.value
        or digest(record["policy_sha256"]) != definition.policy_sha256.value
        or definition.policy_sha256 != context.policy_sha256
        or digest(record["build_sha256"]) != definition.build_sha256.value
        or definition.build_sha256 != context.build_sha256
        or not context.valid_from
        <= definition.authored_at
        <= utc(record["observed_at"])
        <= utc(record["available_at"])
        <= at
        < context.valid_until
    ):
        raise ValueError("Invalid forward-only schema outcome or attempted approval")
    return FixtureOutcomeEvidence(
        definition.effective_config_sha256,
        listing.listing_sha256,
        definition.input_sha256,
        definition.policy_sha256,
        definition.build_sha256,
        utc(record["available_at"]),
        Digest(verified.payload_sha256),
    )


def assess_fixture_listing(
    payload: bytes,
    manifest: bytes,
    signature: bytes,
    public_key: bytes,
    definition: InstrumentDefinition,
    context: RunContext,
    at: datetime,
) -> ListingAssessment:
    """Read only one exact account/family/product revision with current distinct per-field proof."""
    require_utc(at)
    verified = authenticate_fixture(payload, manifest, signature, public_key)
    record = object_fields(
        _parse(verified.payload, verified.bounds), {"kind", "listing", "evidence_index"}
    )
    listing = object_fields(
        record["listing"],
        {
            "contract_listing_id",
            "product_family_id",
            "broker_product_id",
            "expiry_timestamp",
            "last_trade_timestamp",
            "status",
            "account_scope_id",
            "per_field_evidence_index_sha256",
            "economics_revision_sha256",
            "listing_sha256",
            "observed_at",
        },
    )
    index = object_fields(
        record["evidence_index"],
        {
            "kind",
            "account_id",
            "product_id",
            "max_age_seconds",
            "source_price_unit",
            "source_currency",
            "point_conversion",
            "fields",
        },
    )
    body = {key: value for key, value in listing.items() if key != "listing_sha256"}
    index_hash, listing_hash = _hash(index), _hash(body)
    _identity(listing["contract_listing_id"])
    product = _identity(listing["broker_product_id"])
    maximum_age = _integer(index["max_age_seconds"])
    if (
        record["kind"] != "FIXTURE_CONTRACT_LISTING_V1"
        or index["kind"] != "FIXTURE_ECONOMICS_INDEX_V1"
        or listing["status"] != "ACTIVE"
        or maximum_age <= 0
        or listing["account_scope_id"] != context.account.value
        or index["account_id"] != context.account.value
        or listing["product_family_id"] != definition.family.value
        or index["product_id"] != product
        or definition.instrument != context.instrument
        or definition.policy_sha256 != context.policy_sha256
        or definition.build_sha256 != context.build_sha256
        or digest(listing["per_field_evidence_index_sha256"]) != index_hash
        or digest(listing["economics_revision_sha256"]) != index_hash
        or digest(listing["listing_sha256"]) != listing_hash
        or not 0 <= (at - utc(listing["observed_at"])).total_seconds() <= maximum_age
        or index["source_price_unit"] != definition.unit.name.value
        or index["source_currency"] != definition.unit.currency
        or _decimal(index["point_conversion"]) != 1
    ):
        return ListingAssessment(False, "UNKNOWN_LISTING_SCOPE_REVISION_OR_UNIT")
    raw_fields = index["fields"]
    if not isinstance(raw_fields, list):
        raise ValueError("Explicit per-field evidence list required")
    names: set[str] = set()
    ids: set[str] = set()
    values = []
    for raw in raw_fields:
        field = object_fields(
            raw,
            {
                "field",
                "value",
                "unit",
                "evidence_id",
                "source",
                "observed_at",
                "available_at",
                "account_id",
                "product_id",
                "status",
                "actor",
                "content_sha256",
            },
        )
        name, evidence_id = _identity(field["field"]), _identity(field["evidence_id"])
        value, unit = _text(field["value"]), _identity(field["unit"])
        _identity(field["source"])
        body = {key: value for key, value in field.items() if key != "content_sha256"}
        if (
            name not in ECONOMICS_FIELDS
            or name in names
            or evidence_id in ids
            or field["status"] != "FIXTURE_VERIFIED"
            or field["actor"] != "FIXTURE_ECONOMICS_ATTESTOR"
            or field["account_id"] != context.account.value
            or field["product_id"] != product
            or digest(field["content_sha256"]) != _hash(body)
            or not utc(field["observed_at"]) <= utc(field["available_at"]) <= at
            or not 0 <= (at - utc(field["observed_at"])).total_seconds() <= maximum_age
        ):
            return ListingAssessment(False, "UNKNOWN_FIELD_PROOF")
        if name in _POSITIVE | _NONNEGATIVE:
            number = _decimal(value)
            if number is None or (name in _POSITIVE and number <= 0):
                return ListingAssessment(False, "UNKNOWN_ECONOMICS_VALUE")
        names.add(name)
        ids.add(evidence_id)
        values.append((name, value, unit))
    mapping = {name: (value, unit) for name, value, unit in values}
    if names != ECONOMICS_FIELDS:
        return ListingAssessment(False, "MISSING_MANDATORY_FIELD")
    if (
        mapping["size_unit"][0] not in {"GBP_PER_POINT", "CONTRACTS", "OTHER"}
        or mapping["stop_capability"][0] != "ATTACHED_STOP"
        or mapping["market_status"][0] != "OPEN"
        or mapping["margin_treatment"][0] != "GROSS"
        or mapping["session"][0] != "OPEN"
        or any(
            mapping[name][0] not in definition.currencies
            for name in ("margin_currency", "settlement_currency")
        )
        or mapping["price_step"][1] != definition.unit.name.value
        or mapping["point_value"][1]
        != mapping["settlement_currency"][0] + "_PER_" + definition.point_unit.name.value
        or mapping["min_stop_distance"][1] != definition.point_unit.name.value
        or mapping["expiry_timestamp"][0] != (listing["expiry_timestamp"] or "NONE")
        or mapping["last_trade_timestamp"][0] != (listing["last_trade_timestamp"] or "NONE")
    ):
        return ListingAssessment(False, "UNKNOWN_LISTING_CAPABILITY_OR_DIMENSION")
    if definition.expiry_mode == "CASH":
        if listing["expiry_timestamp"] is not None or listing["last_trade_timestamp"] is not None:
            return ListingAssessment(False, "CASH_EXPIRY_CONFLICT")
    elif (
        listing["expiry_timestamp"] is None
        or listing["last_trade_timestamp"] is None
        or not at < utc(listing["last_trade_timestamp"]) <= utc(listing["expiry_timestamp"])
    ):
        return ListingAssessment(False, "UNKNOWN_OR_EXPIRED_CONTRACT")
    return ListingAssessment(
        True,
        "COMPLETE_FIXTURE_VALUES_NOT_MONETARY_AUTHORITY",
        Digest(listing_hash),
        tuple(sorted(values)),
    )


@dataclass(frozen=True)
class RegistrationEvent:
    """Append-only fixture event; no research/broker/DEMO/LIVE authority transition."""

    event_id: Identity
    version: int
    instrument: InstrumentId
    definition_sha256: Digest
    command_sha256: Digest
    previous_sha256: Digest
    event_sha256: Digest


class FixtureRegistrationRegistry:
    """Configuration-only fixture registry with serialized expected-version checks."""

    def __init__(self) -> None:
        """Start empty; rebuilding requires replay of the retained signed command fixtures."""
        self._lock = RLock()
        self._events: tuple[RegistrationEvent, ...] = ()

    @property
    def events(self) -> tuple[RegistrationEvent, ...]:
        """Expose immutable append-only fixture history, never mutation authority."""
        with self._lock:
            return self._events

    def register(
        self,
        payload: bytes,
        manifest: bytes,
        signature: bytes,
        public_key: bytes,
        definition: InstrumentDefinition,
        context: RunContext,
        at: datetime,
    ) -> RegistrationEvent:
        """Authenticate configuration actor, scope and exact prior state before atomic append."""
        require_utc(at)
        verified = authenticate_fixture(payload, manifest, signature, public_key)
        command = object_fields(
            _parse(verified.payload, verified.bounds),
            {
                "kind",
                "actor",
                "event_id",
                "expected_version",
                "instrument_id",
                "definition_sha256",
                "run_id",
                "expected_previous_sha256",
                "account_id",
                "policy_sha256",
                "at",
            },
        )
        event_id = Identity(_identity(command["event_id"]))
        expected = _integer(command["expected_version"])
        account = SimulatedAccountId(_identity(command["account_id"]))
        if (
            command["kind"] != "FIXTURE_CONFIG_REGISTRATION_V1"
            or command["actor"] != "FIXTURE_CONFIG_CONTROL"
            or account != context.account
            or command["run_id"] != context.run.value
            or command["instrument_id"] != definition.instrument.value
            or definition.instrument != context.instrument
            or digest(command["definition_sha256"]) != definition.effective_config_sha256.value
            or digest(command["policy_sha256"]) != context.policy_sha256.value
            or definition.policy_sha256 != context.policy_sha256
            or definition.build_sha256 != context.build_sha256
            or not context.valid_from <= utc(command["at"]) <= at < context.valid_until
        ):
            raise ValueError("Unauthenticated or mismatched fixture configuration writer/scope")
        with self._lock:
            for event in self._events:
                if event.command_sha256.value == verified.payload_sha256:
                    return event
                if event.event_id == event_id or event.instrument == definition.instrument:
                    raise ValueError("Conflicting event or immutable instrument identity")
            previous = self._events[-1].event_sha256 if self._events else Digest("0" * 64)
            if (
                expected != len(self._events)
                or digest(command["expected_previous_sha256"]) != previous.value
            ):
                raise ValueError("Registration expected-version or previous-state conflict")
            event_hash = Digest(
                hashlib.sha256(
                    (previous.value + verified.payload_sha256 + str(expected + 1)).encode()
                ).hexdigest()
            )
            event = RegistrationEvent(
                event_id,
                expected + 1,
                definition.instrument,
                definition.effective_config_sha256,
                Digest(verified.payload_sha256),
                previous,
                event_hash,
            )
            self._events += (event,)
            return event
