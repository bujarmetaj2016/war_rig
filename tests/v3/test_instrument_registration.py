import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from test_fixture_policy_loader import signed

from tools.check_stage_a_registration import (
    ACCOUNT,
    AT,
    RUN,
    bundle,
    foundations,
    profile,
    raw_bundle,
    registration_proof,
)
from tools.create_stage_a_registration_fixtures import build_artifacts
from v3.offline.calendar_completion import parse_utc
from v3.offline.contract_listing_registry import (
    FixtureRegistrationRegistry,
    assess_fixture_listing,
    load_fixture_outcome,
)
from v3.offline.data_intake_schema import load_snapshot_fixture
from v3.offline.effective_policy import load_fixture_tiers
from v3.offline.instrument_definition import (
    DEFINITION_FIELDS,
    POLICY_FIELDS,
    REFERENCE_FIELDS,
    InstrumentDefinition,
    definition_fingerprint,
    load_definition_inputs,
    load_instrument_definition,
)
from v3.offline.intent_identity import (
    Digest,
    Identity,
    InstrumentId,
    MarketId,
    PriceUnit,
    RunContext,
)
from v3.offline.plugin_manifest import build_fingerprint, load_plugin_manifest


def resign(value):
    return signed(
        policy=value, manifest_updates={"max_bytes": 65536, "max_depth": 16, "max_nodes": 2048}
    )


def value(name):
    return json.loads(bundle("a5/" + name)[0])


@pytest.fixture
def ready():
    artifacts, plugins, inputs, policy = foundations()
    snapshot, context, definition = profile("XAUUSD", plugins, inputs, policy)
    return artifacts, plugins, inputs, policy, snapshot, context, definition


def definition_load(record, ready, **changes):
    _, plugins, inputs, policy, snapshot, context, _ = ready
    args = {
        "plugins": plugins,
        "inputs": inputs,
        "policy": policy,
        "context": context,
        "snapshot": snapshot,
    }
    args.update(changes)
    return load_instrument_definition(*resign(record), **args)


def test_sixth_instrument_requires_no_source_or_plugin_manifest_change():
    proof = registration_proof()
    assert proof["registered_profiles"] == 6
    assert proof["runtime_source_and_plugin_manifest_bytes_changed"] == 0
    assert proof["before_sha256"] == proof["after_sha256"]
    assert proof["profiles"][-1]["instrument"] == "SYNTHETIC_6"
    assert all(row["data"] == "COMPLETED_FIXTURE_ONLY" for row in proof["profiles"])


