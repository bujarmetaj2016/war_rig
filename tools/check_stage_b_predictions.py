"""Replay signed current-build packets through bounded intake and both prediction sources."""

import hashlib
import json
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from tools.check_stage_a_registration import ACCOUNT, AT, RUN
from tools.create_stage_a_registration_fixtures import build_artifacts
from v3.offline.data_intake_schema import load_snapshot_fixture
from v3.offline.fixture_policy_loader import load_intake_policy, read_fixture_directory
from v3.offline.intent_identity import (
    Digest,
    Identity,
    InstrumentId,
    MarketId,
    PolicyId,
    RunContext,
)
from v3.offline.macro_features import attach_observation, compute_macro_observation
from v3.offline.model_intake import synthetic_reader_provider
from v3.offline.offline_scenario_runner import (
    ScoreProvider,
    canonical,
    evaluate_prediction,
    grouped_report,
    load_confidence_policy,
    load_feature_row,
    load_prediction_plugins,
    load_run_manifest,
    signed_score_provider,
    v2_confidence_observation,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures/stage_a/b3_prediction"


def raw(name):
    folder = FIXTURES / name
    public = json.loads((ROOT / "evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json").read_text())
    key = bytes.fromhex(public["public_key_hex"])
    if hashlib.sha256(key).hexdigest() != public["sha256"]:
        raise ValueError("Pinned development fixture key mismatch")
    return (
        (folder / "payload.json").read_bytes(),
        (folder / "manifest.json").read_bytes(),
        bytes.fromhex((folder / "manifest.sig").read_text()),
        key,
    )


def bundle(name):
    policy_bundle = raw("intake/" + name.replace("/", "_"))
    policy = load_intake_policy(*policy_bundle)
    files = read_fixture_directory(policy, policy_bundle[3], RUN, ACCOUNT, AT)
    return files.payload, files.manifest, files.signature, policy_bundle[3]


def prediction_proof():
    inventory = tuple(str(path.relative_to(ROOT)) for path in (ROOT / "v3").rglob("*.py"))
    plugins = load_prediction_plugins(*bundle("plugins"), build_artifacts(source_paths=inventory))
    policy = load_confidence_policy(*bundle("confidence"))
    model = synthetic_reader_provider(bundle("model_manifest"), bundle("model_artifacts"), plugins)
    scores, audits, observations = [], [], []
    for instrument in ("XAUUSD", "GER40", "US500", "EURUSD", "GBPUSD", "SYNTHETIC_6"):
        prefix = "profiles/" + instrument
        snapshot = load_snapshot_fixture(*bundle(prefix + "_snapshot"))
        context = RunContext(
            RUN,
            ACCOUNT,
            MarketId("SYNTHETIC_MARKET"),
            InstrumentId(instrument),
            PolicyId("SYNTHETIC_POLICY"),
            Digest(policy.sha256),
            plugins.build_sha256,
            Digest(snapshot.lineage.snapshot_sha256),
            Digest(snapshot.binding.feature_schema_sha256),
            Identity(snapshot.clock.source_clock_id),
            AT - timedelta(days=1),
            AT + timedelta(days=1),
        )
        row = load_feature_row(*bundle(prefix + "_feature"), snapshot, context)
        model_run = load_run_manifest(*bundle(prefix + "_model_run"))
        provider = (
            ScoreProvider(model.kind, model.sha256, model.score)
            if instrument == "SYNTHETIC_6"
            else None
        )
        result = evaluate_prediction(
            provider,
            row,
            model_run,
            policy,
            AT,
            runtime_profile="G1_R",
            data_quality=Decimal("0.8"),
            climate=None,
            conservative_cap=Decimal("0.15"),
        )
        audits.append(asdict(result.audit))
        if instrument == "SYNTHETIC_6":
            if result.score is None:
                raise ValueError("Synthetic model mechanics failed: " + result.audit.reason)
            scores.append(result.score)
        elif result.score is not None or result.audit.status != "NO_AUTHORITATIVE_PREDICTION":
            raise ValueError("Real Core-5 model source did not deny")
        if instrument in ("EURUSD", "GBPUSD"):
            table = signed_score_provider(bundle(prefix + "_scores"), plugins)
            run = load_run_manifest(*bundle(prefix + "_score_run"))
            valid = evaluate_prediction(
                ScoreProvider(table.kind, table.sha256, table.score),
                row,
                run,
                policy,
                AT,
                runtime_profile="G1_R",
                data_quality=Decimal("0.8"),
                climate=None,
                conservative_cap=Decimal("0.15"),
            )
            if valid.score is None:
                raise ValueError("Registered signed test source failed: " + valid.audit.reason)
            observation = compute_macro_observation(
                *bundle(prefix + "_macro"),
                instrument=instrument,
                direction=valid.score.direction,
                entry_at=AT,
                snapshot_sha256=row.snapshot_sha256,
            )
            attached = attach_observation(valid.score, observation)
            if (
                attached.prediction.encoded != valid.score.encoded
                or observation.basket != "AGAINST"
            ):
                raise ValueError("Macro changed prediction or basket fixture failed")
            scores.append(valid.score)
            audits.append(asdict(valid.audit))
            observations.append(asdict(observation))
    return {
        "status": "PASS",
        "scope": "SIGNED_SYNTHETIC_MECHANICS_ONLY_NOT_MODEL_ELIGIBILITY",
        "build_sha256": plugins.build_sha256.value,
        "core5_model_denials": 5,
        "signed_score_predictions": 2,
        "synthetic_reader_predictions": 1,
        "source_reports": {
            kind: [json.loads(value) for value in values]
            for kind, values in grouped_report(tuple(scores))
        },
        "prediction_audits": audits,
        "macro_observations": observations,
        "v2_reference_only": asdict(
            v2_confidence_observation("GBPUSD", Decimal("0.8"), Decimal(40))
        ),
        "lifecycle_or_performance_claim": "NONE; D/E/F integration remains separately gated",
    }


if __name__ == "__main__":
    print(canonical(prediction_proof()).decode())
