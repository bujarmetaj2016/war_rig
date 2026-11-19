import copy
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pytest
from test_completed_snapshots import daily_record
from test_completed_snapshots import record as snapshot_record
from test_fixture_policy_loader import signed

from tools.create_stage_a_registration_fixtures import build_artifacts
from v3.offline.data_intake_schema import load_snapshot_fixture
from v3.offline.intent_identity import (
    Digest,
    Identity,
    InstrumentId,
    MarketId,
    PolicyId,
    RunContext,
    RunId,
    SimulatedAccountId,
)
from v3.offline.offline_scenario_runner import (
    PredictionDenied,
    PredictionRecordKind,
    SourceKind,
    canonical,
    evaluate_prediction,
    fingerprint,
    grouped_report,
    load_confidence_policy,
    load_feature_row,
    load_prediction_plugins,
    load_run_manifest,
    make_signal,
    number,
    prediction_reference,
)
from v3.offline.offline_scenario_runner import (
    load_score_table as load_registered_score_table,
)
from v3.offline.plugin_manifest import build_fingerprint


def plugin_body():
    root = Path(__file__).resolve().parents[2]
    artifacts = build_artifacts(
        source_paths=tuple(str(path.relative_to(root)) for path in (root / "v3").rglob("*.py"))
    )
    build = build_fingerprint(artifacts).value
    sources = {artifact.module: artifact for artifact in artifacts}
    definitions = (
        (
            "SIGNED_SCORE",
            "SIGNED_SCORE_V1",
            "v3.offline.offline_scenario_runner",
            "PURE_SIGNED_SCORE",
        ),
        ("MODEL_SCORE", "MODEL_SCORE_V1", "v3.offline.model_intake", "NONEXECUTABLE_JSON_READER"),
        (
            "MACRO_OBSERVATION",
            "MACRO_OBSERVATION_V1",
            "v3.offline.macro_features",
            "COMPUTE_AND_LOG_ONLY",
        ),
    )
    return {
        "kind": "FIXTURE_PREDICTION_PLUGINS_V1",
        "build_sha256": build,
        "entries": [
            {
                "plugin_id": plugin,
                "interface_id": interface,
                "source_import_path": path,
                "artifact_sha256": sources[path].sha256.value,
                "version": "1.0.0",
                "schema_version": "1.0.0",
                "capabilities": [capability],
                "permitted_build_id": build,
                "dependencies": list(sources[path].dependencies),
            }
            for plugin, interface, path, capability in definitions
        ],
    }, artifacts


@lru_cache
def prediction_plugins():
    body, artifacts = plugin_body()
    return load_prediction_plugins(
        *signed(policy=body, manifest_updates={"max_nodes": 1024}), artifacts
    )


def load_score_table(*bundle):
    return load_registered_score_table(*bundle, prediction_plugins())


POLICY = {
    "kind": "FIXTURE_CONFIDENCE_POLICY_V1",
    "cap": "0.5",
    "bands": [
        {"grade": grade, "threshold": threshold, "tier": tier}
        for grade, threshold, tier in zip(
            "ABCD", ("0.6", "0.45", "0.3", "0"), ("0.4", "0.3", "0.2", "0"), strict=True
        )
    ],
}


def load_policy(value=None):
    return load_confidence_policy(*signed(policy=POLICY if value is None else value))


def feature_bundle(
    *,
    values=("6",),
    names=("x",),
    schema_sha256="2" * 64,
    instrument="SYNTHETIC_6",
    snapshot_value=None,
):
    policy = load_policy()
    vector = {"names": list(names), "dtypes": ["DECIMAL"] * len(names), "values": list(values)}
    original = snapshot_record() if snapshot_value is None else copy.deepcopy(snapshot_value)
    original.update(
        policy_sha256=policy.sha256,
        feature_schema_sha256=schema_sha256,
        feature_row_sha256=fingerprint(vector),
        instrument_id=instrument,
    )
    snapshot = load_snapshot_fixture(
        *signed(policy=original, manifest_updates={"max_bytes": 65536, "max_nodes": 256})
    )
    context = RunContext(
        RunId(snapshot.binding.run_id),
        SimulatedAccountId(snapshot.binding.account_id),
        MarketId("SYNTHETIC_MARKET"),
        InstrumentId(instrument),
        PolicyId("SYNTHETIC_POLICY"),
        Digest(policy.sha256),
        prediction_plugins().build_sha256,
        Digest(snapshot.lineage.snapshot_sha256),
        Digest(schema_sha256),
        Identity(snapshot.clock.source_clock_id),
        snapshot.clock.at - timedelta(days=1),
        snapshot.clock.at + timedelta(days=1),
    )
    body = vector | {
        "kind": "SIGNED_FEATURE_ROW_V1",
        "row_sha256": fingerprint(vector),
        "snapshot_sha256": snapshot.lineage.snapshot_sha256,
        "schema_sha256": schema_sha256,
        "event_id": snapshot.lineage.source_event_id,
        "available_at": str(snapshot.clock.at),
        "context_sha256": context.sha256,
    }
    return body, snapshot, context, policy


