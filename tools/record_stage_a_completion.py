"""Map executed Stage A foundations without claiming that pending B-G oracles have passed."""

import csv
import hashlib
import io
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "evidence/stage_a"
AMENDMENT = "evidence/stage_a/source_conflict/OWNER_DISPOSITION_20261118_AMENDMENT_1.md"
COMPLETION = SCOPE / "STAGE_A_COMPLETION.csv"
REPORT = SCOPE / "COMPLETION_REPORT.json"
RUNTIME = "v3/offline/"
TESTS = "tests/v3/"
MAPPINGS = [
    ("intent_identity.py:Identity", "test_policy_foundations.py", "A3"),
    ("fixture_policy_loader.py:authenticate_fixture", "test_fixture_policy_loader.py", "A1-A2"),
    ("plugin_manifest.py:load_plugin_manifest", "test_instrument_registration.py", "A5"),
    ("intent_identity.py:PriceUnit", "test_policy_foundations.py", "A3"),
    ("calendar_completion.py:assess_snapshot", "test_completed_snapshots.py", "A2"),
    ("calendar_completion.py:assess_snapshot", "test_completed_snapshots.py", "A2"),
    ("calendar_completion.py:assess_snapshot", "test_completed_snapshots.py", "A2"),
    ("calendar_completion.py:assess_snapshot", "test_completed_snapshots.py", "A2"),
    ("data_intake_schema.py:load_snapshot_fixture", "test_completed_snapshots.py", "A2"),
    ("calendar_completion.py:assess_snapshot", "test_completed_snapshots.py", "A2"),
    ("intent_identity.py:RunContext", "test_instrument_registration.py", "A3,A5"),
    ("calendar_completion.py:FeatureLineage", "test_completed_snapshots.py", "A2"),
    ("fixture_policy_loader.py:IntakePolicy", "test_fixture_filesystem.py", "A1,A3,A4"),
    ("effective_policy.py:resolve_fixture_tiers", "test_policy_foundations.py", "A3"),
    (
        "instrument_definition.py:load_instrument_definition",
        "test_instrument_registration.py",
        "A1-A5",
    ),
    ("effective_policy.py:OfflinePermission", "test_policy_foundations.py", "A3"),
    ("calendar_completion.py:ReplayClock", "test_calendar_completion.py", "A1"),
    ("calendar_completion.py:VerifiedEventClock", "test_completed_snapshots.py", "A2"),
    ("intent_identity.py:ReplayCursor", "test_policy_foundations.py", "A3"),
    ("fixture_policy_loader.py:read_fixture_directory", "test_fixture_filesystem.py", "A4"),
    (
        "instrument_definition.py:load_instrument_definition",
        "test_instrument_registration.py",
        "A5",
    ),
    ("contract_listing_registry.py:load_fixture_outcome", "test_instrument_registration.py", "A5"),
    (
        "contract_listing_registry.py:assess_fixture_listing",
        "test_instrument_registration.py",
        "A5",
    ),
    (
        "contract_listing_registry.py:FixtureRegistrationRegistry",
        "test_instrument_registration.py",
        "A5",
    ),
    (
        "instrument_definition.py:load_instrument_definition",
        "test_instrument_registration.py",
        "A5",
    ),
    ("TOOLS:offline_preflight.py", "TOOLS:check_stage_a_evidence.py", "A1-A6"),
    ("TOOLS:extract_requirement_universe.py", "TOOLS:extract_requirement_universe.py", "A6"),
]
COMPLETE_GLOBAL = {"V3EXT-001", "V3EXT-004", "V3EXT-006"}
PARTIAL_GLOBAL = {
    f"V3EXT-{number:03}"
    for number in (
        2,
        3,
        5,
        7,
        10,
        13,
        14,
        15,
        16,
        20,
        23,
        24,
        25,
        27,
        28,
        31,
        32,
        33,
        34,
    )
}


