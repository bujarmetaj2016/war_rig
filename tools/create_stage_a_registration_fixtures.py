"""Build only synthetic A5 schema evidence; no model, broker certificate or promotion."""

import ast
import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.create_stage_a_calendar_fixtures import write_fixture as write_signed
from v3.offline.instrument_definition import POLICY_FIELDS, REFERENCE_FIELDS, definition_fingerprint
from v3.offline.intent_identity import Digest
from v3.offline.plugin_manifest import BuildArtifact, build_fingerprint

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTS = ("XAUUSD", "GER40", "US500", "EURUSD", "GBPUSD", "SYNTHETIC_6")
INTERFACES = (
    ("SYNTHETIC_BARS", "SNAPSHOT_FIXTURE_V1", "data_intake_schema", "SIGNED_SYNTHETIC_DATA"),
    ("COMPLETED", "COMPLETION_V1", "calendar_completion", "PURE_COMPLETION"),
    ("CALENDAR", "CALENDAR_V1", "calendar_completion", "PURE_CALENDAR"),
    ("SYNTHETIC_MACRO", "MACRO_INPUT_V1", "data_intake_schema", "SIGNED_SYNTHETIC_DATA"),
    ("FIXTURE_POLICY", "FIXTURE_PARAMETERS_V1", "effective_policy", "FIXTURE_PARAMETERS"),
)