def load_feature(body=None, snapshot=None, context=None, **kwargs):
    original, snap, ctx, _ = feature_bundle(**kwargs)
    return load_feature_row(
        *signed(policy=original if body is None else body),
        snap if snapshot is None else snapshot,
        ctx if context is None else context,
    )


def score_body(row):
    return {
        "kind": "SIGNED_TEST_SCORE_V1",
        "rows": [
            {
                "feature_row_sha256": row.row_sha256,
                "direction": "BULLISH",
                "raw": "0.9",
                "probability": "0.8",
                "lower_bound": "0.6",
            }
        ],
    }


def run_body(row, source):
    return {
        "kind": "FIXTURE_PREDICTION_RUN_V1",
        "run_id": row.context.run.value,
        "account_id": row.context.account.value,
        "runtime_profile": "G1_R",
        "valid_from": str(row.context.valid_from),
        "valid_until": str(row.context.valid_until),
        "sources": [
            {
                "instrument": row.context.instrument.value,
                "source_kind": source.kind,
                "fingerprint": source.source_fingerprint,
            }
        ],
    }


def pipeline(*, instrument="SYNTHETIC_6"):
    row = load_feature(instrument=instrument)
    table = load_score_table(*signed(policy=score_body(row)))
    source = table.score(row)
    run = load_run_manifest(*signed(policy=run_body(row, source)))
    return row, source, run, load_policy()


def signal(row, source, run, policy, **kwargs):
    args = {
        "runtime_profile": "G1_R",
        "data_quality": Decimal("0.8"),
        "climate": None,
        "conservative_cap": Decimal("0.15"),
    }
    args.update(kwargs)
    return make_signal(source, row, run, policy, row.available_at, **args)


def test_signed_pipeline_repeat_reload_source_labels_and_caps():
    row, source, run, policy = pipeline()
    first = signal(row, source, run, policy)
    assert first.encoded == signal(*pipeline()).encoded
    assert first.grade == "A" and first.base_tier == Decimal("0.4")
    assert first.conservative_tier == Decimal("0.15")
    assert first.raw_score == Decimal("0.9") and first.confidence == Decimal("0.6")
    assert first.calibrated_probability == Decimal("0.8") and first.climate is None
    assert first.labels == ("NOT_PERFORMANCE_EVIDENCE", "NOT_A_MODEL_PREDICTION")
    assert first.evidence_class == "PIPELINE_VALIDATION_ONLY"
    assert dict(grouped_report((first,)))[SourceKind.TRAINED_MODEL] == ()
    assert canonical({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
    with pytest.raises(FrozenInstanceError):
        run.sources = ()
    with pytest.raises(FrozenInstanceError):
        first.grade = "D"


def test_daily_features_and_prediction_remain_valid_after_close_until_data_max_age():
    body, snapshot, context, policy = feature_bundle(snapshot_value=daily_record())
    row = load_feature_row(*signed(policy=body), snapshot, context)
    assert row.available_at > snapshot.calendar.session_close
    assert row.expires_at == row.bar_end + timedelta(seconds=600)
    table = load_score_table(*signed(policy=score_body(row)))
    source = table.score(row)
    run = load_run_manifest(*signed(policy=run_body(row, source)))
    result = signal(row, source, run, policy)
    assert result.created_at == row.available_at and result.grade == "A"
    capped_context = replace(context, valid_until=row.available_at + timedelta(seconds=1))
    capped_body = body | {"context_sha256": capped_context.sha256}
    capped = load_feature_row(*signed(policy=capped_body), snapshot, capped_context)
    assert capped.expires_at == capped_context.valid_until
    denied = evaluate_prediction(
        table,
        row,
        run,
        policy,
        row.expires_at + timedelta(microseconds=1),
        runtime_profile="G1_R",
        data_quality=Decimal("0.8"),
        climate=None,
        conservative_cap=Decimal("0.15"),
    )
    assert denied.score is None and denied.audit.status == "NOT_PROVEN"


@pytest.mark.parametrize("value", ["-1", "0", "0.0001", "123", "-0.2"])
def test_exact_feature_numbers(value):
    assert number(value) == Decimal(value)


@pytest.mark.parametrize("value", ["NaN", "1e2", "+1", "01", ".1", "1.", "1" * 19, True, 1, None])
def test_no_numeric_coercion(value):
    with pytest.raises(ValueError):
        number(value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "MODEL"),
        ("dtypes", "DECIMAL"),
        ("dtypes", ["FLOAT"]),
        ("values", []),
        ("values", "6"),
        ("values", [1]),
        ("names", ["x", "x"]),
        ("row_sha256", "9" * 64),
        ("snapshot_sha256", "9" * 64),
        ("schema_sha256", "9" * 64),
        ("context_sha256", "9" * 64),
        ("available_at", "2020-01-01T00:00:00Z"),
    ],
)
def test_signed_feature_lineage_failures(field, value):
    body, snapshot, context, _ = feature_bundle()
    body[field] = value
    with pytest.raises(ValueError):
        load_feature(body, snapshot, context)


