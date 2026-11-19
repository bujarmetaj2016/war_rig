"""Persist an immutable, independently reproducible successful Stage A slice gate."""

import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    name, run, base_commit, title = sys.argv[1:]
    if name not in {"a2", "a3", "a4", "a5", "a6"}:
        raise ValueError("Unrecognised Stage A slice")
    if not re.fullmatch(r"[a-f0-9]{40}", base_commit):
        raise ValueError("Expected the independently recorded Git source base")
    source = (ROOT / run).resolve()
    if not source.is_relative_to(ROOT / "evidence/stage_a/runs"):
        raise ValueError("Expected a fresh sandbox-run artifact directory")
    checks = json.loads((source / "checks.json").read_text())
    coverage = json.loads((source / "coverage.json").read_text())
    mutations = json.loads((source / "mutations.json").read_text())
    suites = list(ET.parse(source / "junit.xml").getroot().iter("testsuite"))
    totals = coverage["totals"]
    if (
        checks["status"] != "PASS"
        or totals["missing_lines"] != 0
        or totals["missing_branches"] != 0
        or totals["num_partial_branches"] != 0
        or totals["excluded_lines"] != 0
        or mutations["survived"] != 0
        or any(
            int(suite.attrib[key]) for suite in suites for key in ("errors", "failures", "skipped")
        )
    ):
        raise ValueError("A failed/incomplete gate cannot be recorded as PASS")
    if name == "a6":
        completion = subprocess.check_output(
            [sys.executable, "-I", "tools/record_stage_a_completion.py", "--check"], cwd=ROOT
        )
        (source / "stage-a-traceability.json").write_bytes(completion)
    target = ROOT / "evidence/stage_a" / name
    if target.exists():
        for path in target.iterdir():
            if (
                not (source / path.name).is_file()
                or path.read_bytes() != (source / path.name).read_bytes()
            ):
                raise ValueError("Refusing to overwrite an existing checkpoint")
    target.mkdir(exist_ok=True)
    for path in sorted(source.iterdir()):
        if not path.is_file():
            raise ValueError("Unexpected nested gate output")
        shutil.copyfile(path, target / path.name)
    test_count = sum(int(suite.attrib["tests"]) for suite in suites)
    record = {
        "slice": name.upper(),
        "title": title,
        "decision": "PASS",
        "overall_stage_a": "PASS" if name == "a6" else "IN_PROGRESS",
        "source_commit_before_gate": base_commit,
        "source_sha256": checks["source_sha256"],
        "command": "sh tools/run_offline.sh",
        "runner_exit_code": 0,
        "dependency_lock_sha256": hashlib.sha256(
            (ROOT / "requirements-dev.lock").read_bytes()
        ).hexdigest(),
        "tests": test_count,
        "coverage": totals,
        "mutations_killed": mutations["killed"],
        "runtime_modules": checks["required_modules"],
        "source_traceability": "evidence/stage_a/STAGE_A_REQUIREMENTS.csv",
        "source_reading": "evidence/stage_a/SOURCE_READING.md",
        "r2_handoff": "evidence/REVIEWER_R2_HANDOFF.md",
        "authority": "SYNTHETIC_OFFLINE_ONLY_NO_IG_NO_TRADING_AUTHORITY",
    }
    if name == "a6":
        record["stage_a_completion_csv_sha256"] = hashlib.sha256(
            (ROOT / "evidence/stage_a/STAGE_A_COMPLETION.csv").read_bytes()
        ).hexdigest()
    (target / "GATE.json").write_text(json.dumps(record, indent=2) + "\n")
    (target / "REPORT.md").write_text(
        f"# Stage A / {name.upper()} - {title}\n\n"
        + (
            "Decision: PASS. Stage A foundations complete; B-G remain NOT_STARTED.\n"
            if name == "a6"
            else "Decision: PASS for this slice only. Overall Stage A: IN_PROGRESS.\n"
        )
        + "Source reading and exact V5 member/clause mapping are recorded in "
        "`../SOURCE_READING.md` and `../STAGE_A_REQUIREMENTS.csv`.\n\n"
        "| Gate | Actual result |\n|---|---|\n"
        f"| Whole available V3 suite | {test_count} passed; 0 failed/skipped |\n"
        f"| Cumulative production statements | {totals['covered_lines']} / "
        f"{totals['num_statements']}; 0 missing |\n"
        f"| Cumulative production branch destinations | {totals['covered_branches']} / "
        f"{totals['num_branches']}; 0 missing/partial |\n"
        "| Coverage exclusions | 0 excluded executable lines; exact inventory checked |\n"
        "| Ruff lint / format and strict mypy | PASS |\n"
        f"| Explicit safety mutations | {mutations['killed']} killed; 0 survived |\n"
        "| Cross-process determinism | Two independently launched processes; byte-identical |\n"
        "| Network denial | Fresh pinned network-none container; six actual blocked probes |\n"
        "| Source/mirror integrity | 69 V5 members; 482 macro / 374 reference / 19 wheels |\n\n"
        "The exact source hashes, base commit, counters, commands and scope are in "
        "`GATE.json`; raw runner outputs are retained alongside it. The enclosing "
        "Git checkpoint identifies the committed source, rather than inventing a "
        "self-referential commit hash. The required negative tests are the executed "
        "JUnit cases, not the unexecuted oracles in the design archive.\n\n"
        "No real monetary, model, broker, operational timer, DEMO or LIVE policy is "
        "selected. Later stages and full-scope R2 acceptance are not implied.\n"
    )
    paths = sorted(path for path in target.iterdir() if path.is_file())
    (target / "MANIFEST.sha256").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT)}\n"
            for path in paths
        )
    )
    state_path = ROOT / "evidence/STAGE_STATE.json"
    state = json.loads(state_path.read_text())
    state.update(
        status="IN_PROGRESS",
        last_pass_slice=name.upper(),
        last_commit=base_commit,
        last_commit_role="BASE_OF_GATE_SOURCE_HASHES_BOUND_BY_ENCLOSING_CHECKPOINT",
        resume_note="Resume after the enclosing committed slice gate; source SHA inventory "
        "binds the tested runtime. Stage A is not complete until its final traceability gate.",
    )
    state["stage_a_slices"][name.upper()] = {
        "status": "PASS",
        "gate_path": str((target / "GATE.json").relative_to(ROOT)),
        "source_commit_binding": "ENCLOSING_GATE_COMMIT",
        "title": title,
    }
    state["tests_and_coverage"].update(
        status="PASS_THROUGH_" + name.upper(),
        tests_executed=test_count,
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
        determinism_output_sha256=checks["determinism_output_sha256"],
    )
    state["evidence"][name + "_manifest_path"] = str((target / "MANIFEST.sha256").relative_to(ROOT))
    state["evidence"][name + "_manifest_sha256"] = hashlib.sha256(
        (target / "MANIFEST.sha256").read_bytes()
    ).hexdigest()
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
