"""Sign hand-authored Stage B fixtures; never learn weights or derive golden outputs."""

import hashlib
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "b3_prediction"
sys.path.insert(0, str(ROOT / "tests/v3"))

# Independent test-fixture constants, not evaluator-generated reference outputs.
from test_completed_snapshots import record as snapshot_record  # noqa: E402
from test_macro_features import macro_body  # noqa: E402
from test_model_intake import model_fixture  # noqa: E402
from test_prediction_pipeline import (  # noqa: E402
    POLICY,
    feature_bundle,
    plugin_body,
)

from v3.offline.offline_scenario_runner import SourceKind, canonical  # noqa: E402


def write(name, value, key, *, intake=True):
    folder = ROOT / "fixtures/stage_a" / NAMESPACE / name
    folder.mkdir(parents=True, exist_ok=True)
    if any(folder.iterdir()):
        raise ValueError("Refusing to overwrite an existing signed Stage B fixture")
    payload = canonical(value)
    manifest = canonical(
        {
            "schema_version": 1,
            "domain": "FIXTURE_ONLY",
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "max_bytes": 1048576,
            "max_depth": 16,
            "max_nodes": 10000,
        }
    )
    (folder / "payload.json").write_bytes(payload)
    (folder / "manifest.json").write_bytes(manifest)
    (folder / "manifest.sig").write_text(
        key.sign(b"WAR_RIG_DEV_FIXTURE_V1\x00" + manifest).hex() + "\n"
    )
    if intake:
        policy = {
            "kind": "FIXTURE_INTAKE_POLICY_V1",
            "relative_directory": "stage_a/" + NAMESPACE + "/" + name,
            "max_path_depth": 4,
            "max_files": 3,
            "max_file_bytes": 1048576,
            "max_total_bytes": 1052801,
            "run_id": "SYNTHETIC_RUN_001",
            "account_id": "SIMULATED_ACCOUNT",
            "valid_from": "2027-01-01T00:00:00Z",
            "valid_until": "2028-01-01T00:00:00Z",
        }
        write("intake/" + name.replace("/", "_"), policy, key, intake=False)


def main():
    key = serialization.load_pem_private_key(
        (ROOT / "keys/dev_fixture_signing.key").read_bytes(), password=None
    )
    public = json.loads((ROOT / "evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json").read_text())
    if (
        not isinstance(key, Ed25519PrivateKey)
        or key.public_key().public_bytes_raw().hex() != public["public_key_hex"]
    ):
        raise ValueError("Pinned development fixture signer mismatch")
    model_bundle, files = model_fixture()
    model = json.loads(model_bundle[0])
    write("model_manifest", model, key)
    write(
        "model_artifacts",
        {
            "kind": "SIGNED_MODEL_ARTIFACT_PACKET_V1",
            "files": {name: raw.decode() for name, raw in files},
        },
        key,
    )
    write("plugins", plugin_body()[0], key)
    write("confidence", POLICY, key)
    schema = model["feature_schema_sha256"]
    for instrument in ("XAUUSD", "GER40", "US500", "EURUSD", "GBPUSD", "SYNTHETIC_6"):
        row, snapshot, context, _ = feature_bundle(
            instrument=instrument, schema_sha256=schema if instrument == "SYNTHETIC_6" else "2" * 64
        )
        body = snapshot_record()
        body.update(
            instrument_id=instrument,
            feature_schema_sha256=context.feature_schema_sha256.value,
            policy_sha256=context.policy_sha256.value,
            feature_row_sha256=row["row_sha256"],
        )
        if hashlib.sha256(canonical(body)).hexdigest() != snapshot.lineage.snapshot_sha256:
            raise ValueError("Independent signed snapshot fixture assembly mismatch")
        write("profiles/" + instrument + "_snapshot", body, key)
        write("profiles/" + instrument + "_feature", row, key)
        source_hash = hashlib.sha256(model_bundle[0]).hexdigest()
        run = {
            "kind": "FIXTURE_PREDICTION_RUN_V1",
            "run_id": context.run.value,
            "account_id": context.account.value,
            "runtime_profile": "G1_R",
            "valid_from": str(context.valid_from),
            "valid_until": str(context.valid_until),
            "sources": [
                {
                    "instrument": instrument,
                    "source_kind": "TRAINED_MODEL",
                    "fingerprint": source_hash if instrument == "SYNTHETIC_6" else None,
                }
            ],
        }
        write("profiles/" + instrument + "_model_run", run, key)
        if instrument in ("EURUSD", "GBPUSD"):
            # Only independent constants are signed, never a learned or fitted score.
            score = {
                "kind": "SIGNED_TEST_SCORE_V1",
                "rows": [
                    {
                        "feature_row_sha256": row["row_sha256"],
                        "direction": "BULLISH",
                        "raw": "0.9",
                        "probability": "0.8",
                        "lower_bound": "0.6",
                    }
                ],
            }
            write("profiles/" + instrument + "_scores", score, key)
            run["sources"][0].update(
                source_kind=SourceKind.SIGNED_TEST_SCORE,
                fingerprint=hashlib.sha256(canonical(score)).hexdigest(),
            )
            write("profiles/" + instrument + "_score_run", run, key)
            observation, _ = macro_body(instrument=instrument, trend=1)
            write("profiles/" + instrument + "_macro", observation, key)
    print(
        "Signed fixed Stage B snapshot/feature/source/model/macro fixtures; "
        "no training or authority"
    )


if __name__ == "__main__":
    main()