def rows(path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def encoded(records, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue().encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_rows():
    fields, source = rows(SCOPE / "STAGE_A_REQUIREMENTS.csv")
    if len(source) != 27 or len(MAPPINGS) != 27:
        raise ValueError("Stage A source decomposition changed")
    result = []
    for number, (row, mapping) in enumerate(zip(source, MAPPINGS, strict=True), 1):
        if row["id"] != f"SA-{number:02}" or not row["v5_member"] or not row["v5_clause"]:
            raise ValueError("Stage A source/member/clause identity mismatch")
        runtime, tests, slices = mapping
        runtime = (
            runtime.replace("TOOLS:", "tools/")
            if runtime.startswith("TOOLS:")
            else RUNTIME + runtime
        )
        tests = tests.replace("TOOLS:", "tools/") if tests.startswith("TOOLS:") else TESTS + tests
        if not (ROOT / runtime.split(":")[0]).is_file() or not (ROOT / tests).is_file():
            raise ValueError("Missing implemented runtime or executed test")
        result.append(
            {
                **row,
                "status": "IMPLEMENTED_TESTED",
                "runtime": runtime,
                "positive_and_hostile_tests": tests,
                "slice_gates": slices,
                "executed_evidence": (
                    "evidence/stage_a/a6/GATE.json;evidence/stage_a/a5/registration.json"
                ),
                "source_reading": "evidence/stage_a/SOURCE_READING.md",
                "owner_disposition": AMENDMENT + " point 2(a-d)" if number == 27 else "",
                "scope": "STAGE_A_FOUNDATIONS_ONLY_NOT_B_G_OR_REAL_AUTHORITY",
            }
        )
    return result, list(result[0])


def update_global():
    path = ROOT / "evidence/traceability.csv"
    fields, records = rows(path)
    ids = {row["universe_id"] for row in records}
    if len(records) != 627 or len(ids) != 627 or not COMPLETE_GLOBAL | PARTIAL_GLOBAL <= ids:
        raise ValueError("Universe changed; no inferred/dropped identifiers")
    for row in records:
        identifier = row["universe_id"]
        if identifier not in COMPLETE_GLOBAL | PARTIAL_GLOBAL:
            continue
        complete = identifier in COMPLETE_GLOBAL
        runtime = (
            RUNTIME
            + "instrument_definition.py:load_instrument_definition;"
            + RUNTIME
            + "contract_listing_registry.py:FixtureRegistrationRegistry"
        )
        tests = TESTS + "test_instrument_registration.py"
        if identifier in {"V3EXT-004", "V3EXT-005", "V3EXT-031"}:
            runtime = RUNTIME + "plugin_manifest.py:load_plugin_manifest"
        elif identifier in {"V3EXT-002", "V3EXT-007"}:
            runtime = RUNTIME + "effective_policy.py:resolve_fixture_tiers"
            tests = TESTS + "test_policy_foundations.py"
        elif identifier in {"V3EXT-013", "V3EXT-016", "V3EXT-023"}:
            runtime = RUNTIME + "calendar_completion.py:assess_snapshot"
            tests = TESTS + "test_completed_snapshots.py"
        elif identifier in {"V3EXT-020", "V3EXT-024", "V3EXT-025", "V3EXT-027"}:
            runtime = "tools/offline_preflight.py;tools/check_stage_a_evidence.py"
            tests = "tools/offline_preflight.py;tools/check_stage_a_evidence.py"
        elif identifier in {"V3EXT-010", "V3EXT-032", "V3EXT-033"}:
            runtime = RUNTIME + "contract_listing_registry.py:assess_fixture_listing"
        row.update(
            implementation_state="IMPLEMENTED" if complete else "PARTIALLY_IMPLEMENTED",
            final_status="IMPLEMENTED_TESTED" if complete else "",
            applicability="G1_OFFLINE_ONLY_COMPLETE_ORACLE"
            if complete
            else "LATER_STAGE_COMPLETION_PENDING",
            runtime_module_class_function=runtime,
            positive_tests=tests,
            negative_fault_tests=TESTS
            + "test_instrument_registration.py;"
            + TESTS
            + "test_policy_foundations.py",
            executed_result="PASS" if complete else "PARTIAL_STAGE_A_ONLY_NOT_FINAL_PASS",
            evidence_paths="evidence/stage_a/a5/GATE.json;evidence/stage_a/a5/registration.json;"
            "evidence/stage_a/a6/GATE.json;evidence/stage_a/a6/preflight.json;"
            "evidence/stage_a/STAGE_A_COMPLETION.csv",
            mapping_notes=(
                "Exact own-ID oracle in EXT section 5.4, not incidental cross-reference text. "
                "Executed immutable family hashes, strict plug-in registry and six-profile "
                "configuration-only onboarding; no approval or real dealing authority."
                if complete
                else "Stage A primitives and explicit denials only. The entire source oracle "
                "is NOT passed: operational lifecycle/authority, predictions, monetary "
                "risk, rolls, ledger, model or final integration duties remain B-G work. "
                "See the 27 source-clause-specific foundation mappings."
            ),
        )
    path.write_bytes(encoded(records, fields))
    result = subprocess.run(
        [sys.executable, "-I", "tools/extract_requirement_universe.py", "--write"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
    )
    if result.returncode not in {0, 2}:
        raise RuntimeError("Requirement regeneration failed")
    # Exit 2 includes honest pending B-G mappings; check() separately requires
    # the source/count gate to exit 0 before accepting the regenerated artifacts.


def check():
    expected, fields = stage_rows()
    if COMPLETION.read_bytes() != encoded(expected, fields):
        raise ValueError("Stage A completion/source mapping is stale")
    _, universe = rows(ROOT / "evidence/requirement_universe.csv")
    _, trace = rows(ROOT / "evidence/traceability.csv")
    if len(trace) != 627 or {row["universe_id"] for row in trace} != {
        row["universe_id"] for row in universe
    }:
        raise ValueError("Requirement universe/trace identity mismatch")
    complete = {row["universe_id"] for row in trace if row["final_status"] == "IMPLEMENTED_TESTED"}
    if not COMPLETE_GLOBAL <= complete:
        raise ValueError("A completed Stage A oracle lost its disposition")
    negative = [row for row in trace if "negative" in row["requirement_classes"].lower()]
    # Exact source-class membership is independently rechecked by the extractor.
    cited = [row for row in trace if row["source_id"].startswith(("CC1-NEG-", "SD2-MST-NEG-"))]
    if len(cited) != 84 or any(AMENDMENT not in row["source_references_json"] for row in cited):
        raise ValueError("Missing amendment citations in the 84 negative rows")
    subprocess.run(
        [sys.executable, "-I", "tools/extract_requirement_universe.py", "--check-source-counts"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return {
        "stage_a_rows": 27,
        "stage_a_implemented_tested": 27,
        "universe_rows": len(universe),
        "traceability_rows": len(trace),
        "global_final_status_counts": dict(
            Counter(row["final_status"] or "PENDING" for row in trace)
        ),
        "global_implementation_state_counts": dict(
            Counter(row["implementation_state"] for row in trace)
        ),
        "negative_amendment_citations": len(cited),
        "negative_class_rows": len(negative),
        "source_count_gate": "PASS",
        "full_B_G_completion": "NOT_CLAIMED",
        "completion_csv_sha256": sha(COMPLETION),
    }


def finalize(summary):
    gate = json.loads((SCOPE / "a6/GATE.json").read_text())
    proof = json.loads((SCOPE / "a6/registration.json").read_text())
    if gate["decision"] != "PASS" or proof["registered_profiles"] != 6:
        raise ValueError("Final gate or sixth-instrument proof missing")
    for path, digest in gate["source_sha256"].items():
        if sha(ROOT / path) != digest:
            raise ValueError("Runtime changed after the final gate")
    state_path = ROOT / "evidence/STAGE_STATE.json"
    state = json.loads(state_path.read_text())
    if any(state["stages"][stage] != "NOT_STARTED" for stage in "BCDEFG"):
        raise ValueError("Refusing to overwrite later-stage progress")
    if any(state["stage_a_slices"][f"A{number}"]["status"] != "PASS" for number in range(1, 7)):
        raise ValueError("A required slice is not passed")
    state.update(
        recorded_date_utc=json.loads((SCOPE / "a6/coverage.json").read_text())["meta"]["timestamp"][
            :10
        ],
        status="STAGE_A_COMPLETE_FULL_SCOPE_NOT_READY",
        current_stage="B",
        last_pass_stage="A",
        checkpoint_form="STAGE_A_FOUNDATIONS_COMPLETE_B_G_NOT_STARTED",
        remaining_stage_a_work=[],
        resume_note="Stage A is complete at the enclosing A6 checkpoint. Read Stage B governing "
        "clauses before implementation; full-package reading and B-G completion remain pending. "
        "No release, model, broker, promotion or trading authority is granted.",
    )
    state["stages"]["A"] = "PASS"
    state["execution_environment"]["status"] = "PASS_FOR_STAGE_A_OFFLINE_EXECUTION"
    state["execution_environment"]["full_runtime_safety_suite"] = (
        "STAGE_A_PASS_FULL_STAGE_G_SCOPE_PENDING"
    )
    evidence = state["evidence"]
    for key, path in (
        ("requirement_universe", ROOT / "evidence/requirement_universe.csv"),
        ("traceability", ROOT / "evidence/traceability.csv"),
        ("requirement_universe_report", ROOT / "evidence/REQUIREMENT_UNIVERSE_REPORT.json"),
    ):
        evidence[key + "_sha256"] = sha(path)
    evidence.update(
        traceability_status="STAGE_A_27_OF_27_PASS_GLOBAL_B_G_MAPPINGS_PENDING",
        stage_a_completion_path=str(COMPLETION.relative_to(ROOT)),
        stage_a_completion_sha256=sha(COMPLETION),
        traceability_totals={**summary["global_final_status_counts"], "source_count_conflicts": 0},
        source_verification_path="evidence/stage_a/a6/preflight.json",
        source_verification_sha256=sha(SCOPE / "a6/preflight.json"),
        r2_handoff_status="STAGE_A_COMPLETE_FULL_SCOPE_NOT_READY_FOR_ACCEPTANCE",
    )
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    REPORT.write_text(
        json.dumps({"decision": "PASS_STAGE_A_FOUNDATIONS_ONLY", **summary}, indent=2) + "\n"
    )


def main():
    if sys.argv[1:] == ["--write"]:
        records, fields = stage_rows()
        COMPLETION.write_bytes(encoded(records, fields))
        update_global()
        summary = check()
        REPORT.write_text(
            json.dumps({"decision": "TRACEABILITY_PREPARED_A6_GATE_PENDING", **summary}, indent=2)
            + "\n"
        )
    elif sys.argv[1:] in (["--check"], ["--finalize"]):
        summary = check()
        if sys.argv[1] == "--finalize":
            finalize(summary)
    else:
        raise ValueError("Use --write, --check or --finalize")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
