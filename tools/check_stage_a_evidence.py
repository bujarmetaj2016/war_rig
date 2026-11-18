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
    "v3/offline/fixture_policy_loader.py",
}
ALLOWED_IMPORTS = {
    "v3/__init__.py": set(),
    "v3/offline/__init__.py": set(),
    "v3/offline/calendar_completion.py": {"dataclasses", "datetime"},
    "v3/offline/fixture_policy_loader.py": {
        "hashlib",
        "json",
        "re",
        "dataclasses",
        "datetime",
        "enum",
        "cryptography.exceptions",
        "cryptography.hazmat.primitives.asymmetric.ed25519",
        "v3.offline.calendar_completion",
    },
}


def normalized(path: Path) -> list[str]:
    return [
        " ".join(line.split())
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def main() -> None:
    destination = (ROOT / sys.argv[1]).resolve()
    if not destination.is_relative_to(ROOT / "evidence/stage_a"):
        raise ValueError("Evidence output must remain inside evidence/stage_a")
    report = json.loads((destination / "coverage.json").read_text())
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
from v3.offline.fixture_policy_loader import load_fixture_policy
root = pathlib.Path.cwd()
public = json.loads((root/'evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json').read_text())
fixture = root/'fixtures/stage_a'
clock = ReplayClock(datetime.datetime(2026,11,18,12,tzinfo=datetime.UTC))
policy = load_fixture_policy(
    (fixture/'policy.json').read_bytes(), (fixture/'manifest.json').read_bytes(),
    bytes.fromhex((fixture/'manifest.sig').read_text()),
    bytes.fromhex(public['public_key_hex']), clock.at)
print(json.dumps(dataclasses.asdict(policy), sort_keys=True, default=str, separators=(',',':')))
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
    print(
        json.dumps(
            {
                "status": "PASS",
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
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
