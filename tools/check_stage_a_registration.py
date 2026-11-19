"""Replay signed schema registration and prove sixth-instrument configuration-only onboarding."""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from tools.create_stage_a_registration_fixtures import REGISTRATION_NAMESPACE, build_artifacts
from v3.offline.contract_listing_registry import (
    FixtureRegistrationRegistry,
    assess_fixture_listing,
    load_fixture_outcome,
)
from v3.offline.data_intake_schema import load_snapshot_fixture
from v3.offline.effective_policy import load_fixture_tiers
from v3.offline.fixture_policy_loader import load_intake_policy, read_fixture_directory
from v3.offline.instrument_definition import load_definition_inputs, load_instrument_definition
from v3.offline.intent_identity import (
    Digest,
    Identity,
    InstrumentId,
    MarketId,
    RunContext,
    RunId,
    SimulatedAccountId,
)
from v3.offline.plugin_manifest import load_plugin_manifest

ROOT = Path(__file__).resolve().parents[1]
AT = datetime(2027, 3, 15, 12, 0, 5, tzinfo=UTC)
RUN = RunId("SYNTHETIC_RUN_001")
ACCOUNT = SimulatedAccountId("SIMULATED_ACCOUNT")


def raw_bundle(name):
    if name.startswith("a5/"):
        name = REGISTRATION_NAMESPACE + name.removeprefix("a5")
    folder = ROOT / "fixtures/stage_a" / name
    public = json.loads((ROOT / "evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json").read_text())
    key = bytes.fromhex(public["public_key_hex"])
    if hashlib.sha256(key).hexdigest() != public["sha256"]:
        raise ValueError("Pinned public key fingerprint mismatch")
    return (
        (folder / "payload.json").read_bytes(),
        (folder / "manifest.json").read_bytes(),
        bytes.fromhex((folder / "manifest.sig").read_text()),
        key,
    )


def bundle(name):
    policy_bundle = raw_bundle("a5/intake/" + name.replace("/", "_"))
    policy = load_intake_policy(*policy_bundle)
    files = read_fixture_directory(policy, policy_bundle[3], RUN, ACCOUNT, AT)
    return files.payload, files.manifest, files.signature, policy_bundle[3]


def foundations():
    artifacts = build_artifacts()
    plugins = load_plugin_manifest(*bundle("a5/plugins"), artifacts)
    inputs = load_definition_inputs(*bundle("a5/inputs"))
    policy = load_fixture_tiers(*raw_bundle("a3"))
    return artifacts, plugins, inputs, policy


def profile(instrument, plugins, inputs, policy):
    snapshot = load_snapshot_fixture(*bundle("a5/snapshots/" + instrument))
    context = RunContext(
        RUN,
        ACCOUNT,
        MarketId("SYNTHETIC_MARKET"),
        InstrumentId(instrument),
        policy.policy_id,
        policy.payload_sha256,
        plugins.build_sha256,
        Digest(snapshot.lineage.snapshot_sha256),
        inputs.feature_schema_sha256,
        Identity(snapshot.clock.source_clock_id),
        policy.valid_from,
        policy.valid_until,
    )
    definition = load_instrument_definition(
        *bundle("a5/definitions/" + instrument),
        plugins,
        inputs,
        policy,
        context,
        snapshot,
    )
    return snapshot, context, definition


def inventory():
    paths = sorted((ROOT / "v3").rglob("*.py"))
    paths += sorted((ROOT / "fixtures/stage_a" / REGISTRATION_NAMESPACE / "plugins").iterdir())
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    }


def registration_proof():
    _, plugins, inputs, policy = foundations()
    registry = FixtureRegistrationRegistry()
    before = inventory()
    outcomes = []
    for instrument in inputs.instruments:
        snapshot, context, definition = profile(instrument, plugins, inputs, policy)
        listing = assess_fixture_listing(
            *bundle("a5/listings/" + instrument),
            definition,
            context,
            snapshot.clock.at,
        )
        if not listing.complete_fixture_data:
            raise ValueError("Fixture listing proof failed: " + listing.reason)
        outcome = load_fixture_outcome(
            *bundle("a5/outcomes/" + instrument),
            definition,
            listing,
            context,
            snapshot.clock.at,
        )
        event = registry.register(
            *bundle("a5/commands/" + instrument),
            definition,
            context,
            snapshot.clock.at,
        )
        if (
            registry.register(
                *bundle("a5/commands/" + instrument),
                definition,
                context,
                snapshot.clock.at,
            )
            != event
        ):
            raise ValueError("Exact signed command replay is not idempotent")
        outcomes.append(
            {
                "instrument": instrument,
                "definition": definition.effective_config_sha256.value,
                "listing": listing.listing_sha256.value,
                "outcome": outcome.payload_sha256.value,
                "event": asdict(event),
                "data": "COMPLETED_FIXTURE_ONLY",
                "authority": "NO_ENTRY_NO_BROKER_NO_MODEL_APPROVAL",
                "interval_seconds": snapshot.calendar.interval_seconds,
                "session_close": snapshot.calendar.session_close,
                "decision_at": snapshot.clock.at,
            }
        )
    after = inventory()
    if len(outcomes) != 6 or outcomes[-1]["instrument"] != "SYNTHETIC_6" or before != after:
        raise ValueError("Sixth definition/fixture-only onboarding or byte-identity proof failed")
    if (
        outcomes[-1]["interval_seconds"] != 86400
        or outcomes[-1]["decision_at"] <= outcomes[-1]["session_close"]
    ):
        raise ValueError("Daily configuration-only post-close registration proof failed")
    return {
        "status": "PASS",
        "initial_profiles": 5,
        "added_profiles": 1,
        "registered_profiles": 6,
        "daily_post_close_profiles": 1,
        "runtime_source_and_plugin_manifest_bytes_changed": 0,
        "before_sha256": before,
        "after_sha256": after,
        "profiles": outcomes,
        "registry_event_count": len(registry.events),
        "registry_scope": "PROCESS_LOCAL_SCHEMA_FOUNDATIONS_NOT_OPERATIONAL_AUTHORITY",
    }


def main():
    print(json.dumps(registration_proof(), sort_keys=True, indent=2, default=str))


if __name__ == "__main__":
    main()
