"""Check exact coverage, import/source independence and cross-process determinism."""

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "v3/offline/__init__.py",
    "v3/offline/calendar_completion.py",
    "v3/offline/data_intake_schema.py",
    "v3/offline/effective_policy.py",
    "v3/offline/intent_identity.py",
    "v3/offline/fixture_policy_loader.py",
    "v3/offline/plugin_manifest.py",
    "v3/offline/instrument_definition.py",
    "v3/offline/contract_listing_registry.py",
    "v3/offline/offline_scenario_runner.py",
    "v3/offline/model_intake.py",
    "v3/offline/macro_features.py",
}
ALLOWED_IMPORTS = {
    "v3/offline/offline_scenario_runner.py": {
        "hashlib",
        "json",
        "re",
        "collections.abc",
        "dataclasses",
        "datetime",
        "decimal",
        "enum",
        "v3.offline.calendar_completion",
        "v3.offline.data_intake_schema",
        "v3.offline.effective_policy",
        "v3.offline.fixture_policy_loader",
        "v3.offline.intent_identity",
        "v3.offline.plugin_manifest",
    },
    "v3/offline/model_intake.py": {
        "hashlib",
        "json",
        "dataclasses",
        "datetime",
        "decimal",
        "v3.offline.offline_scenario_runner",
        "v3.offline.plugin_manifest",
        "v3.offline.calendar_completion",
        "v3.offline.intent_identity",
        "v3.offline.fixture_policy_loader",
    },
    "v3/offline/macro_features.py": {
        "hashlib",
        "dataclasses",
        "datetime",
        "decimal",
        "statistics",
        "v3.offline.calendar_completion",
        "v3.offline.data_intake_schema",
        "v3.offline.fixture_policy_loader",
        "v3.offline.offline_scenario_runner",
    },
    "v3/__init__.py": set(),
    "v3/offline/__init__.py": set(),
    "v3/offline/plugin_manifest.py": {
        "hashlib",
        "json",
        "dataclasses",
        "v3.offline.data_intake_schema",
        "v3.offline.effective_policy",
        "v3.offline.fixture_policy_loader",
        "v3.offline.intent_identity",
    },
    "v3/offline/instrument_definition.py": {
        "hashlib",
        "json",
        "re",
        "dataclasses",
        "datetime",
        "v3.offline.calendar_completion",
        "v3.offline.data_intake_schema",
        "v3.offline.effective_policy",
        "v3.offline.fixture_policy_loader",
        "v3.offline.intent_identity",
        "v3.offline.plugin_manifest",
    },
    "v3/offline/contract_listing_registry.py": {
        "hashlib",
        "json",
        "dataclasses",
        "datetime",
        "threading",
        "v3.offline.calendar_completion",
        "v3.offline.data_intake_schema",
        "v3.offline.effective_policy",
        "v3.offline.fixture_policy_loader",
        "v3.offline.instrument_definition",
        "v3.offline.intent_identity",
    },
    "v3/offline/calendar_completion.py": {
        "dataclasses",
        "datetime",
        "decimal",
        "enum",
        "io",
        "struct",
        "zoneinfo",
    },
    "v3/offline/data_intake_schema.py": {
        "base64",
        "re",
        "datetime",
        "decimal",
        "v3.offline.calendar_completion",
        "v3.offline.fixture_policy_loader",
    },
    "v3/offline/effective_policy.py": {
        "re",
        "dataclasses",
        "datetime",
        "decimal",
        "enum",
        "v3.offline.calendar_completion",
        "v3.offline.data_intake_schema",
        "v3.offline.fixture_policy_loader",
        "v3.offline.intent_identity",
    },
    "v3/offline/intent_identity.py": {
        "hashlib",
        "json",
        "re",
        "dataclasses",
        "datetime",
        "decimal",
        "v3.offline.calendar_completion",
    },
    "v3/offline/fixture_policy_loader.py": {
        "hashlib",
        "json",
        "re",
        "os",
        "stat",
        "contextlib",
        "pathlib",
        "dataclasses",
        "datetime",
        "enum",
        "cryptography.exceptions",
        "cryptography.hazmat.primitives.asymmetric.ed25519",
        "v3.offline.calendar_completion",
        "v3.offline.intent_identity",
    },
}


