"""Kill explicit safety-critical mutants in disposable repository-local copies."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOADER = "v3/offline/fixture_policy_loader.py"
CLOCK = "v3/offline/calendar_completion.py"
TIERS = "v3/offline/effective_policy.py"


def main() -> None:
    originals = {name: (ROOT / name).read_bytes() for name in (LOADER, CLOCK, TIERS)}
    mutations = [
        (
            "signature_verification_removed",
            LOADER,
            "Ed25519PublicKey.from_public_bytes(public_key).verify(\n"
            "            signature, SIGNATURE_DOMAIN + manifest\n"
            "        )",
            "pass",
            "tests/v3/test_fixture_policy_loader.py::test_mutating_any_authenticated_input_denies[2]",
        ),
        (
            "payload_hash_check_removed",
            LOADER,
            "if payload_hash != expected_hash:",
            "if False:",
            "tests/v3/test_fixture_policy_loader.py::test_mutating_any_authenticated_input_denies[0]",
        ),
        (
            "fixture_domain_check_removed",
            LOADER,
            'if record["domain"] != "FIXTURE_ONLY":',
            "if False:",
            "tests/v3/test_fixture_policy_loader.py"
            "::test_signed_manifest_still_cannot_widen_scope_or_skip_bounds",
        ),
        (
            "expiry_boundary_widened",
            LOADER,
            "if not valid_from <= as_of < valid_until:",
            "if not valid_from <= as_of <= valid_until:",
            "tests/v3/test_fixture_policy_loader.py"
            "::test_validity_is_half_open_and_never_uses_wall_time",
        ),
        (
            "duplicate_key_override_allowed",
            LOADER,
            "if key in result:",
            "if False:",
            "tests/v3/test_fixture_policy_loader.py"
            "::test_duplicate_key_cannot_override_an_otherwise_valid_signed_policy",
        ),
        (
            "payload_byte_bound_removed",
            LOADER,
            "if len(payload) > bounds.max_bytes:",
            "if False:",
            "tests/v3/test_fixture_policy_loader.py"
            "::test_signed_manifest_still_cannot_widen_scope_or_skip_bounds",
        ),
        (
            "signature_domain_separator_removed",
            LOADER,
            "signature, SIGNATURE_DOMAIN + manifest",
            "signature, manifest",
            "tests/v3/test_fixture_policy_loader.py"
            "::test_signature_without_the_fixture_domain_is_not_accepted",
        ),
        (
            "replay_clock_rewind_allowed",
            CLOCK,
            "if to < self.at:",
            "if False:",
            "tests/v3/test_calendar_completion.py"
            "::test_utc_clock_is_immutable_monotonic_and_replayable",
        ),
        (
            "forming_bar_allowed",
            CLOCK,
            "not bar.complete",
            "False",
            "tests/v3/test_completed_snapshots.py"
            "::test_forming_wrong_interval_or_prior_bar_cannot_substitute",
        ),
        (
            "post_decision_revision_allowed",
            CLOCK,
            "not bar.end <= bar.revision_available_at <= replay.at",
            "False",
            "tests/v3/test_completed_snapshots.py"
            "::test_post_decision_or_pre_completion_evidence_is_not_available",
        ),
        (
            "untrusted_event_clock_domain_allowed",
            CLOCK,
            'self.domain != "SIMULATED_REPLAY"',
            "False",
            "tests/v3/test_completed_snapshots.py"
            "::test_invalid_clock_replay_or_calendar_evidence_returns_explicit_data_denial",
        ),
        (
            "closed_session_boundary_allowed",
            CLOCK,
            "calendar.session_open <= replay.at < calendar.session_close",
            "calendar.session_open <= replay.at <= calendar.session_close",
            "tests/v3/test_completed_snapshots.py::test_invalid_or_closed_session_cannot_be_fresh",
        ),
        (
            "t3_owner_floor_widened",
            TIERS,
            "or tighter < floor",
            "or False",
            "tests/v3/test_policy_foundations.py::test_any_t3_rr_below_signed_owner_floor_denies",
        ),
        (
            "t1_mandatory_checks_removed",
            TIERS,
            "not T1_REQUIRED_CHECKS <= set(policy.required_checks)",
            "False",
            "tests/v3/test_policy_foundations.py"
            "::test_t1_and_unselected_or_unsupported_t2_parameters_deny",
        ),
    ]
    results = []
    for name, module, before, after, selector in mutations:
        original = originals[module].decode()
        if original.count(before) != 1:
            raise ValueError(f"Mutation anchor is no longer unique: {name}")
        with tempfile.TemporaryDirectory(prefix=".stage-a-mutation-", dir=ROOT) as directory:
            copy = Path(directory)
            for tree in ("v3", "tests/v3", "fixtures/stage_a"):
                shutil.copytree(
                    ROOT / tree, copy / tree, ignore=shutil.ignore_patterns("__pycache__")
                )
            (copy / "evidence/preflight").mkdir(parents=True)
            shutil.copyfile(
                ROOT / "evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json",
                copy / "evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json",
            )
            shutil.copyfile(ROOT / "pyproject.toml", copy / "pyproject.toml")
            (copy / module).write_text(original.replace(before, after))
            command = [sys.executable, "-m", "pytest", "-q", selector, "--junitxml=result.xml"]
            result = subprocess.run(
                command,
                cwd=copy,
                env={
                    **os.environ,
                    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONPATH": str(copy),
                },
                capture_output=True,
                text=True,
                timeout=30,
            )
            junit = ET.parse(copy / "result.xml").getroot()
            suites = list(junit.iter("testsuite"))
            failures = sum(int(suite.attrib["failures"]) for suite in suites)
            errors = sum(int(suite.attrib["errors"]) for suite in suites)
            if result.returncode != 1 or failures == 0 or errors != 0:
                raise RuntimeError(
                    f"Mutant survived or did not fail a real assertion: {name}\n"
                    f"{result.stdout}\n{result.stderr}"
                )
            results.append(
                {
                    "mutation": name,
                    "module": module,
                    "original_sha256": hashlib.sha256(originals[module]).hexdigest(),
                    "test": selector,
                    "exit_code": result.returncode,
                    "assertion_failures": failures,
                    "collection_errors": errors,
                    "status": "KILLED",
                }
            )
    if any((ROOT / module).read_bytes() != content for module, content in originals.items()):
        raise RuntimeError("Mutation harness changed the real source")
    print(json.dumps({"mutations": results, "killed": len(results), "survived": 0}, indent=2))


if __name__ == "__main__":
    main()