def test_ordered_multiple_and_explicit_missing_features():
    row = load_feature(values=("1", None), names=("x", "y"))
    assert row.values == (Decimal(1), None) and row.dtypes == ("DECIMAL", "DECIMAL")


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "MODEL"),
        ("sources", []),
        ("sources", {}),
        ("account_id", "REAL_ACCOUNT"),
        ("valid_until", "2020-01-01T00:00:00Z"),
    ],
)
def test_run_manifest_rejects_bad_bindings(field, value):
    row, source, _, _ = pipeline()
    body = run_body(row, source)
    body[field] = value
    with pytest.raises(ValueError):
        load_run_manifest(*signed(policy=body))


def test_duplicate_instrument_sources_deny_even_when_the_kind_or_fingerprint_matches():
    row, source, _, _ = pipeline()
    body = run_body(row, source)
    body["sources"] *= 2
    with pytest.raises(PredictionDenied):
        load_run_manifest(*signed(policy=body))


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "TRAINED_MODEL"),
        ("rows", []),
        ("rows", {}),
    ],
)
def test_unregistered_signed_scores_are_not_model_predictions(field, value):
    body = score_body(load_feature())
    body[field] = value
    with pytest.raises(ValueError):
        load_score_table(*signed(policy=body))


@pytest.mark.parametrize(
    "field,value",
    [
        ("direction", "NONE"),
        ("lower_bound", "0.9"),
        ("probability", "1.1"),
        ("raw", "NaN"),
    ],
)
def test_bad_score_values(field, value):
    body = score_body(load_feature())
    body["rows"][0][field] = value
    with pytest.raises(ValueError):
        load_score_table(*signed(policy=body))


def test_no_latest_fixture_or_unknown_feature_fallback():
    row = load_feature()
    body = score_body(row)
    body["rows"] *= 2
    with pytest.raises(PredictionDenied):
        load_score_table(*signed(policy=body))
    table = load_score_table(*signed(policy=score_body(row)))
    with pytest.raises(PredictionDenied, match="NOT_PROVEN"):
        table.score(replace(row, row_sha256="9" * 64))
    payload, manifest, signature, key = signed(policy=score_body(row))
    with pytest.raises(ValueError):
        load_score_table(payload + b" ", manifest, signature, key)
    with pytest.raises(ValueError):
        load_score_table(payload, manifest, b"\x00" * 64, key)


@pytest.mark.parametrize("field,value", [("kind", "LIVE"), ("bands", {}), ("cap", "1.1")])
def test_unselected_confidence_policy_denies(field, value):
    with pytest.raises(ValueError):
        load_policy(POLICY | {field: value})