def test_definition_is_full_closed_immutable_and_digest_excludes_only_its_own_field(ready):
    _, plugins, _, policy, _, _, definition = ready
    body = json.loads(definition.canonical)
    assert set(body) == DEFINITION_FIELDS
    expected_body = {key: value for key, value in body.items() if key != "effective_config_sha256"}
    expected = hashlib.sha256(
        json.dumps(
            {
                "definition": expected_body,
                "plugin_manifest": plugins.payload_sha256.value,
                "policy": policy.payload_sha256.value,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()
    assert expected == definition.effective_config_sha256.value
    body["effective_config_sha256"] = "0" * 64
    assert (
        definition_fingerprint(body, plugins.payload_sha256, policy.payload_sha256).value
        == expected
    )
    with pytest.raises(FrozenInstanceError):
        definition.timezone = "UTC"
    assert not hasattr(definition, "live_approved")


@pytest.mark.parametrize("field", sorted(DEFINITION_FIELDS))
def test_every_required_definition_field_cannot_be_omitted(field, ready):
    record = value("definitions/XAUUSD")
    del record["definition"][field]
    with pytest.raises(ValueError):
        definition_load(record, ready)


@pytest.mark.parametrize(
    "field",
    [
        "size_unit",
        "point_value",
        "margin_factor",
        "broker_product_id",
        "expiry_timestamp",
        "last_trade_timestamp",
        "live_approved",
        "demo_enabled",
        "outcome_sha256",
        "equity",
    ],
)
def test_economics_outcomes_and_authority_cannot_enter_stable_definition(field, ready):
    record = value("definitions/XAUUSD")
    record["definition"][field] = "UNTRUSTED"
    with pytest.raises(ValueError):
        definition_load(record, ready)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("schema_version", "0.9.0"),
        ("asset_class", "UNKNOWN"),
        ("instrument_type", "IG_AUTO"),
        ("expiry_mode", "UNKNOWN"),
        ("base_currency", "ZZZ"),
        ("deny_market_entry", True),
        ("deny_market_entry", "false"),
        ("model_artifact_sha256", "0" * 64),
        ("model_fit_record_id", "UNREGISTERED_FIT"),
        ("data_source_id", "UNREGISTERED"),
        ("data_source_version", "2.0.0"),
        ("intervals", []),
        ("intervals", [0]),
        ("intervals", [300, 300]),
        (
            "strategy_parameters",
            {"minimum_rr": {"BULLISH": "3", "BEARISH": "3"}, "entry_type": "LIMIT"},
        ),
        (
            "strategy_parameters",
            {"minimum_rr": {"BULLISH": "2", "BEARISH": "3"}, "entry_type": "MARKET"},
        ),
        (
            "strategy_parameters",
            {"minimum_rr": {"BULLISH": None, "BEARISH": "3"}, "entry_type": "MARKET"},
        ),
        (
            "strategy_parameters",
            {"minimum_rr": {"BULLISH": "11", "BEARISH": "3"}, "entry_type": "MARKET"},
        ),
        ("direction_eligibility_policy_id", None),
        ("risk_policy_id", "FAKE_RISK"),
        ("definition_input_evidence_manifest_sha256", "0" * 64),
        ("criteria_hash", "0" * 64),
        ("feature_schema_hash", "0" * 64),
        ("broker_id", "IG"),
        ("broker_account_scope_id", "SIMULATED_OTHER"),
        ("cost_schedule_ref", "LATER_OUTCOME"),
        ("portfolio_group_id", "UNREGISTERED_GROUP"),
        ("effective_config_sha256", "0" * 64),
        ("timezone", "Not/AZone"),
        (
            "contract_unit",
            {"dimension": "REFERENCE_POINT", "currency": "USD", "precision": 5, "increment": None},
        ),
    ],
)
def test_invalid_signed_definition_never_registers(field, bad, ready):
    record = value("definitions/XAUUSD")
    record["definition"][field] = bad
    if field != "effective_config_sha256":
        record["definition"]["effective_config_sha256"] = definition_fingerprint(
            record["definition"],
            ready[1].payload_sha256,
            ready[3].payload_sha256,
        ).value
    with pytest.raises(ValueError):
        definition_load(record, ready)


@pytest.mark.parametrize("change", ["bar", "price", "forming", "source", "clock", "schema"])
def test_source_context_and_completed_data_cannot_substitute(change, ready):
    snapshot, context = ready[4:6]
    if change == "bar":
        snapshot = replace(snapshot, bar=None)
    elif change == "price":
        snapshot = replace(snapshot, bar=replace(snapshot.bar, price=None))
    elif change == "forming":
        snapshot = replace(snapshot, bar=replace(snapshot.bar, complete=False))
    elif change == "source":
        context = replace(context, source_sha256=Digest("0" * 64))
    elif change == "clock":
        context = replace(context, clock_id=Identity("OTHER_CLOCK"))
    else:
        context = replace(context, feature_schema_sha256=Digest("0" * 64))
    with pytest.raises(ValueError):
        definition_load(value("definitions/XAUUSD"), ready, snapshot=snapshot, context=context)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("definition_sha256", "0" * 64),
        ("qualification", "BROKER_CERTIFIED"),
        ("currencies", ["bad"]),
        ("observed_at", "2028-01-01T00:00:00Z"),
        ("baseline_cost_assumption", None),
        ("timezones", {}),
        ("timezones", []),
        ("timezones", {"NotAZone": {"version": "2026f", "tzif_sha256": "0" * 64}}),
    ],
)
def test_input_manifest_is_preexisting_acyclic_and_not_outcome_or_broker_authority(field, bad):
    record = value("inputs")
    record[field] = bad
    with pytest.raises(ValueError):
        load_definition_inputs(*resign(record))