def normalized(path: Path) -> list[str]:
    return [
        " ".join(line.split())
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def input_integrity():
    state = json.loads((ROOT / "evidence/STAGE_STATE.json").read_text())
    manifests = (
        ("evidence/macro/MANIFEST.sha256", ROOT, state["macro_research"]["manifest_sha256"], 482),
        ("reference/MANIFEST.sha256", ROOT, state["reference_manifest"]["sha256"], 374),
        (
            "wheelhouse/SHA256SUMS",
            ROOT / "wheelhouse",
            state["execution_environment"]["wheelhouse_manifest_sha256"],
            19,
        ),
    )
    results = {}
    for name, base, expected, count in manifests:
        raw = (ROOT / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise RuntimeError("Pinned input manifest changed: " + name)
        entries = [line for line in raw.decode().splitlines() if line and not line.startswith("#")]
        seen = set()
        for line in entries:
            digest, relative = line.split("  ", 1)
            path = (base / relative).resolve()
            if (
                not path.is_relative_to(base)
                or path in seen
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest
            ):
                raise RuntimeError("Input checksum/path/duplicate mismatch: " + relative)
            seen.add(path)
        if len(entries) != count:
            raise RuntimeError("Input manifest cardinality changed: " + name)
        results[name] = {"sha256": expected, "verified_entries": count, "status": "PASS"}
    for name, expected in (
        (
            state["owner_directed_start_record"]["path"],
            state["owner_directed_start_record"]["sha256"],
        ),
        (state["controlling_prompt"]["path"], state["controlling_prompt"]["sha256"]),
        ("requirements-dev.lock", state["execution_environment"]["dependency_lock_sha256"]),
        (
            state["macro_research"]["owner_decision_path"],
            state["macro_research"]["owner_decision_sha256"],
        ),
    ):
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Pinned authority/dependency input changed: " + name)
    return results


def main() -> None:
    destination = (ROOT / sys.argv[1]).resolve()
    if not any(
        destination.is_relative_to(ROOT / f"evidence/{stage}") for stage in ("stage_a", "stage_b")
    ):
        raise ValueError("Evidence output must remain inside an approved stage directory")
    report = json.loads((destination / "coverage.json").read_text())
    inputs = input_integrity()
    modules = {str(path.relative_to(ROOT)) for path in (ROOT / "v3/offline").rglob("*.py")}
    if (
        modules != REQUIRED
        or set(report["files"]) != REQUIRED
        or not report["meta"]["branch_coverage"]
    ):
        raise RuntimeError("Coverage required-module inventory/branch tracking mismatch")
    for name, data in report["files"].items():
        if (
            data["missing_lines"]
            or data["missing_branches"]
            or data["excluded_lines"]
            or data["summary"]["missing_lines"] != 0
            or data["summary"]["missing_branches"] != 0
        ):
            raise RuntimeError(f"Nonzero missing/excluded coverage: {name}")
    forbidden = {
        "socket",
        "subprocess",
        "urllib",
        "http",
        "requests",
        "httpx",
        "trading_ig",
        "boto3",
        "pickle",
        "joblib",
        "dill",
        "cloudpickle",
        "marshal",
        "shelve",
        "xgboost",
        "sklearn",
        "reference",
    }
    source_files = sorted((ROOT / "v3").rglob("*.py"))
    snapshot = sorted((ROOT / "reference/v2_snapshot").rglob("*.py"))
    source_hashes = {}
    overlap = []
    for path in source_files:
        content = path.read_bytes()
        relative = str(path.relative_to(ROOT))
        source_hashes[relative] = hashlib.sha256(content).hexdigest()
        if relative not in ALLOWED_IMPORTS:
            raise RuntimeError(f"Undeclared first-party unit: {relative}")
        for node in ast.walk(ast.parse(content)):
            imports = []
            if isinstance(node, ast.Import):
                imports = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports = [node.module or ""]
            if any(name.split(".")[0] in forbidden for name in imports):
                raise RuntimeError(f"Forbidden V3 import: {path}")
            if any(name not in ALLOWED_IMPORTS[relative] for name in imports):
                raise RuntimeError(f"Unapproved first-party import dependency: {path}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"eval", "exec", "open", "__import__"}:
                    raise RuntimeError(f"Forbidden dynamic/I/O V3 capability: {path}")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr
                in {"fit", "train", "refit", "partial_fit", "fit_transform", "calibrate"}
            ):
                raise RuntimeError(f"Forbidden training/calibration-fitting call: {path}")
            prohibited = {
                "fit",
                "train",
                "refit",
                "partial_fit",
                "fit_transform",
                "calibrate",
                "allow_pickle",
            }
            if (
                isinstance(node, ast.Name)
                and node.id in prohibited
                or isinstance(node, ast.Attribute)
                and node.attr in prohibited
                or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.name in prohibited
                or isinstance(node, ast.keyword)
                and node.arg in prohibited
            ):
                raise RuntimeError(f"Forbidden training/deserialization symbol: {path}")
        lines = normalized(path)
        windows = {tuple(lines[i : i + 12]) for i in range(len(lines) - 11)}
        for legacy in snapshot:
            if content == legacy.read_bytes():
                raise RuntimeError("Identical-byte V2 source reuse")
            legacy_lines = normalized(legacy)
            if any(
                tuple(legacy_lines[i : i + 12]) in windows for i in range(len(legacy_lines) - 11)
            ):
                overlap.append([str(path.relative_to(ROOT)), str(legacy.relative_to(ROOT))])
    if overlap:
        raise RuntimeError(f"Quarantine 12-line source-overlap hits for R2: {overlap}")
    program = """
import dataclasses, datetime, json, pathlib
from v3.offline.calendar_completion import ReplayClock
from v3.offline.fixture_policy_loader import (
    load_fixture_policy, load_intake_policy, read_fixture_directory)
from v3.offline.data_intake_schema import load_snapshot_fixture
from v3.offline.calendar_completion import assess_snapshot
from v3.offline.effective_policy import load_fixture_tiers, resolve_fixture_tiers
from v3.offline.intent_identity import (
    Digest, Identity, InstrumentId, MarketId, PolicyId, RunContext, RunId, SimulatedAccountId)
root = pathlib.Path.cwd()
public = json.loads((root/'evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json').read_text())
fixture = root/'fixtures/stage_a'
clock = ReplayClock(datetime.datetime(2026,11,18,12,tzinfo=datetime.UTC))
policy = load_fixture_policy(
    (fixture/'policy.json').read_bytes(), (fixture/'manifest.json').read_bytes(),
    bytes.fromhex((fixture/'manifest.sig').read_text()),
    bytes.fromhex(public['public_key_hex']), clock.at)
snapshot_fixture = fixture/'a2'
snapshot = load_snapshot_fixture(
    (snapshot_fixture/'payload.json').read_bytes(),
    (snapshot_fixture/'manifest.json').read_bytes(),
    bytes.fromhex((snapshot_fixture/'manifest.sig').read_text()),
    bytes.fromhex(public['public_key_hex']))
assessment = assess_snapshot(snapshot, snapshot.binding, ReplayClock(snapshot.clock.at))
result = {'identity_policy': dataclasses.asdict(policy),
          'snapshot': dataclasses.asdict(snapshot),
          'assessment': dataclasses.asdict(assessment)}
tiers_fixture = fixture/'a3'
tiers = load_fixture_tiers(
    (tiers_fixture/'payload.json').read_bytes(), (tiers_fixture/'manifest.json').read_bytes(),
    bytes.fromhex((tiers_fixture/'manifest.sig').read_text()),
    bytes.fromhex(public['public_key_hex']))
context = RunContext(
    RunId('SYNTHETIC_RUN_001'), SimulatedAccountId('SIMULATED_ACCOUNT'),
    MarketId('SYNTHETIC_MARKET'), InstrumentId('EURUSD'), PolicyId('SYNTHETIC_TIER_POLICY'),
    tiers.payload_sha256, Digest('a'*64), Digest('b'*64), Digest('2'*64),
    Identity('REPLAY_CLOCK_001'), tiers.valid_from, tiers.valid_until)
result['tier_resolution'] = dataclasses.asdict(resolve_fixture_tiers(
    tiers, context, snapshot.clock.at))
result['context_sha256'] = context.sha256
intake_fixture = fixture/'a4'
intake = load_intake_policy(
    (intake_fixture/'payload.json').read_bytes(), (intake_fixture/'manifest.json').read_bytes(),
    bytes.fromhex((intake_fixture/'manifest.sig').read_text()),
    bytes.fromhex(public['public_key_hex']))
disk = read_fixture_directory(intake, bytes.fromhex(public['public_key_hex']),
                              context.run, context.account, snapshot.clock.at)
result['filesystem_payload_sha256'] = disk.payload_sha256
from tools.check_stage_a_registration import registration_proof
result['registration'] = registration_proof()
print(json.dumps(result, sort_keys=True, default=str, separators=(',',':')))
"""
    results = [
        subprocess.check_output(
            [sys.executable, "-c", program],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
        )
        for _ in range(2)
    ]
    if results[0] != results[1]:
        raise RuntimeError("Cross-process fixture replay was not byte-identical")
    predictions = [
        subprocess.check_output([sys.executable, "-m", "tools.check_stage_b_predictions"], cwd=ROOT)
        for _ in range(2)
    ]
    if predictions[0] != predictions[1]:
        raise RuntimeError("Cross-process dual-source predictions were not byte-identical")
    prediction_report = json.loads(predictions[0])
    if (
        prediction_report["status"] != "PASS"
        or prediction_report["core5_model_denials"] != 5
        or prediction_report["signed_score_predictions"] != 2
        or prediction_report["synthetic_reader_predictions"] != 1
    ):
        raise RuntimeError("Dual-source prediction witness shape mismatch")
    print(
        json.dumps(
            {
                "status": "PASS",
                "input_integrity": inputs,
                "coverage": report["totals"],
                "required_modules": sorted(REQUIRED),
                "source_sha256": source_hashes,
                "forbidden_import_and_direct_io_scan": "PASS",
                "first_party_import_allowlist": "PASS",
                "v2_snapshot_files_compared": len(snapshot),
                "identical_byte_matches": 0,
                "normalized_12_line_matches": overlap,
                "normalization": "strip and collapse whitespace; omit blank/full-line comments",
                "finite_recall_caution": (
                    "These source comparisons do not prove absence of V2 reuse"
                ),
                "determinism_processes": 2,
                "determinism_output_sha256": hashlib.sha256(results[0]).hexdigest(),
                "prediction_determinism_processes": 2,
                "prediction_determinism_output_sha256": hashlib.sha256(predictions[0]).hexdigest(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