def write_fixture(name, value, key, *, max_nodes=256):
    write_signed(name, value, key, max_nodes=max_nodes)
    write_signed(
        "a5/intake/" + name.replace("/", "_"),
        {
            "kind": "FIXTURE_INTAKE_POLICY_V1",
            "relative_directory": "stage_a/" + name,
            "max_path_depth": 4,
            "max_files": 3,
            "max_file_bytes": 65536,
            "max_total_bytes": 70000,
            "run_id": "SYNTHETIC_RUN_001",
            "account_id": "SIMULATED_ACCOUNT",
            "valid_from": "2027-01-01T00:00:00Z",
            "valid_until": "2028-01-01T00:00:00Z",
        },
        key,
    )


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def hash_json(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def build_artifacts() -> tuple[BuildArtifact, ...]:
    sources = {
        ".".join(path.relative_to(ROOT).with_suffix("").parts): path
        for path in sorted((ROOT / "v3").rglob("*.py"))
    }
    return tuple(
        BuildArtifact(
            module,
            Digest(hashlib.sha256(path.read_bytes()).hexdigest()),
            tuple(
                sorted(
                    hashlib.sha256(sources[node.module].read_bytes()).hexdigest()
                    for node in ast.walk(ast.parse(path.read_bytes()))
                    if isinstance(node, ast.ImportFrom) and node.module in sources
                )
            ),
        )
        for module, path in sources.items()
    )


def definition_body(instrument, inputs_hash, criteria_hash, plugins_hash, policy_hash):
    unit = {
        "dimension": "REFERENCE_POINT",
        "currency": "USD",
        "precision": 5,
        "increment": "0.00001",
    }
    body = {name: "SYNTHETIC_TIER_POLICY" for name in POLICY_FIELDS}
    for name in (
        "risk_policy_id",
        "protection_policy_id",
        "broker_economics_bounds_policy_id",
        "portfolio_candidate_priority_policy_id",
        "model_use_policy_id",
        "contract_selection_policy_id",
        "rollover_policy_id",
    ):
        body[name] = None
    body.update(
        {
            "schema_version": "1.0.0",
            "instrument_id": instrument,
            "display_name": "SYNTHETIC " + instrument + " NOT REAL ECONOMICS",
            "asset_class": "OTHER",
            "base_currency": "USD",
            "quote_currency": "USD",
            "settlement_currency": "GBP",
            "contract_unit": unit,
            "point_unit": unit,
            "data_source_id": "SYNTHETIC_BARS",
            "data_source_version": "1.0.0",
            "price_instrument_id": instrument,
            "intervals": [300],
            "completion_rule_id": "COMPLETED",
            "calendar_rule_id": "CALENDAR",
            "timezone": "Europe/London",
            "session_profile_id": "FIXTURE_LONDON",
            "macro_profile_id": "FIXTURE_MACRO",
            "macro_feature_refs": ["SYNTHETIC_MACRO"],
            "strategy_plugin_id": "FIXTURE_POLICY",
            "strategy_version": "1.0.0",
            "strategy_parameters": {
                "minimum_rr": {"BULLISH": "3", "BEARISH": "3"},
                "entry_type": "MARKET",
            },
            "feature_schema_hash": "2" * 64,
            "model_artifact_sha256": None,
            "model_fit_record_id": None,
            "broker_id": "OFFLINE_SIMULATOR",
            "broker_product_family_id": "FAMILY_" + instrument,
            "broker_account_scope_id": "SIMULATED_ACCOUNT",
            "instrument_type": "OTHER",
            "cost_schedule_ref": "FIXTURE_BASELINE_INPUT",
            "market_status_mapping_id": "FIXTURE_STATUS",
            "expiry_mode": "CASH",
            "deny_market_entry": False,
            "definition_input_evidence_manifest_sha256": inputs_hash,
            "portfolio_group_id": "FIXTURE_GROUP",
            "calendar_constraints": {
                "not_before": "2027-01-01T00:00:00Z",
                "not_after": "2028-01-01T00:00:00Z",
            },
            "evaluation_criteria_id": "FIXTURE_SCHEMA_CRITERIA",
            "criteria_hash": criteria_hash,
            "audit_schema_id": "FIXTURE_AUDIT_V1",
        }
    )
    body["effective_config_sha256"] = definition_fingerprint(
        body, Digest(plugins_hash), Digest(policy_hash)
    ).value
    return body


def listing_body(instrument):
    fields = {
        "size_unit": ("GBP_PER_POINT", "ENUM"),
        "stake_increment": ("0.5", "GBP_PER_POINT"),
        "min_stake": ("0", "GBP_PER_POINT"),
        "point_value": ("1", "GBP_PER_REFERENCE_POINT"),
        "min_stop_distance": ("1", "REFERENCE_POINT"),
        "margin_factor": ("0.05", "RATIO"),
        "margin_currency": ("GBP", "ISO4217"),
        "settlement_currency": ("GBP", "ISO4217"),
        "contract_size": ("1", "REFERENCE_POINT"),
        "price_step": ("0.00001", "REFERENCE_POINT"),
        "spread": ("0.00002", "REFERENCE_POINT"),
        "fee": ("0", "GBP"),
        "stop_capability": ("ATTACHED_STOP", "ENUM"),
        "market_status": ("OPEN", "ENUM"),
        "expiry_timestamp": ("NONE", "UTC"),
        "last_trade_timestamp": ("NONE", "UTC"),
        "margin_treatment": ("GROSS", "ENUM"),
        "session": ("OPEN", "ENUM"),
    }
    records = []
    product = "DATED_" + instrument
    for name, (value, unit) in sorted(fields.items()):
        record = {
            "field": name,
            "value": value,
            "unit": unit,
            "evidence_id": "EVIDENCE_" + name,
            "source": "FIXTURE_BROKER_EQUIVALENT_NOT_IG",
            "observed_at": "2027-03-15T12:00:00Z",
            "available_at": "2027-03-15T12:00:01Z",
            "account_id": "SIMULATED_ACCOUNT",
            "product_id": product,
            "status": "FIXTURE_VERIFIED",
            "actor": "FIXTURE_ECONOMICS_ATTESTOR",
        }
        record["content_sha256"] = hash_json(record)
        records.append(record)
    index = {
        "kind": "FIXTURE_ECONOMICS_INDEX_V1",
        "account_id": "SIMULATED_ACCOUNT",
        "product_id": product,
        "max_age_seconds": 60,
        "source_price_unit": "REFERENCE_POINT",
        "source_currency": "USD",
        "point_conversion": "1",
        "fields": records,
    }
    listing = {
        "contract_listing_id": "LISTING_" + instrument,
        "product_family_id": "FAMILY_" + instrument,
        "broker_product_id": product,
        "expiry_timestamp": None,
        "last_trade_timestamp": None,
        "status": "ACTIVE",
        "account_scope_id": "SIMULATED_ACCOUNT",
        "per_field_evidence_index_sha256": hash_json(index),
        "economics_revision_sha256": hash_json(index),
        "observed_at": "2027-03-15T12:00:00Z",
    }
    listing["listing_sha256"] = hash_json(listing)
    return {"kind": "FIXTURE_CONTRACT_LISTING_V1", "listing": listing, "evidence_index": index}


def main():
    key = serialization.load_pem_private_key(
        (ROOT / "keys/dev_fixture_signing.key").read_bytes(), password=None
    )
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Existing Ed25519 fixture key required")
    public = json.loads((ROOT / "evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json").read_text())
    if key.public_key().public_bytes_raw().hex() != public["public_key_hex"]:
        raise ValueError("Pinned development signer mismatch")
    artifacts = build_artifacts()
    build = build_fingerprint(artifacts).value
    source = {item.module: item for item in artifacts}
    entries = []
    for plugin_id, interface, module, capability in INTERFACES:
        path = "v3.offline." + module
        entries.append(
            {
                "plugin_id": plugin_id,
                "interface_id": interface,
                "version": "1.0.0",
                "artifact_sha256": source[path].sha256.value,
                "schema_version": "1.0.0",
                "capabilities": [capability],
                "source_import_path": path,
                "permitted_build_id": build,
                "dependencies": list(source[path].dependencies),
            }
        )
    plugins = {"kind": "FIXTURE_PLUGIN_MANIFEST_V1", "build_sha256": build, "entries": entries}
    write_fixture("a5/plugins", plugins, key)
    policy_hash = hashlib.sha256(
        (ROOT / "fixtures/stage_a/a3/payload.json").read_bytes()
    ).hexdigest()
    criteria = "SCHEMA_AND_COMPLETED_SOURCE_ONLY_NOT_PROMOTION"
    bodies = [
        definition_body(item, "0" * 64, "0" * 64, hash_json(plugins), policy_hash)
        for item in INSTRUMENTS
    ]
    calendar = json.loads((ROOT / "fixtures/stage_a/a2/payload.json").read_text())
    inputs = {
        "kind": "FIXTURE_DEFINITION_INPUT_V1",
        "evidence_id": "FIXTURE_BASELINE_INPUT",
        "instrument_ids": list(INSTRUMENTS),
        "currencies": ["USD", "GBP", "EUR"],
        "feature_schema_sha256": "2" * 64,
        "observed_at": "2027-01-01T00:00:00Z",
        "available_at": "2027-01-01T00:00:01Z",
        "qualification": "ASSUMPTION_NOT_BROKER_CERTIFICATION",
        "baseline_cost_assumption": "0",
        "criteria": criteria,
        "timezones": {
            calendar["timezone"]: {
                "version": calendar["timezone_version"],
                "tzif_sha256": hashlib.sha256(
                    base64.b64decode(calendar["timezone_tzif_base64"])
                ).hexdigest(),
            }
        },
        "reference_values": {
            name: sorted({body[name] for body in bodies}) for name in REFERENCE_FIELDS
        },
    }
    write_fixture("a5/inputs", inputs, key)
    previous = "0" * 64
    for index, instrument in enumerate(INSTRUMENTS):
        body = definition_body(
            instrument,
            hash_json(inputs),
            hashlib.sha256(criteria.encode()).hexdigest(),
            hash_json(plugins),
            policy_hash,
        )
        write_fixture(
            "a5/definitions/" + instrument,
            {
                "kind": "FIXTURE_INSTRUMENT_DEFINITION_V1",
                "authored_at": "2027-01-01T00:00:02Z",
                "definition": body,
            },
            key,
        )
        snapshot = json.loads((ROOT / "fixtures/stage_a/a2/payload.json").read_text())
        snapshot.update(
            {
                "instrument_id": instrument,
                "policy_sha256": policy_hash,
                "snapshot_id": "SNAPSHOT_" + instrument,
                "source_event_id": "BAR_" + instrument,
            }
        )
        write_fixture("a5/snapshots/" + instrument, snapshot, key)
        listing = listing_body(instrument)
        write_fixture("a5/listings/" + instrument, listing, key, max_nodes=1024)
        write_fixture(
            "a5/outcomes/" + instrument,
            {
                "kind": "FIXTURE_SCHEMA_OUTCOME_V1",
                "qualification": "SCHEMA_REPLAY_NOT_PERFORMANCE_NOT_APPROVAL",
                "definition_sha256": body["effective_config_sha256"],
                "listing_sha256": listing["listing"]["listing_sha256"],
                "input_sha256": hash_json(inputs),
                "policy_sha256": policy_hash,
                "build_sha256": build,
                "observed_at": "2027-03-15T12:00:05Z",
                "available_at": "2027-03-15T12:00:05Z",
            },
            key,
        )
        command = {
            "kind": "FIXTURE_CONFIG_REGISTRATION_V1",
            "actor": "FIXTURE_CONFIG_CONTROL",
            "event_id": "REGISTER_" + instrument,
            "expected_version": index,
            "expected_previous_sha256": previous,
            "instrument_id": instrument,
            "definition_sha256": body["effective_config_sha256"],
            "run_id": "SYNTHETIC_RUN_001",
            "account_id": "SIMULATED_ACCOUNT",
            "policy_sha256": policy_hash,
            "at": "2027-03-15T12:00:05Z",
        }
        write_fixture("a5/commands/" + instrument, command, key)
        previous = hashlib.sha256(
            (previous + hash_json(command) + str(index + 1)).encode()
        ).hexdigest()
    print("Signed six synthetic schema profiles; no economics/model/promotion authority")


if __name__ == "__main__":
    main()