@pytest.mark.parametrize(
    "field,bad",
    [
        ("plugin_id", "DUPLICATE"),
        ("interface_id", "IG_TRANSPORT"),
        ("source_import_path", "reference.v2_snapshot"),
        ("capabilities", ["NETWORK"]),
        ("version", "2.0.0"),
        ("schema_version", "0.9.0"),
        ("artifact_sha256", "0" * 64),
        ("permitted_build_id", "0" * 64),
        ("dependencies", []),
        ("dependencies", None),
    ],
)
def test_signed_manifest_cannot_widen_build_or_capabilities(field, bad, ready):
    record = value("plugins")
    if field == "plugin_id":
        record["entries"].append(copy.deepcopy(record["entries"][0]))
    else:
        record["entries"][0][field] = bad
    with pytest.raises(ValueError):
        load_plugin_manifest(*resign(record), ready[0])


@pytest.mark.parametrize("entries", [None, []])
def test_absent_plugin_registry_and_missing_or_duplicate_build_deny(entries, ready):
    record = value("plugins")
    record["entries"] = entries
    with pytest.raises(ValueError):
        load_plugin_manifest(*resign(record), ready[0])
    with pytest.raises(ValueError):
        build_fingerprint(())
    with pytest.raises(ValueError):
        build_fingerprint(ready[0] + ready[0])


@pytest.mark.parametrize(
    "field,bad", [("kind", "OWNER_PLUGIN_MANIFEST"), ("build_sha256", "0" * 64)]
)
def test_manifest_domain_and_actual_build_are_not_advisory(field, bad, ready):
    record = value("plugins")
    record[field] = bad
    with pytest.raises(ValueError):
        load_plugin_manifest(*resign(record), ready[0])


def listing_load(record, ready, **changes):
    args = {"definition": ready[6], "context": ready[5], "at": AT}
    args.update(changes)
    return assess_fixture_listing(*resign(record), **args)


def rehash_listing(record, *, fields=True):
    def digest(value):
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    if fields:
        for field in record["evidence_index"]["fields"]:
            field["content_sha256"] = digest(
                {k: v for k, v in field.items() if k != "content_sha256"}
            )
    index = digest(record["evidence_index"])
    record["listing"].update(per_field_evidence_index_sha256=index, economics_revision_sha256=index)
    record["listing"]["listing_sha256"] = digest(
        {k: v for k, v in record["listing"].items() if k != "listing_sha256"}
    )


