"""EXT-01 immutable full closed family schema; input evidence precedes definition, never outcomes.

Canonical bytes retain every validated field. Typed reference groups contain no mutable
JSON maps. Fixture registration is not broker certification, a model approval or entry.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime

from v3.offline.calendar_completion import DataVerdict, ReplayClock, SignedSnapshot, assess_snapshot
from v3.offline.data_intake_schema import digest, object_fields, utc
from v3.offline.effective_policy import (
    FixtureTierPolicy,
    OfflinePermission,
    _decimal,
    _rr,
    _strings,
    resolve_fixture_tiers,
)
from v3.offline.fixture_policy_loader import (
    JsonValue,
    _identity,
    _integer,
    _parse,
    _text,
    authenticate_fixture,
)
from v3.offline.intent_identity import Digest, Identity, InstrumentId, PriceUnit, RunContext
from v3.offline.plugin_manifest import PluginManifest

POLICY_FIELDS = frozenset(
    {
        "macro_freshness_policy_id",
        "model_use_policy_id",
        "broker_economics_bounds_policy_id",
        "contract_selection_policy_id",
        "rollover_policy_id",
        "entry_checks_policy_id",
        "direction_eligibility_policy_id",
        "risk_policy_id",
        "protection_policy_id",
        "portfolio_candidate_priority_policy_id",
        "evaluation_time_budget_policy_id",
        "data_quality_policy_id",
    }
)
REFERENCE_FIELDS = frozenset(
    {
        "price_instrument_id",
        "session_profile_id",
        "macro_profile_id",
        "broker_id",
        "broker_product_family_id",
        "broker_account_scope_id",
        "cost_schedule_ref",
        "market_status_mapping_id",
        "portfolio_group_id",
        "evaluation_criteria_id",
        "audit_schema_id",
    }
)
DEFINITION_FIELDS = set(POLICY_FIELDS | REFERENCE_FIELDS) | {
    "schema_version",
    "instrument_id",
    "display_name",
    "asset_class",
    "base_currency",
    "quote_currency",
    "settlement_currency",
    "contract_unit",
    "point_unit",
    "data_source_id",
    "data_source_version",
    "intervals",
    "completion_rule_id",
    "calendar_rule_id",
    "timezone",
    "macro_feature_refs",
    "strategy_plugin_id",
    "strategy_version",
    "strategy_parameters",
    "feature_schema_hash",
    "model_artifact_sha256",
    "model_fit_record_id",
    "instrument_type",
    "expiry_mode",
    "deny_market_entry",
    "definition_input_evidence_manifest_sha256",
    "calendar_constraints",
    "criteria_hash",
    "effective_config_sha256",
}


@dataclass(frozen=True)
class DefinitionInputEvidence:
    """Pre-existing signed synthetic baseline, not broker certification or fit approval."""

    evidence_id: Identity
    instruments: tuple[str, ...]
    currencies: tuple[str, ...]
    feature_schema_sha256: Digest
    available_at: datetime
    payload_sha256: Digest
    references: tuple[tuple[str, tuple[str, ...]], ...]
    criteria_sha256: Digest
    timezones: tuple[tuple[str, str, str], ...]


def _timezones(value: JsonValue) -> tuple[tuple[str, str, str], ...]:
    if not isinstance(value, dict) or not value:
        raise ValueError("Versioned signed timezone inventory required")
    result = []
    for name, raw in sorted(value.items()):
        record = object_fields(raw, {"version", "tzif_sha256"})
        if not re.fullmatch(r"(?:[A-Za-z_]+(?:/[A-Za-z_+-]+)+|UTC)", name):
            raise ValueError("Invalid IANA timezone identifier")
        result.append((name, _identity(record["version"]), digest(record["tzif_sha256"])))
    return tuple(result)


def load_definition_inputs(
    payload: bytes, manifest: bytes, signature: bytes, public_key: bytes
) -> DefinitionInputEvidence:
    """Authenticate acyclic inputs, forbidding subsequent definition/outcome references."""
    verified = authenticate_fixture(payload, manifest, signature, public_key)
    item = object_fields(
        _parse(verified.payload, verified.bounds),
        {
            "kind",
            "evidence_id",
            "instrument_ids",
            "currencies",
            "feature_schema_sha256",
            "observed_at",
            "available_at",
            "qualification",
            "baseline_cost_assumption",
            "reference_values",
            "criteria",
            "timezones",
        },
    )
    currencies = _strings(item["currencies"])
    if (
        item["kind"] != "FIXTURE_DEFINITION_INPUT_V1"
        or item["qualification"] != "ASSUMPTION_NOT_BROKER_CERTIFICATION"
        or any(not re.fullmatch(r"[A-Z]{3}", value) for value in currencies)
        or utc(item["observed_at"]) > utc(item["available_at"])
        or _decimal(item["baseline_cost_assumption"]) is None
    ):
        raise ValueError("Invalid pre-existing input evidence")
    return DefinitionInputEvidence(
        Identity(_identity(item["evidence_id"])),
        _strings(item["instrument_ids"]),
        currencies,
        Digest(digest(item["feature_schema_sha256"])),
        utc(item["available_at"]),
        Digest(verified.payload_sha256),
        tuple(
            (name, _strings(values))
            for name, values in sorted(
                object_fields(item["reference_values"], set(REFERENCE_FIELDS)).items()
            )
        ),
        Digest(hashlib.sha256(_text(item["criteria"]).encode()).hexdigest()),
        _timezones(item["timezones"]),
    )


def _unit(value: JsonValue) -> PriceUnit:
    unit = object_fields(value, {"dimension", "currency", "precision", "increment"})
    increment = _decimal(unit["increment"])
    if increment is None:
        raise ValueError("Explicit source increment required")
    return PriceUnit(
        Identity(_identity(unit["dimension"])),
        _identity(unit["currency"]),
        _integer(unit["precision"]),
        increment,
    )


def definition_fingerprint(
    body: dict[str, JsonValue],
    plugins: Digest,
    policy: Digest,
) -> Digest:
    """Hash every canonical family field except its own derived digest, plus exact external pins."""
    included = {key: value for key, value in body.items() if key != "effective_config_sha256"}
    encoded = json.dumps(
        {"definition": included, "plugin_manifest": plugins.value, "policy": policy.value},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return Digest(hashlib.sha256(encoded).hexdigest())


@dataclass(frozen=True)
class InstrumentDefinition:
    """Validated stable family; listing economics, outcomes and authority cannot be fields."""

    instrument: InstrumentId
    family: Identity
    source: Identity
    source_version: str
    unit: PriceUnit
    point_unit: PriceUnit
    intervals: tuple[int, ...]
    timezone: str
    expiry_mode: str
    references: tuple[tuple[str, Identity], ...]
    policy_refs: tuple[tuple[str, Identity | None], ...]
    input_sha256: Digest
    policy_sha256: Digest
    plugins_sha256: Digest
    effective_config_sha256: Digest
    canonical: bytes
    currencies: tuple[str, ...]
    build_sha256: Digest
    authored_at: datetime


def load_instrument_definition(
    payload: bytes,
    manifest: bytes,
    signature: bytes,
    public_key: bytes,
    plugins: PluginManifest,
    inputs: DefinitionInputEvidence,
    policy: FixtureTierPolicy,
    context: RunContext,
    snapshot: SignedSnapshot,
) -> InstrumentDefinition:
    """Validate EXT section 3.2 fields and dependencies; only synthetic parameters can pass."""
    verified = authenticate_fixture(payload, manifest, signature, public_key)
    envelope = object_fields(
        _parse(verified.payload, verified.bounds), {"kind", "authored_at", "definition"}
    )
    item = object_fields(envelope["definition"], DEFINITION_FIELDS)
    instrument = InstrumentId(_identity(item["instrument_id"]))
    references = tuple((name, Identity(_identity(item[name]))) for name in sorted(REFERENCE_FIELDS))
    policies = tuple(
        (name, None if item[name] is None else Identity(_identity(item[name])))
        for name in sorted(POLICY_FIELDS)
    )
    unit, point_unit = _unit(item["contract_unit"]), _unit(item["point_unit"])
    raw_intervals = item["intervals"]
    if not isinstance(raw_intervals, list) or not raw_intervals:
        raise ValueError("Explicit supported source intervals required")
    intervals = tuple(_integer(value) for value in raw_intervals)
    constraints = object_fields(item["calendar_constraints"], {"not_before", "not_after"})
    parameters = object_fields(item["strategy_parameters"], {"minimum_rr", "entry_type"})
    rr = _rr(parameters["minimum_rr"])
    resolution = resolve_fixture_tiers(policy, context, snapshot.clock.at)
    for name, interface, version in (
        ("data_source_id", "SNAPSHOT_FIXTURE_V1", _identity(item["data_source_version"])),
        ("completion_rule_id", "COMPLETION_V1", "1.0.0"),
        ("calendar_rule_id", "CALENDAR_V1", "1.0.0"),
        ("strategy_plugin_id", "FIXTURE_PARAMETERS_V1", _identity(item["strategy_version"])),
    ):
        plugins.require(_identity(item[name]), interface, version)
    for macro in _strings(item["macro_feature_refs"]):
        plugins.require(macro, "MACRO_INPUT_V1")
    digest(item["criteria_hash"])
    schema = Digest(digest(item["feature_schema_hash"]))
    input_digest = Digest(digest(item["definition_input_evidence_manifest_sha256"]))
    fingerprint = definition_fingerprint(item, plugins.payload_sha256, policy.payload_sha256)
    if snapshot.bar is None or snapshot.bar.price is None:
        raise ValueError("Completed source price required")
    if (
        envelope["kind"] != "FIXTURE_INSTRUMENT_DEFINITION_V1"
        or item["schema_version"] != "1.0.0"
        or not 1 <= len(_text(item["display_name"])) <= 120
        or _identity(item["asset_class"])
        not in {"FX", "EQUITY", "INDEX", "METAL", "ENERGY", "OTHER"}
        or _identity(item["instrument_type"]) not in {"SPREAD_BET", "CFD", "OTHER"}
        or _identity(item["expiry_mode"]) not in {"CASH", "EXPIRING", "ROLLING"}
        or any(
            _identity(item[name]) not in inputs.currencies
            for name in ("base_currency", "quote_currency", "settlement_currency")
        )
        or type(item["deny_market_entry"]) is not bool
        or item["deny_market_entry"]
        or item["model_artifact_sha256"] is not None
        or item["model_fit_record_id"] is not None
        or instrument != context.instrument
        or instrument.value not in inputs.instruments
        or plugins.build_sha256 != context.build_sha256
        or input_digest != inputs.payload_sha256
        or inputs.available_at > utc(envelope["authored_at"])
        or utc(envelope["authored_at"]) > snapshot.clock.at
        or schema != inputs.feature_schema_sha256
        or schema != context.feature_schema_sha256
        or item["broker_id"] != "OFFLINE_SIMULATOR"
        or item["broker_account_scope_id"] != context.account.value
        or item["cost_schedule_ref"] != inputs.evidence_id.value
        or item["audit_schema_id"] != "FIXTURE_AUDIT_V1"
        or any(_identity(item[name]) not in allowed for name, allowed in inputs.references)
        or digest(item["criteria_hash"]) != inputs.criteria_sha256.value
        or any(value is not None and value.value != policy.policy_id.value for _, value in policies)
        or any(
            item[name] is None
            for name in (
                "macro_freshness_policy_id",
                "entry_checks_policy_id",
                "direction_eligibility_policy_id",
                "evaluation_time_budget_policy_id",
                "data_quality_policy_id",
            )
        )
        or resolution.permission is not OfflinePermission.FIXTURE_ONLY
        or parameters["entry_type"] != "MARKET"
        or rr.bullish is None
        or policy.minimum_rr.bullish is None
        or rr.bullish < policy.minimum_rr.bullish
        or rr.bearish is None
        or policy.minimum_rr.bearish is None
        or rr.bearish < policy.minimum_rr.bearish
        or policy.rr_bounds is None
        or not policy.rr_bounds.accepts(rr.bullish)
        or not policy.rr_bounds.accepts(rr.bearish)
        or not policy.valid_from <= utc(constraints["not_before"]) <= snapshot.clock.at
        or not snapshot.clock.at < utc(constraints["not_after"]) <= policy.valid_until
        or len(set(intervals)) != len(intervals)
        or any(value <= 0 for value in intervals)
        or snapshot.calendar.interval_seconds not in intervals
        or snapshot.binding.instrument_id != item["price_instrument_id"]
        or snapshot.binding.source_id != item["data_source_id"]
        or snapshot.binding.source_version != item["data_source_version"]
        or snapshot.binding.policy_sha256 != policy.payload_sha256.value
        or snapshot.binding.run_id != context.run.value
        or snapshot.binding.account_id != context.account.value
        or snapshot.binding.feature_schema_sha256 != schema.value
        or context.source_sha256.value != snapshot.lineage.snapshot_sha256
        or context.clock_id.value != snapshot.clock.source_clock_id
        or snapshot.binding.timezone != item["timezone"]
        or not snapshot.binding.timezone_version
        or (
            snapshot.binding.timezone,
            snapshot.binding.timezone_version,
            hashlib.sha256(snapshot.calendar.tzif).hexdigest(),
        )
        not in inputs.timezones
        or snapshot.binding.price_unit != unit.name.value
        or snapshot.binding.currency != unit.currency
        or unit.currency != item["quote_currency"]
        or point_unit.name != unit.name
        or point_unit.currency != unit.currency
        or assess_snapshot(snapshot, snapshot.binding, ReplayClock(snapshot.clock.at)).verdict
        is not DataVerdict.COMPLETED_FIXTURE_ONLY
        or digest(item["effective_config_sha256"]) != fingerprint.value
    ):
        raise ValueError(
            "Definition, input, policy, source, calendar or immutable fingerprint mismatch"
        )
    unit.check(snapshot.bar.price)
    point_unit.check(snapshot.bar.price)
    floors = {"BULLISH": rr.bullish, "BEARISH": rr.bearish}
    if any(floors[side] < floor for side, floor in resolution.minimum_rr):
        raise ValueError("Strategy parameters weaken the effective T3 RR floor")
    return InstrumentDefinition(
        instrument,
        Identity(_identity(item["broker_product_family_id"])),
        Identity(_identity(item["data_source_id"])),
        _identity(item["data_source_version"]),
        unit,
        point_unit,
        intervals,
        _text(item["timezone"]),
        _identity(item["expiry_mode"]),
        references,
        policies,
        input_digest,
        policy.payload_sha256,
        plugins.payload_sha256,
        fingerprint,
        json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(),
        tuple(
            _identity(item[name])
            for name in ("base_currency", "quote_currency", "settlement_currency")
        ),
        plugins.build_sha256,
        utc(envelope["authored_at"]),
    )
