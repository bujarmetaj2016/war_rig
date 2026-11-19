"""Map executed Stage B mechanics without certifying real models or later lifecycles."""

import json
import subprocess
import sys
from collections import Counter

from tools.record_stage_a_completion import ROOT, encoded, rows, sha

SCOPE = ROOT / "evidence/stage_b"
COMPLETION = SCOPE / "STAGE_B_COMPLETION.csv"
PARTIAL = {
    "MSB-08": "Synthetic scope/state/profile/expiry denials only; real owner serving unavailable.",
    "MSB-13": "Canonical event intent identity proved; durable no-second-intent gate belongs to D.",
    "MSB-14": "No real registration; owner records and real conversion unavailable.",
    "MSB-15": "Current whole-build import gate passes; EXT-04 strategy integration belongs to C.",
    "MSB-16": "Source/audit references proved; order/position/outcome records belong to D/F.",
}
RUNTIME = "v3/offline/"
TESTS = "tests/v3/"
MAPPINGS = [
    ("offline_scenario_runner.py:load_feature_row", "test_prediction_pipeline.py"),
    ("offline_scenario_runner.py:load_prediction_plugins", "test_prediction_pipeline.py"),
    ("offline_scenario_runner.py:make_signal", "test_prediction_pipeline.py"),
    ("offline_scenario_runner.py:evaluate_prediction", "test_prediction_integration.py"),
    ("offline_scenario_runner.py:signed_score_provider", "test_prediction_integration.py"),
    ("model_intake.py:load_synthetic_model_packet", "test_model_intake.py"),
    ("model_intake.py:SyntheticModel", "test_model_intake.py"),
    ("model_intake.py:load_synthetic_model", "test_model_intake.py"),
    ("model_intake.py:unavailable_core5", "test_prediction_integration.py"),
    ("offline_scenario_runner.py:make_signal", "test_prediction_pipeline.py"),
    ("offline_scenario_runner.py:make_signal", "test_prediction_integration.py"),
    ("offline_scenario_runner.py:grouped_report", "test_model_intake.py"),
    ("offline_scenario_runner.py:prediction_reference", "test_prediction_pipeline.py"),
    ("macro_features.py:compute_macro_observation", "test_macro_features.py"),
    ("macro_features.py:compute_macro_observation", "test_macro_features.py"),
    ("macro_features.py:compute_macro_observation", "test_macro_features.py"),
    ("macro_features.py:attach_observation", "test_macro_features.py"),
    ("offline_scenario_runner.py:v2_confidence_observation", "test_prediction_integration.py"),
    ("TOOLS:record_stage_b_completion.py", "TOOLS:check_stage_b_predictions.py"),
]


def stage_rows():
    _, source = rows(SCOPE / "STAGE_B_REQUIREMENTS.csv")
    if len(source) != 19 or len(MAPPINGS) != 19:
        raise ValueError("Stage B source decomposition changed")
    result = []
    for number, (row, (runtime, test)) in enumerate(zip(source, MAPPINGS, strict=True), 1):
        if row["id"] != f"SB-{number:02}" or not row["v5_member"] or not row["v5_clause"]:
            raise ValueError("Missing or reordered Stage B source clause")
        runtime = (
            runtime.replace("TOOLS:", "tools/")
            if runtime.startswith("TOOLS:")
            else RUNTIME + runtime
        )
        test = test.replace("TOOLS:", "tools/") if test.startswith("TOOLS:") else TESTS + test
        if not (ROOT / runtime.split(":")[0]).is_file() or not (ROOT / test).is_file():
            raise ValueError("Missing implementation or executable witness")
        result.append(
            {
                **row,
                "stage_b_result": "PASS_OFFLINE_SYNTHETIC_SCOPE",
                "runtime": runtime,
                "positive_and_hostile_tests": test,
                "executed_evidence": "evidence/stage_b/b3/GATE.json;"
                "evidence/stage_b/b3/predictions.json",
                "source_reading": "evidence/stage_b/SOURCE_READING.md",
                "limits": "NO_REAL_MODEL_ELIGIBILITY; NO_ENTRY_OR_MONETARY_AUTHORITY; "
                "C_D_E_F_INTEGRATION_SEPARATELY_GATED",
            }
        )
    return result, list(result[0])


