"""Seal successful Stage B slice evidence without editing any accepted checkpoint."""

import hashlib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    name, run, base_commit = sys.argv[1:]
    if name not in {"b1", "b2", "b3"} or not re.fullmatch(r"[a-f0-9]{40}", base_commit):
        raise ValueError("Expected known Stage B slice and independently supplied Git base")
    source = (ROOT / run).resolve()
    if not source.is_relative_to(ROOT / "evidence/stage_b/runs"):
        raise ValueError("Expected a fresh Stage B sandbox run")
    checks = json.loads((source / "checks.json").read_text())
    coverage = json.loads((source / "coverage.json").read_text())
    mutations = json.loads((source / "mutations.json").read_text())
    preflight = json.loads((source / "preflight.json").read_text())
    if name != "b1":
        prediction_bytes = (source / "predictions.json").read_bytes()
        predictions = json.loads(prediction_bytes)
        if (
            predictions["status"] != "PASS"
            or predictions["core5_model_denials"] != 5
            or predictions["signed_score_predictions"] != 2
            or predictions["synthetic_reader_predictions"] != 1
            or checks["prediction_determinism_processes"] != 2
            or checks["prediction_determinism_output_sha256"]
            != hashlib.sha256(prediction_bytes).hexdigest()
        ):
            raise ValueError("Missing or mismatched independently replayed prediction proof")
    if name == "b3":
        trace = json.loads((source / "stage-b-traceability.json").read_text())
        if (
            trace["stage_b_rows"] != 19
            or trace["stage_b_scoped_pass"] != 19
            or trace["traceability_rows"] != 627
            or trace["source_count_gate"] != "PASS"
            or trace["completion_csv_sha256"]
            != hashlib.sha256(
                (ROOT / "evidence/stage_b/STAGE_B_COMPLETION.csv").read_bytes()
            ).hexdigest()
        ):
            raise ValueError("Stage B completion scope or final mapping changed")
    suites = list(ET.parse(source / "junit.xml").getroot().iter("testsuite"))
    totals = coverage["totals"]
    if (
        checks["status"] != "PASS"
        or preflight["status"] != "PASS"
        or any(
            totals[key]
            for key in (
                "missing_lines",
                "missing_branches",
                "num_partial_branches",
                "excluded_lines",
            )
        )
        or mutations["survived"]
        or mutations["killed"] < 28
        or any(
            int(suite.attrib[key]) for suite in suites for key in ("failures", "errors", "skipped")
        )
        or not (source / "traceability-check.txt").is_file()
    ):
        raise ValueError("Cannot seal a failed, partial or incompletely evidenced slice")
    for path, digest in checks["source_sha256"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError("Source changed after passing gate: " + path)
    target = ROOT / "evidence/stage_b" / name
    target.mkdir(exist_ok=False)
    for path in sorted(source.iterdir()):
        if not path.is_file():
            raise ValueError("Unexpected nested gate output")
        shutil.copyfile(path, target / path.name)
    count = sum(int(suite.attrib["tests"]) for suite in suites)
    gate = {
        "slice": name.upper(),
        "decision": "PASS",
        "stage_b": "PASS_OFFLINE_SYNTHETIC_SCOPE" if name == "b3" else "IN_PROGRESS",
        "source_commit_before_gate": base_commit,
        "source_sha256": checks["source_sha256"],
        "command": "sh tools/run_offline.sh stage_b",
        "dependency_lock_sha256": hashlib.sha256(
            (ROOT / "requirements-dev.lock").read_bytes()
        ).hexdigest(),
        "python_image": (ROOT / "evidence/preflight/PYTHON_IMAGE.txt").read_text().strip(),
        "runner_exit_code": 0,
        "tests": count,
        "coverage": totals,
        "mutations_killed": mutations["killed"],
        "requirements": "evidence/stage_b/STAGE_B_REQUIREMENTS.csv",
        "source_reading": "evidence/stage_b/SOURCE_READING.md",
        "authority": "SYNTHETIC_OFFLINE_ONLY_NO_MODEL_ELIGIBILITY_NO_TRADING_AUTHORITY",
        "real_core5_models": "UNAVAILABLE_NOT_VERIFIED_NO_AUTHORITATIVE_PREDICTION",
    }
    (target / "GATE.json").write_text(json.dumps(gate, indent=2) + "\n")
    (target / "MANIFEST.sha256").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT)}\n"
            for path in sorted(target.iterdir())
            if path.is_file()
        )
    )
    state_path = ROOT / "evidence/STAGE_STATE.json"
    state = json.loads(state_path.read_text())
    state.update(
        status="STAGE_B_IN_PROGRESS",
        checkpoint_form="STAGE_B_SLICE_GATED",
        current_stage="B",
        last_pass_slice=name.upper(),
        last_commit=base_commit,
        last_commit_role="BASE_OF_GATE_SOURCE_HASHES_BOUND_BY_ENCLOSING_CHECKPOINT",
        resume_note="Resume Stage B after the enclosing committed slice gate; "
        "no Stage C start until any arriving Stage A R2 finding is fixed.",
    )
    state["stages"]["B"] = "IN_PROGRESS"
    state.setdefault("stage_b_slices", {})[name.upper()] = {
        "status": "PASS",
        "gate_path": str((target / "GATE.json").relative_to(ROOT)),
        "source_commit_binding": "ENCLOSING_GATE_COMMIT",
    }
    state["macro_research"]["implementation_status"] = (
        "B1_COMPUTE_LOG_PIPELINE_ONLY_C_E_F_INTEGRATION_PENDING"
    )
    state["tests_and_coverage"].update(
        status="PASS_THROUGH_" + name.upper(),
        tests_executed=count,
        statements_total=totals["num_statements"],
        statements_missing=0,
        branches_total=totals["num_branches"],
        branches_missing=0,
        branches_partial=0,
        coverage_artifact_path=str((target / "coverage.json").relative_to(ROOT)),
        coverage_artifact_sha256=hashlib.sha256(
            (target / "coverage.json").read_bytes()
        ).hexdigest(),
        mutations_killed=mutations["killed"],
        mutation_report_path=str((target / "mutations.json").relative_to(ROOT)),
    )
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()