@pytest.mark.parametrize(
    "change",
    [
        "status",
        "account",
        "family",
        "product",
        "revision",
        "stale",
        "future",
        "units",
        "conversion",
        "missing",
        "duplicate",
        "id",
        "field_account",
        "field_product",
        "field_status",
        "field_actor",
        "field_digest",
        "field_future",
        "field_stale",
        "zero",
        "unknown_stop",
        "unknown_market",
        "point_unit",
        "cash_expiry",
        "expired",
        "missing_expiry",
        "unknown_currency",
    ],
)
def test_listing_requires_exact_current_per_field_evidence_with_no_definition_fallback(
    change, ready
):
    record = value("listings/XAUUSD")
    listing, index = record["listing"], record["evidence_index"]
    first = index["fields"][0]
    fields = {item["field"]: item for item in index["fields"]}
    definition = ready[6]
    if change == "status":
        listing["status"] = "UNKNOWN"
    elif change == "account":
        listing["account_scope_id"] = "SIMULATED_OTHER"
    elif change == "family":
        listing["product_family_id"] = "OTHER"
    elif change == "product":
        index["product_id"] = "OTHER"
    elif change == "revision":
        listing["economics_revision_sha256"] = "0" * 64
    elif change == "stale":
        listing["observed_at"] = "2027-03-15T11:00:00Z"
    elif change == "future":
        listing["observed_at"] = "2027-03-15T13:00:00Z"
    elif change == "units":
        index["source_price_unit"] = "BROKER_STAKE"
    elif change == "conversion":
        index["point_conversion"] = None
    elif change == "missing":
        index["fields"].pop()
    elif change == "duplicate":
        index["fields"].append(copy.deepcopy(first))
    elif change == "id":
        index["fields"][1]["evidence_id"] = first["evidence_id"]
    elif change == "field_account":
        first["account_id"] = "SIMULATED_OTHER"
    elif change == "field_product":
        first["product_id"] = "OTHER"
    elif change == "field_status":
        first["status"] = "UNKNOWN"
    elif change == "field_actor":
        first["actor"] = "SIGNAL_RUNTIME"
    elif change == "field_digest":
        first["content_sha256"] = "0" * 64
    elif change == "field_future":
        first["available_at"] = "2027-03-15T13:00:00Z"
    elif change == "field_stale":
        first["observed_at"] = "2027-03-15T11:00:00Z"
    elif change == "zero":
        fields["point_value"]["value"] = "0"
    elif change == "unknown_stop":
        fields["stop_capability"]["value"] = "UNKNOWN"
    elif change == "unknown_market":
        fields["market_status"]["value"] = "UNKNOWN"
    elif change == "point_unit":
        fields["point_value"]["unit"] = "USD_PER_UNKNOWN"
    elif change == "unknown_currency":
        fields["settlement_currency"]["value"] = "ZZZ"
    elif change in {"cash_expiry", "expired"}:
        listing["expiry_timestamp"] = "2027-03-15T11:00:00Z"
        listing["last_trade_timestamp"] = "2027-03-15T10:00:00Z"
        fields["expiry_timestamp"]["value"] = listing["expiry_timestamp"]
        fields["last_trade_timestamp"]["value"] = listing["last_trade_timestamp"]
        if change == "expired":
            definition = replace(definition, expiry_mode="EXPIRING")
    else:
        definition = replace(definition, expiry_mode="EXPIRING")
    if change != "revision":
        rehash_listing(record, fields=change != "field_digest")
    assert not listing_load(record, ready, definition=definition).complete_fixture_data


def test_listing_bad_field_shape_and_valid_expiring_fixture(ready):
    record = value("listings/XAUUSD")
    record["evidence_index"]["fields"] = None
    rehash_listing(record, fields=False)
    with pytest.raises(ValueError):
        listing_load(record, ready)
    record = value("listings/XAUUSD")
    for field in record["evidence_index"]["fields"]:
        if field["field"] in {"expiry_timestamp", "last_trade_timestamp"}:
            field["value"] = "2027-03-16T12:00:00Z"
            record["listing"][field["field"]] = field["value"]
    rehash_listing(record)
    assert listing_load(
        record, ready, definition=replace(ready[6], expiry_mode="EXPIRING")
    ).complete_fixture_data


@pytest.mark.parametrize(
    "field,bad",
    [
        ("actor", "SIGNAL_RUNTIME"),
        ("kind", "LIVE_APPROVAL"),
        ("expected_version", 1),
        ("expected_previous_sha256", "f" * 64),
        ("account_id", "SIMULATED_OTHER"),
        ("definition_sha256", "0" * 64),
        ("policy_sha256", "0" * 64),
        ("run_id", "OTHER"),
        ("at", "2028-01-01T00:00:00Z"),
    ],
)
def test_registration_rejects_unauthorised_or_stale_expected_state_without_append(
    field, bad, ready
):
    registry = FixtureRegistrationRegistry()
    command = value("commands/XAUUSD")
    command[field] = bad
    with pytest.raises(ValueError):
        registry.register(*resign(command), ready[6], ready[5], AT)
    assert registry.events == ()