@pytest.mark.parametrize(
    "index,field,value",
    [
        (0, "grade", "D"),
        (3, "threshold", "0.1"),
        (1, "threshold", "0.9"),
        (1, "tier", "0.9"),
        (0, "tier", "2"),
    ],
)
def test_nonmonotonic_policy_or_missing_grade_denies(index, field, value):
    body = copy.deepcopy(POLICY)
    body["bands"][index][field] = value
    with pytest.raises(ValueError):
        load_policy(body)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_fingerprint", "9" * 64),
        ("kind", SourceKind.TRAINED_MODEL),
        ("feature_row_sha256", "9" * 64),
        ("direction", "NONE"),
        ("calibration_status", "LONG_ONLY"),
        ("probability", None),
        ("lower_bound", None),
        ("probability", Decimal("1.1")),
        ("raw_score", Decimal("NaN")),
        ("lower_bound", Decimal("-0.1")),
        ("probability", Decimal("Infinity")),
        ("lower_bound", Decimal("NaN")),
    ],
)
def test_source_change_relabel_or_bad_calibration_denies_without_fallback(field, value):
    row, source, run, policy = pipeline()
    with pytest.raises(PredictionDenied, match="NO_AUTHORITATIVE_PREDICTION"):
        signal(row, replace(source, **{field: value}), run, policy)


@pytest.mark.parametrize(
    "field,value",
    [
        ("data_quality", Decimal("-1")),
        ("data_quality", Decimal("NaN")),
        ("conservative_cap", Decimal("2")),
        ("conservative_cap", Decimal("NaN")),
        ("climate", Decimal("101")),
        ("climate", Decimal("NaN")),
        ("runtime_profile", "LIVE"),
    ],
)
def test_caps_and_runtime_profile_are_restrictions_not_risk_overrides(field, value):
    with pytest.raises(PredictionDenied):
        signal(*pipeline(), **{field: value})


def test_monotonic_bands_climate_is_not_a_calibration_or_size_multiplier():
    row, source, run, policy = pipeline()
    tiers = []
    for bound in ("0", "0.3", "0.45", "0.6", "0.8"):
        score = replace(source, lower_bound=Decimal(bound))
        low = signal(row, score, run, policy, climate=Decimal(0))
        high = signal(row, score, run, policy, climate=Decimal(100))
        assert low.conservative_tier == high.conservative_tier <= Decimal("0.15")
        tiers.append(low.base_tier)
    assert tiers == sorted(tiers)
    for changed in (
        replace(run, run_id="OTHER"),
        replace(run, account_id="SIMULATED_OTHER"),
        replace(run, valid_until=row.available_at),
        replace(run, valid_from=row.available_at + timedelta(seconds=1)),
    ):
        with pytest.raises(PredictionDenied):
            signal(row, source, changed, policy)
    with pytest.raises(PredictionDenied):
        signal(row, source, run, replace(policy, sha256="9" * 64))
    # Artifact replacement changes attribution, never the canonical source-event intent.
    changed = replace(source, source_fingerprint="9" * 64)
    newrun = replace(
        run, sources=((row.context.instrument.value, changed.kind, changed.source_fingerprint),)
    )
    assert (
        signal(row, changed, newrun, policy).intent_id == signal(row, source, run, policy).intent_id
    )
    assert (
        signal(row, changed, newrun, policy).prediction_id
        != signal(row, source, run, policy).prediction_id
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "LIVE"),
        ("build_sha256", "9" * 64),
        ("entries", []),
        ("entries", {}),
    ],
)
def test_prediction_registry_is_signed_explicit_and_build_bound(field, value):
    body, artifacts = plugin_body()
    body[field] = value
    with pytest.raises(ValueError):
        load_prediction_plugins(
            *signed(policy=body, manifest_updates={"max_nodes": 1024}), artifacts
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("interface_id", "EXECUTE"),
        ("capabilities", ["NETWORK"]),
        ("dependencies", {}),
        ("dependencies", []),
        ("source_import_path", "reference.v2_snapshot"),
        ("artifact_sha256", "9" * 64),
        ("version", "2.0.0"),
        ("schema_version", "2.0.0"),
        ("permitted_build_id", "9" * 64),
    ],
)
def test_prediction_registry_capabilities_and_dependencies_cannot_widen(field, value):
    body, artifacts = plugin_body()
    body["entries"][0][field] = value
    with pytest.raises(ValueError):
        load_prediction_plugins(
            *signed(policy=body, manifest_updates={"max_nodes": 1024}), artifacts
        )


