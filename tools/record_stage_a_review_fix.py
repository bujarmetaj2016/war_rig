"""Seal the R2-A-01 Stage A correction and cumulative A/B regression evidence."""

import hashlib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "evidence/stage_a/r2_a_01"
DISPOSITION = ROOT / "evidence/stage_a/R2_A_01_DISPOSITION.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    run, base_commit = sys.argv[1:]
    source = (ROOT / run).resolve()
    if not source.is_relative_to(ROOT / "evidence/stage_a/runs") or not re.fullmatch(
        r"[0-9a-f]{40}", base_commit
    ):
        raise ValueError("Expected a Stage A sandbox run and exact source-base commit")
    checks = json.loads((source / "checks.json").read_text())
    totals = json.loads((source / "coverage.json").read_text())["totals"]
    mutations = json.loads((source / "mutations.json").read_text())
    registration = json.loads((source / "registration.json").read_text())
    predictions = json.loads((source / "predictions.json").read_text())
    junit = ET.parse(source / "junit.xml").getroot()
    suites = list(junit.iter("testsuite"))
    names = {case.attrib["name"].split("[")[0] for case in junit.iter("testcase")}
    required = {
        "test_daily_bar_at_session_close_is_available_after_close_within_max_age",
        "test_daily_bar_denies_before_close_and_when_stale_or_still_forming",
        "test_post_close_decision_still_requires_each_publication_and_vintage",
        "test_daily_post_close_dst_uses_signed_local_close_and_actual_utc_duration",
        "test_daily_interval_instrument_registers_by_configuration_only_after_close",
        "test_daily_features_and_prediction_remain_valid_after_close_until_data_max_age",
    }
    if (
        checks["status"] != "PASS"
        or json.loads((source / "preflight.json").read_text())["status"] != "PASS"
        or any(
            totals[key]
            for key in (
                "missing_lines",
                "missing_branches",
                "num_partial_branches",
                "excluded_lines",
            )
        )
        or any(
            int(suite.attrib[key]) for suite in suites for key in ("failures", "errors", "skipped")
        )
        or not required <= names
        or mutations["killed"] < 30
        or mutations["survived"] != 0
        or registration["daily_post_close_profiles"] != 1
        or registration["registered_profiles"] != 6
        or registration["runtime_source_and_plugin_manifest_bytes_changed"] != 0
        or registration["before_sha256"] != registration["after_sha256"]
        or predictions["status"] != "PASS"
        or predictions["core5_model_denials"] != 5
        or predictions["signed_score_predictions"] != 2
        or predictions["synthetic_reader_predictions"] != 1
        or checks["prediction_determinism_output_sha256"] != sha(source / "predictions.json")
        or not (source / "traceability-check.txt").is_file()
    ):
        raise ValueError("R2 correction or cumulative A/B gate is incomplete")
    for path, digest in checks["source_sha256"].items():
        if sha(ROOT / path) != digest:
            raise ValueError("Source changed after passing gate: " + path)
    for stage, slice_name in (
        ("stage_a", "a6"),
        ("stage_b", "b1"),
        ("stage_b", "b2"),
        ("stage_b", "b3"),
    ):
        for line in (
            (ROOT / "evidence" / stage / slice_name / "MANIFEST.sha256").read_text().splitlines()
        ):
            digest, relative = line.split("  ", 1)
            if sha(ROOT / relative) != digest:
                raise ValueError("Historical checkpoint changed: " + relative)
    TARGET.mkdir(exist_ok=False)
    for path in sorted(source.iterdir()):
        if not path.is_file():
            raise ValueError("Unexpected nested gate output")
        shutil.copyfile(path, TARGET / path.name)
    count = sum(int(suite.attrib["tests"]) for suite in suites)
    gate = {
        "slice": "A7_R2_A_01",
        "finding": "R2-A-01",
        "severity": "MAJOR",
        "decision": "PASS_IMPLEMENTATION_FIXED_REVIEWER_ACCEPTANCE_NOT_ASSERTED",
        "stage_b": "PASS_REVALIDATED_OFFLINE_SYNTHETIC_SCOPE",
        "source_commit_before_gate": base_commit,
        "source_sha256": checks["source_sha256"],
        "dependency_lock_sha256": sha(ROOT / "requirements-dev.lock"),
        "python_image": (ROOT / "evidence/preflight/PYTHON_IMAGE.txt").read_text().strip(),
        "command": "sh tools/run_offline.sh stage_a --seal-r2-a-01",
        "runner_exit_code": 0,
        "tests": count,
        "coverage": totals,
        "mutations_killed": mutations["killed"],
        "required_regressions": sorted(required),
        "disposition": str(DISPOSITION.relative_to(ROOT)),
        "disposition_sha256": sha(DISPOSITION),
        "authority": "FIXTURE_ONLY_NO_ENTRY_NO_MODEL_APPROVAL_NO_TRADING_AUTHORITY",
    }
    (TARGET / "GATE.json").write_text(json.dumps(gate, indent=2) + "\n")
    (TARGET / "MANIFEST.sha256").write_text(
        "".join(
            f"{sha(path)}  {path.relative_to(ROOT)}\n"
            for path in sorted(TARGET.iterdir())
            if path.is_file()
        )
    )
    state_path = ROOT / "evidence/STAGE_STATE.json"
    state = json.loads(state_path.read_text())
    state.update(
        status="STAGE_A_R2_A01_FIXED_STAGE_B_REVALIDATED_FULL_SCOPE_NOT_READY",
        last_pass_slice="A7_R2_A_01",
        last_commit=base_commit,
        last_commit_role="BASE_OF_GATE_SOURCE_HASHES_BOUND_BY_ENCLOSING_CHECKPOINT",
        checkpoint_form="STAGE_A_REVIEW_CORRECTION_CUMULATIVE_A_B_PASS",
        resume_note="R2-A-01 fixed and Stage B revalidated. Stage C is not started. "
        "Minor typed-denial/parser/versioned-registration work remains tracked; "
        "no independent reviewer acceptance or model/trading authority is asserted.",
    )
    relative = str((TARGET / "GATE.json").relative_to(ROOT))
    state["stage_a_slices"]["A7_R2_A_01"] = {
        "status": "PASS",
        "gate_path": relative,
        "source_commit_binding": "ENCLOSING_GATE_COMMIT",
    }
    state["review_findings"] = {
        "R2-A-01": {
            "severity": "MAJOR",
            "status": "IMPLEMENTATION_FIXED",
            "reviewer_acceptance": "NOT_ASSERTED",
            "evidence": relative,
        },
        "minor_followups": [
            "Typed denial reasons",
            "Public shared parsing module",
            "Controlled successor definition versions for an existing instrument (EXT 3.3)",
        ],
    }
    state["tests_and_coverage"].update(
        status="PASS_A7_R2_A01_AND_STAGE_B_REVALIDATION",
        command=gate["command"],
        tests_executed=count,
        statements_total=totals["num_statements"],
        branches_total=totals["num_branches"],
        mutations_killed=mutations["killed"],
        coverage_artifact_path=str((TARGET / "coverage.json").relative_to(ROOT)),
        coverage_artifact_sha256=sha(TARGET / "coverage.json"),
        mutation_report_path=str((TARGET / "mutations.json").relative_to(ROOT)),
        determinism_output_sha256=checks["determinism_output_sha256"],
        prediction_determinism_output_sha256=checks["prediction_determinism_output_sha256"],
    )
    state["evidence"].update(
        current_correction_gate=relative,
        source_verification_path=str((TARGET / "preflight.json").relative_to(ROOT)),
        source_verification_sha256=sha(TARGET / "preflight.json"),
        r2_handoff_status="R2_A01_IMPLEMENTATION_FIXED_A_B_REVALIDATED_MINOR_FOLLOWUPS_OPEN",
    )
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()
