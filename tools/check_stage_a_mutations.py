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
PLUGINS = "v3/offline/plugin_manifest.py"
REGISTRY = "v3/offline/contract_listing_registry.py"
PREDICTIONS = "v3/offline/offline_scenario_runner.py"
MODELS = "v3/offline/model_intake.py"
MACRO = "v3/offline/macro_features.py"


def main() -> None:
    originals = {
        name: (ROOT / name).read_bytes()
        for name in (LOADER, CLOCK, TIERS, PLUGINS, REGISTRY, PREDICTIONS, MODELS, MACRO)
    }
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
        (
            "fixture_leaf_symlink_followed",
            LOADER,
            "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK",
            "os.O_RDONLY | os.O_NONBLOCK",
            "tests/v3/test_fixture_filesystem.py"
            "::test_even_authentic_bytes_cannot_be_followed_through_a_symlink",
        ),
        (
            "fixture_total_byte_limit_removed",
            LOADER,
            "if len(payload) + len(manifest) + len(signature_text) > policy.max_total_bytes:",
            "if False:",
            "tests/v3/test_fixture_filesystem.py"
            "::test_exact_inventory_file_and_total_limits_are_enforced[total_bytes]",
        ),
        (
            "plugin_network_capability_allowed",
            PLUGINS,
            'or set(_strings(item["capabilities"])) != {_INTERFACES[interface][1]}',
            "or False",
            "tests/v3/test_instrument_registration.py"
            "::test_capability_guard_is_independent_of_exact_source_build_integrity",
        ),
        (
            "registration_expected_version_removed",
            REGISTRY,
            "expected != len(self._events)",
            "False",
            "tests/v3/test_instrument_registration.py"
            "::test_expected_state_guard_is_independent_of_build_integrity",
        ),
        (
            "missing_listing_field_allowed",
            REGISTRY,
            "if names != ECONOMICS_FIELDS:",
            "if False:",
            "tests/v3/test_instrument_registration.py"
            "::test_missing_fee_evidence_cannot_use_an_assumed_definition_value",
        ),
    ]
    mutations.extend(
        [
            (
                "model_declared_bytes_ignored",
                MODELS,
                'len(raw) != _integer(file["bytes"])',
                "False",
                "tests/v3/test_model_intake.py::test_declared_file_bytes_are_independent_of_correct_hashes",
            ),
            (
                "tree_split_reversed",
                MODELS,
                "value < self.conditions[node]",
                "value > self.conditions[node]",
                "tests/v3/test_model_intake.py::test_full_path_hand_constants_signed_artifacts_determinism_and_source_separation",
            ),
            (
                "model_numeric_domain_removed",
                MODELS,
                "if abs(margin) > 100:",
                "if False:",
                "tests/v3/test_model_intake.py::test_platt_and_logistic_numerics_are_pure_registered_constant_proofs",
            ),
            (
                "source_selection_guard_removed",
                PREDICTIONS,
                "if provider.kind != kind or provider.sha256 != source_hash:",
                "if False:",
                "tests/v3/test_prediction_pipeline.py::test_unregistered_source_is_not_called_even_once",
            ),
            (
                "confidence_conservative_caps_removed",
                PREDICTIONS,
                "min(tier, policy.cap, data_quality, conservative_cap)",
                "tier",
                "tests/v3/test_prediction_pipeline.py::test_signed_pipeline_repeat_reload_source_labels_and_caps",
            ),
            (
                "own_currency_in_basket",
                MACRO,
                "pair != instrument",
                "True",
                "tests/v3/test_macro_features.py::test_ex_own_currency_equal_weight_signs_and_sample_std",
            ),
            (
                "event_at_entry_not_before",
                MACRO,
                "timedelta(0) < scheduled - entry",
                "timedelta(days=-1) < scheduled - entry",
                "tests/v3/test_macro_features.py::test_all_five_instruments_event_window_boundary_is_strictly_before_release",
            ),
            (
                "stale_macro_becomes_neutral",
                MACRO,
                'return "UNKNOWN", None, None, "STALE_LEG:" + pair',
                'return "NEUTRAL", None, None, "STALE_LEG:" + pair',
                "tests/v3/test_macro_features.py::test_unknown_is_not_a_neutral_or_success_fallback",
            ),
            (
                "macro_changes_prediction_grade",
                MACRO,
                "return ObservedPrediction(score, observation)",
                "return ObservedPrediction("
                'score.__class__(**(score.__dict__ | {"grade": "D"})), observation)',
                "tests/v3/test_macro_features.py"
                "::test_observation_mutations_cannot_change_existing_prediction_decision_or_risk_caps",
            ),
        ]
    )
    results = []
    for name, module, before, after, selector in mutations:
        original = originals[module].decode()
        if original.count(before) != 1:
            raise ValueError(f"Mutation anchor is no longer unique: {name}")
        with tempfile.TemporaryDirectory(prefix=".stage-a-mutation-", dir=ROOT) as directory:
            copy = Path(directory)
            for tree in ("v3", "tests/v3", "fixtures/stage_a", "tools"):
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