def test_both_sources_required_and_duplicate_plugins_are_not_discovery():
    body, artifacts = plugin_body()
    body["entries"] = body["entries"][:1]
    with pytest.raises(PredictionDenied, match="Both prediction"):
        load_prediction_plugins(*signed(policy=body), artifacts)
    body, artifacts = plugin_body()
    body["entries"].append(body["entries"][0])
    with pytest.raises(PredictionDenied, match="Unregistered"):
        load_prediction_plugins(
            *signed(policy=body, manifest_updates={"max_nodes": 1024}), artifacts
        )
    with pytest.raises(ValueError, match="Absent"):
        load_registered_score_table(
            *signed(policy=score_body(load_feature())), replace(prediction_plugins(), entries=())
        )


def test_source_dispatch_audit_reload_lineage_and_expiry_are_fail_closed():
    row, source, run, policy = pipeline()
    table = load_score_table(*signed(policy=score_body(row)))
    args = {
        "runtime_profile": "G1_R",
        "data_quality": Decimal("1"),
        "climate": None,
        "conservative_cap": Decimal("0.1"),
    }
    first = evaluate_prediction(table, row, run, policy, row.available_at, **args)
    assert first.score is not None
    assert first.audit.prediction_id == first.score.prediction_id
    assert first == evaluate_prediction(table, row, run, policy, row.available_at, **args)
    for kind in PredictionRecordKind:
        reference = prediction_reference(first.score, kind, "RECORD_1", "3" * 64)
        assert reference.prediction_id == first.score.prediction_id
        assert reference.intent_id == first.score.intent_id
        assert reference.source_kind is SourceKind.SIGNED_TEST_SCORE
    assert (
        evaluate_prediction(None, row, run, policy, row.available_at, **args).audit.status
        == "NOT_PROVEN"
    )
    absent = evaluate_prediction(
        table, row, replace(run, sources=()), policy, row.available_at, **args
    )
    assert absent.score is None and absent.audit.status == "NO_AUTHORITATIVE_PREDICTION"
    trained = replace(
        run, sources=((row.context.instrument.value, SourceKind.TRAINED_MODEL, table.sha256),)
    )
    denied = evaluate_prediction(table, row, trained, policy, row.available_at, **args)
    assert denied.score is None and "replacement/relabel" in denied.audit.reason
    assert denied.audit.status == "NO_AUTHORITATIVE_PREDICTION"
    failed = evaluate_prediction(
        table, replace(row, row_sha256="9" * 64), run, policy, row.available_at, **args
    )
    assert failed.score is None and "NOT_PROVEN" in failed.audit.reason
    expired = evaluate_prediction(
        table, row, run, policy, row.expires_at + timedelta(microseconds=1), **args
    )
    assert expired.score is None and "NO_AUTHORITATIVE_PREDICTION" in expired.audit.reason

    class RelabelingSource:
        kind = SourceKind.SIGNED_TEST_SCORE
        sha256 = table.sha256

        def score(self, row):
            return replace(source, kind=SourceKind.TRAINED_MODEL)

    relabeled = evaluate_prediction(RelabelingSource(), row, run, policy, row.available_at, **args)
    assert relabeled.score is None and "Producer source relabel" in relabeled.audit.reason


def test_unregistered_source_is_not_called_even_once():
    from v3.offline.offline_scenario_runner import ScoreProvider

    row, _, run, policy = pipeline()

    def forbidden_score(row):
        raise AssertionError("Unregistered/relabelled source was evaluated")

    provider = ScoreProvider(SourceKind.TRAINED_MODEL, "9" * 64, forbidden_score)
    result = evaluate_prediction(
        provider,
        row,
        run,
        policy,
        row.available_at,
        runtime_profile="G1_R",
        data_quality=Decimal(1),
        climate=None,
        conservative_cap=Decimal("0.1"),
    )
    assert result.score is None and "replacement/relabel" in result.audit.reason