def write():
    records, fields = stage_rows()
    COMPLETION.write_bytes(encoded(records, fields))
    path = ROOT / "evidence/traceability.csv"
    fields, records = rows(path)
    if len(records) != 627 or len({row["universe_id"] for row in records}) != 627:
        raise ValueError("Universe changed")
    for row in records:
        identifier = row["universe_id"]
        if not identifier.startswith("MSB-") and identifier not in {
            "COMPONENT-03",
            "MODULE:ModelArtifactRegistry",
        }:
            continue
        complete = identifier.startswith("MSB-") and identifier not in PARTIAL
        row.update(
            implementation_state="IMPLEMENTED" if complete else "PARTIALLY_IMPLEMENTED",
            final_status="IMPLEMENTED_TESTED" if complete else "",
            applicability="R3_STAGE_B_SYNTHETIC_OFFLINE_ONLY",
            runtime_module_class_function=RUNTIME
            + "offline_scenario_runner.py;"
            + RUNTIME
            + "model_intake.py;"
            + RUNTIME
            + "macro_features.py",
            positive_tests=TESTS
            + "test_prediction_pipeline.py;"
            + TESTS
            + "test_model_intake.py;"
            + TESTS
            + "test_prediction_integration.py",
            negative_fault_tests=TESTS
            + "test_model_intake.py;"
            + TESTS
            + "test_prediction_integration.py;"
            + TESTS
            + "test_macro_features.py",
            executed_result="PASS" if complete else "PARTIAL_NOT_FINAL_PASS",
            evidence_paths="evidence/stage_b/STAGE_B_COMPLETION.csv;"
            "evidence/stage_b/b3/GATE.json;evidence/stage_b/b3/predictions.json;"
            "evidence/stage_b/b3/checks.json",
            mapping_notes=PARTIAL.get(
                identifier,
                (
                    "Own-ID mechanical oracle executed under R3's explicit hand-authored "
                    "synthetic-reader exception, not original-library parity, owner approval, "
                    "VALIDATED/SERVING status, real calibration or performance."
                    if complete
                    else "Prediction/confidence mechanics only; actual strategy, "
                    "real owner registration and later-stage orchestration remain pending."
                ),
            ),
        )
    path.write_bytes(encoded(records, fields))
    regenerated = subprocess.run(
        [sys.executable, "-I", "tools/extract_requirement_universe.py", "--write"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
    )
    if regenerated.returncode not in {0, 2}:
        raise RuntimeError("Source-owned universe regeneration failed")
    parity_path = ROOT / "evidence/V2_V3_CAPABILITY_PARITY.csv"
    fields, parity = rows(parity_path)
    for row in parity:
        if row["baseline"] == "OWNER_ADOPTED_LOGGING":
            row.update(
                implementation_status="IMPLEMENTED_TESTED_COMPUTE_LOG_PIPELINE_ONLY",
                evidence=row["evidence"] + "; evidence/stage_b/STAGE_B_COMPLETION.csv;"
                " evidence/stage_b/b3/predictions.json; tests/v3/test_macro_features.py",
                limitations="Current prediction/grade/cap noninterference proved, including "
                "functional mutants. Entry/size/TP/SL/trailing/ledger/dashboard integrations "
                "remain C/D/E/F gates; no real-data/performance claim.",
            )
    for instrument in ("XAUUSD", "GER40", "US500", "EURUSD", "GBPUSD"):
        for feature in ("prediction_sources", "confidence_grade_reference"):
            if any(row["instrument"] == instrument and row["feature"] == feature for row in parity):
                raise ValueError("Refusing to overwrite an existing parity row")
            parity.append(
                dict(
                    zip(
                        fields,
                        (
                            instrument,
                            feature,
                            "VERIFIED_FROM_PINNED_V2_SOURCE",
                            "V2_PARITY",
                            "COMPARISON_ONLY",
                            "NO_ACTIVE_V2_CLIMATE_GATE_OR_SIZE_MULTIPLIER",
                            "IMPLEMENTED_SYNTHETIC_REFERENCE_ONLY",
                            "reference/v2_snapshot/backtest_ml/live_inference.py:107-150,478-521;"
                            " reference/v2_snapshot/backtest_ml/audit_entry.py:62-67;"
                            " evidence/stage_b/SOURCE_READING.md;"
                            " tests/v3/test_prediction_integration.py",
                            "Pinned inference function refits and retains no frozen model; "
                            "not a live-host/global absence proof. Core-5 models deny. "
                            "Grades and Gold/FX/equity observations are comparison-only; "
                            "NOT_PROVEN "
                            "calibration; not complete feature-transform parity or performance.",
                        ),
                        strict=True,
                    )
                )
            )
    parity_path.write_bytes(encoded(parity, fields))


def check():
    expected, fields = stage_rows()
    if COMPLETION.read_bytes() != encoded(expected, fields):
        raise ValueError("Stage B source mapping stale")
    _, trace = rows(ROOT / "evidence/traceability.csv")
    msb = [row for row in trace if row["universe_id"].startswith("MSB-")]
    if len(trace) != 627 or {row["universe_id"] for row in msb} != {
        f"MSB-{number:02}" for number in range(1, 20)
    }:
        raise ValueError("MS-B/global cardinality mismatch")
    for row in msb:
        pending = row["universe_id"] in PARTIAL
        if (
            row["final_status"] != ("" if pending else "IMPLEMENTED_TESTED")
            or "evidence/stage_b/b3/GATE.json" not in row["evidence_paths"]
        ):
            raise ValueError("Dishonest or missing MS-B disposition")
    subprocess.run(
        [sys.executable, "-I", "tools/extract_requirement_universe.py", "--check-source-counts"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return {
        "stage_b_rows": 19,
        "stage_b_scoped_pass": len(expected),
        "msb_mechanical_oracles_pass": 14,
        "msb_partial_not_final_pass": PARTIAL,
        "traceability_rows": len(trace),
        "global_final_status_counts": dict(
            Counter(row["final_status"] or "PENDING" for row in trace)
        ),
        "global_implementation_state_counts": dict(
            Counter(row["implementation_state"] for row in trace)
        ),
        "source_count_gate": "PASS",
        "full_C_G_completion": "NOT_CLAIMED",
        "completion_csv_sha256": sha(COMPLETION),
    }


def finalize(summary):
    gate = json.loads((SCOPE / "b3/GATE.json").read_text())
    if gate["decision"] != "PASS" or gate["stage_b"] != "PASS_OFFLINE_SYNTHETIC_SCOPE":
        raise ValueError("Final Stage B gate missing")
    for path, digest in gate["source_sha256"].items():
        if sha(ROOT / path) != digest:
            raise ValueError("Runtime changed after gate")
    state_path = ROOT / "evidence/STAGE_STATE.json"
    state = json.loads(state_path.read_text())
    state.update(
        status="STAGE_B_COMPLETE_FULL_SCOPE_NOT_READY",
        current_stage="C",
        last_pass_stage="B",
        checkpoint_form="STAGE_B_SYNTHETIC_OFFLINE_COMPLETE",
        resume_note="Resume C only after fixing any arriving Stage A R2 findings. "
        "No real model eligibility, release, broker or trading authority.",
    )
    state["stages"]["B"] = "PASS"
    state["remaining_stage_b_work"] = []
    state["stage_b_limits"] = PARTIAL
    state["execution_environment"].update(
        status="PASS_FOR_STAGE_A_B_OFFLINE_EXECUTION",
        full_runtime_safety_suite="STAGE_A_B_PASS_FULL_STAGE_G_SCOPE_PENDING",
    )
    state["macro_research"]["implementation_status"] = (
        "COMPUTE_LOG_PIPELINE_TESTED_C_E_F_INTEGRATION_PENDING"
    )
    evidence = state["evidence"]
    for key, path in (
        ("requirement_universe", ROOT / "evidence/requirement_universe.csv"),
        ("traceability", ROOT / "evidence/traceability.csv"),
        ("requirement_universe_report", ROOT / "evidence/REQUIREMENT_UNIVERSE_REPORT.json"),
    ):
        evidence[key + "_sha256"] = sha(path)
    _, parity = rows(ROOT / "evidence/V2_V3_CAPABILITY_PARITY.csv")
    evidence.update(
        traceability_status="A_27_B_19_SCOPED_PASS_GLOBAL_C_G_AND_REAL_MODEL_ORACLES_PENDING",
        traceability_totals={**summary["global_final_status_counts"], "source_count_conflicts": 0},
        stage_b_completion_path=str(COMPLETION.relative_to(ROOT)),
        stage_b_completion_sha256=sha(COMPLETION),
        parity_rows=len(parity),
        parity_status="MACRO_AND_PREDICTION_CONFIDENCE_SCOPES_ONLY",
        source_verification_path="evidence/stage_b/b3/preflight.json",
        source_verification_sha256=sha(SCOPE / "b3/preflight.json"),
        r2_handoff_status="STAGE_A_B_COMPLETE_FULL_SCOPE_NOT_READY_FOR_ACCEPTANCE",
    )
    checks = json.loads((SCOPE / "b3/checks.json").read_text())
    state["tests_and_coverage"].update(
        command="sh tools/run_offline.sh stage_b",
        macro_trading_decision_noninterference_tests="CURRENT_PIPELINE_PASS_C_E_F_NOT_YET_BUILT",
        determinism_output_sha256=checks["determinism_output_sha256"],
        prediction_determinism_output_sha256=checks["prediction_determinism_output_sha256"],
    )
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    (SCOPE / "COMPLETION_REPORT.json").write_text(
        json.dumps({"decision": gate["stage_b"], **summary}, indent=2) + "\n"
    )


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        write()
    elif sys.argv[1:] not in (["--check"], ["--finalize"]):
        raise ValueError("Use --write, --check or --finalize")
    summary = check()
    if sys.argv[1:] == ["--finalize"]:
        finalize(summary)
    print(json.dumps(summary, indent=2))