def test_registry_conflict_is_atomic_and_replay_reconstructs_same_history(ready):
    registry = FixtureRegistrationRegistry()
    event = registry.register(*bundle("a5/commands/XAUUSD"), ready[6], ready[5], AT)
    command = value("commands/XAUUSD")
    command["at"] = "2027-03-15T12:00:04Z"
    with pytest.raises(ValueError):
        registry.register(*resign(command), ready[6], ready[5], AT)
    assert registry.events == (event,)
    assert registry.register(*bundle("a5/commands/XAUUSD"), ready[6], ready[5], AT) == event
    again = FixtureRegistrationRegistry()
    assert again.register(*bundle("a5/commands/XAUUSD"), ready[6], ready[5], AT) == event
    assert not hasattr(registry, "approve_live")
    assert listing_load(value("listings/XAUUSD"), ready).complete_fixture_data
    assert not listing_load(
        value("listings/XAUUSD"), ready, at=AT + timedelta(days=1)
    ).complete_fixture_data


def typed_registry_fixture():
    """Isolate registry/value guards from the separately tested build-integrity guard."""
    body = value("definitions/XAUUSD")["definition"]
    snapshot = load_snapshot_fixture(*bundle("a5/snapshots/XAUUSD"))
    policy = load_fixture_tiers(*raw_bundle("a3"))
    build = Digest(value("plugins")["build_sha256"])
    context = RunContext(
        RUN,
        ACCOUNT,
        MarketId("SYNTHETIC_MARKET"),
        InstrumentId("XAUUSD"),
        policy.policy_id,
        policy.payload_sha256,
        build,
        Digest(snapshot.lineage.snapshot_sha256),
        Digest(body["feature_schema_hash"]),
        Identity(snapshot.clock.source_clock_id),
        policy.valid_from,
        policy.valid_until,
    )
    unit = PriceUnit(Identity("REFERENCE_POINT"), "USD", 5, Decimal("0.00001"))
    definition = InstrumentDefinition(
        context.instrument,
        Identity(body["broker_product_family_id"]),
        Identity(body["data_source_id"]),
        body["data_source_version"],
        unit,
        unit,
        (300,),
        body["timezone"],
        body["expiry_mode"],
        tuple((name, Identity(body[name])) for name in sorted(REFERENCE_FIELDS)),
        tuple(
            (name, None if body[name] is None else Identity(body[name]))
            for name in sorted(POLICY_FIELDS)
        ),
        Digest(body["definition_input_evidence_manifest_sha256"]),
        policy.payload_sha256,
        Digest(hashlib.sha256(bundle("a5/plugins")[0]).hexdigest()),
        Digest(body["effective_config_sha256"]),
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode(),
        ("USD", "USD", "GBP"),
        build,
        parse_utc(value("definitions/XAUUSD")["authored_at"]),
    )
    return context, definition


def test_expected_state_guard_is_independent_of_build_integrity():
    context, definition = typed_registry_fixture()
    command = value("commands/XAUUSD")
    command["expected_version"] = 1
    registry = FixtureRegistrationRegistry()
    with pytest.raises(ValueError):
        registry.register(*resign(command), definition, context, AT)
    assert registry.events == ()


def test_missing_fee_evidence_cannot_use_an_assumed_definition_value():
    context, definition = typed_registry_fixture()
    record = value("listings/XAUUSD")
    record["evidence_index"]["fields"] = [
        item for item in record["evidence_index"]["fields"] if item["field"] != "fee"
    ]
    rehash_listing(record)
    result = assess_fixture_listing(*resign(record), definition, context, AT)
    assert not result.complete_fixture_data
    assert result.reason == "MISSING_MANDATORY_FIELD"


def test_capability_guard_is_independent_of_exact_source_build_integrity():
    artifacts = build_artifacts()
    build = build_fingerprint(artifacts).value
    sources = {item.module: item for item in artifacts}
    record = value("plugins")
    record["build_sha256"] = build
    for item in record["entries"]:
        actual = sources[item["source_import_path"]]
        item.update(
            permitted_build_id=build,
            artifact_sha256=actual.sha256.value,
            dependencies=list(actual.dependencies),
        )
    record["entries"][0]["capabilities"] = ["NETWORK"]
    with pytest.raises(ValueError):
        load_plugin_manifest(*resign(record), artifacts)


def test_concurrent_configuration_writers_cannot_both_append_the_same_expected_state():
    context, definition = typed_registry_fixture()
    registry = FixtureRegistrationRegistry()
    commands = []
    for event_id in ("RACE_ONE", "RACE_TWO"):
        command = value("commands/XAUUSD")
        command["event_id"] = event_id
        commands.append(resign(command))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(registry.register, *command, definition, context, AT)
            for command in commands
        ]
    assert sum(future.exception() is None for future in futures) == 1
    errors = [future.exception() for future in futures if future.exception() is not None]
    assert len(errors) == 1 and isinstance(errors[0], ValueError)
    assert len(registry.events) == 1 and registry.events[0].version == 1


@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=30))
def test_cosmetic_edits_are_hashed_without_an_owner_selected_exception(name):
    body = value("definitions/XAUUSD")["definition"]
    before = definition_fingerprint(body, Digest("a" * 64), Digest("b" * 64))
    body["display_name"] = "cosmetic-" + name
    assert definition_fingerprint(body, Digest("a" * 64), Digest("b" * 64)) != before


@pytest.mark.parametrize(
    "field,bad",
    [
        ("qualification", "MODEL_APPROVED"),
        ("definition_sha256", "0" * 64),
        ("input_sha256", "0" * 64),
        ("listing_sha256", "0" * 64),
        ("policy_sha256", "0" * 64),
        ("build_sha256", "0" * 64),
        ("observed_at", "2027-01-01T00:00:00Z"),
        ("available_at", "2028-01-01T00:00:00Z"),
        ("prior_outcome_sha256", "0" * 64),
    ],
)
def test_subsequent_outcomes_cannot_rewrite_inputs_or_become_approval(field, bad, ready):
    record = value("outcomes/XAUUSD")
    record[field] = bad
    listing = listing_load(value("listings/XAUUSD"), ready)
    with pytest.raises(ValueError):
        load_fixture_outcome(*resign(record), ready[6], listing, ready[5], AT)
    with pytest.raises(ValueError):
        load_fixture_outcome(
            *bundle("a5/outcomes/XAUUSD"),
            ready[6],
            replace(listing, complete_fixture_data=False),
            ready[5],
            AT,
        )


def test_new_listing_and_forward_outcome_leave_the_family_fingerprint_unchanged(ready):
    original = ready[6]
    listing = value("listings/XAUUSD")
    listing["listing"]["broker_product_id"] = "DATED_XAUUSD_NEXT"
    listing["listing"]["contract_listing_id"] = "LISTING_XAUUSD_NEXT"
    listing["evidence_index"]["product_id"] = "DATED_XAUUSD_NEXT"
    for field in listing["evidence_index"]["fields"]:
        field["product_id"] = "DATED_XAUUSD_NEXT"
    rehash_listing(listing)
    assessed = listing_load(listing, ready)
    assert assessed.complete_fixture_data
    old_assessed = listing_load(value("listings/XAUUSD"), ready)
    assert assessed.listing_sha256 != old_assessed.listing_sha256
    outcome = load_fixture_outcome(
        *bundle("a5/outcomes/XAUUSD"), original, old_assessed, ready[5], AT
    )
    assert outcome.definition_sha256 == original.effective_config_sha256
    assert ready[6] == original and original.canonical == ready[6].canonical
