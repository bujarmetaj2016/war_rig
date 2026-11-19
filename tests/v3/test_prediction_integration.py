import json
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from test_fixture_policy_loader import signed
from test_model_intake import model_fixture
from test_prediction_pipeline import (
    load_feature,
    load_policy,
    pipeline,
    prediction_plugins,
    run_body,
    signal,
)

from v3.offline.model_intake import (
    ModelDenied,
    load_synthetic_model_packet,
    synthetic_reader_provider,
)
from v3.offline.offline_scenario_runner import (
    SourceKind,
    evaluate_prediction,
    load_run_manifest,
    v2_confidence_observation,
)


def packet_bundle(files):
    return signed(
        policy={
            "kind": "SIGNED_MODEL_ARTIFACT_PACKET_V1",
            "files": {name: raw.decode() for name, raw in files},
        },
        manifest_updates={"max_bytes": 65536, "max_nodes": 1024},
    )


def test_signed_model_packet_has_no_executable_or_discovered_members():
    bundle, files = model_fixture()
    model = load_synthetic_model_packet(bundle, packet_bundle(files), prediction_plugins())
    row = load_feature(schema_sha256=model.schema_sha256)
    assert model.score(row).probability == Decimal("0.1")
    for bad_files in (
        files + (("hidden.py", b"{}"),),
        files[:1],
        files * 2 + (("extra.json", b"{}"),),
    ):
        with pytest.raises(ModelDenied):
            load_synthetic_model_packet(bundle, packet_bundle(bad_files), prediction_plugins())
    for body in (
        {"kind": "LIVE", "files": {}},
        {"kind": "SIGNED_MODEL_ARTIFACT_PACKET_V1", "files": []},
        {
            "kind": "SIGNED_MODEL_ARTIFACT_PACKET_V1",
            "files": {"model.json": {}, "schema.json": "{}"},
        },
        {
            "kind": "SIGNED_MODEL_ARTIFACT_PACKET_V1",
            "files": {"model.json": "\ud800", "schema.json": "{}"},
        },
    ):
        with pytest.raises(ModelDenied):
            load_synthetic_model_packet(bundle, signed(policy=body), prediction_plugins())
    payload, manifest, signature, key = packet_bundle(files)
    with pytest.raises(ValueError):
        load_synthetic_model_packet(
            bundle, (payload + b" ", manifest, signature, key), prediction_plugins()
        )


@pytest.mark.parametrize("instrument", ["XAUUSD", "GER40", "US500", "EURUSD", "GBPUSD"])
def test_missing_core5_models_are_explicit_null_declarations_not_fake_artifact_hashes(instrument):
    row = load_feature(instrument=instrument)
    _, source, _, _ = pipeline()
    body = run_body(row, source)
    body["sources"][0].update(source_kind="TRAINED_MODEL", fingerprint=None)
    run = load_run_manifest(*signed(policy=body))
    result = evaluate_prediction(
        None,
        row,
        run,
        load_policy(),
        row.available_at,
        runtime_profile="G1_R",
        data_quality=Decimal(1),
        climate=None,
        conservative_cap=Decimal("0.1"),
    )
    assert result.score is None and result.audit.status == "NO_AUTHORITATIVE_PREDICTION"
    assert result.audit.source_fingerprint is None
    assert result.audit.source_kind is SourceKind.TRAINED_MODEL
    body["sources"][0]["source_kind"] = "SIGNED_TEST_SCORE"
    with pytest.raises(ValueError):
        load_run_manifest(*signed(policy=body))


@pytest.mark.parametrize(
    "instrument,probability,climate,confidence,grade,label,side",
    [
        ("XAUUSD", "0.6", None, "0.6", "A", "FULL", "BULLISH"),
        ("XAUUSD", "0.45", "0", "0.45", "B", "FULL", "BEARISH"),
        ("XAUUSD", "0.3", "100", "0.3", "C", "FULL", "BEARISH"),
        ("XAUUSD", "0.299", None, "0.299", "D", "FULL", "BEARISH"),
        ("EURUSD", "0.8", "60", "0.48", "B", "FULL", "BULLISH"),
        ("GBPUSD", "0.8", "40", "0.32", "C", "HALF", "BULLISH"),
        ("EURUSD", "0.8", "39.9", "0.319", "C", "SUPPRESS", "NEUTRAL"),
        ("GER40", "0.8", "40", "0.32", "C", "FULL", "BULLISH"),
        ("US500", "0.8", "39", "0.312", "C", "SUPPRESS", "NEUTRAL"),
        ("US500", "0.5", "100", "0.5", "B", "NEUTRAL", "NEUTRAL"),
    ],
)
def test_pinned_v2_instrument_exceptions_only_log_reference_values(
    instrument,
    probability,
    climate,
    confidence,
    grade,
    label,
    side,
):
    observed = v2_confidence_observation(
        instrument, Decimal(probability), None if climate is None else Decimal(climate)
    )
    assert observed.reference_confidence == Decimal(confidence)
    assert observed.reference_grade == grade and observed.telemetry_size_label == label
    assert observed.reference_signal == side
    assert observed.calibration_status == "NOT_PROVEN"
    assert observed.mode == "COMPUTE_AND_LOG_ONLY_V2_PARITY"
    assert not hasattr(observed, "entry_permit") and not hasattr(observed, "stake")


def test_unknown_reference_climate_and_misleading_v2_short_are_not_calibrated():
    observation = v2_confidence_observation("EURUSD", Decimal("0.1"), None)
    assert observation.reference_signal == "UNKNOWN" and observation.reference_grade is None
    assert (
        observation.reference_confidence is None and observation.calibration_status == "NOT_PROVEN"
    )
    row, source, run, policy = pipeline()
    # A low long-target score and V2 bearish label cannot make an eligible short.
    with pytest.raises(ValueError):
        signal(
            row,
            replace(source, direction="BEARISH", calibration_status=observation.calibration_status),
            run,
            policy,
        )


@pytest.mark.parametrize(
    "instrument,score,climate",
    [
        ("OTHER", Decimal("0.5"), None),
        ("EURUSD", Decimal("NaN"), Decimal(50)),
        ("EURUSD", Decimal("1.1"), Decimal(50)),
        ("EURUSD", Decimal("0.5"), Decimal("Infinity")),
        ("EURUSD", Decimal("0.5"), Decimal("-1")),
    ],
)
def test_reference_does_not_impute_invalid_scores_or_climate(instrument, score, climate):
    with pytest.raises(ValueError):
        v2_confidence_observation(instrument, score, climate)


def test_rerun_id_does_not_create_new_fixture_intent_and_model_expiry_is_independent():
    row, source, run, policy = pipeline()
    first = signal(row, source, run, policy)
    context = replace(row.context, run=type(row.context.run)("SYNTHETIC_RELOADED_RUN"))
    rerun = signal(
        replace(row, context=context), source, replace(run, run_id=context.run.value), policy
    )
    assert first.intent_id == rerun.intent_id and first.prediction_id != rerun.prediction_id
    for change in (
        {"valid_until": row.available_at},
        {"runtime_profile": "LIVE"},
    ):
        with pytest.raises(ValueError):
            signal(row, replace(source, **change), run, policy)
    # Underlying data expires independently of the broader signed run interval.
    with pytest.raises(ValueError):
        signal(
            replace(row, expires_at=row.available_at - timedelta(seconds=1)), source, run, policy
        )


def test_model_load_failures_are_correlated_denials_with_no_fixture_or_training_fallback():
    bundle, files = model_fixture()
    model = load_synthetic_model_packet(bundle, packet_bundle(files), prediction_plugins())
    row = load_feature(schema_sha256=model.schema_sha256)
    source = model.score(row)
    run = load_run_manifest(*signed(policy=run_body(row, source)))
    packet = packet_bundle(files)
    args = {
        "runtime_profile": "G1_R",
        "data_quality": Decimal("0.8"),
        "climate": None,
        "conservative_cap": Decimal("0.15"),
    }
    valid = synthetic_reader_provider(bundle, packet, prediction_plugins())
    result = evaluate_prediction(valid, row, run, load_policy(), row.available_at, **args)
    assert result.score is not None and result.audit.prediction_id == result.score.prediction_id
    broken = (packet[0], packet[1], b"\0" * 64, packet[3])
    failed = synthetic_reader_provider(bundle, broken, prediction_plugins())
    denied = evaluate_prediction(failed, row, run, load_policy(), row.available_at, **args)
    assert denied.score is None and denied.audit.status == "NO_AUTHORITATIVE_PREDICTION"
    assert "authentication/time denied" in denied.audit.reason
    assert denied.audit.source_fingerprint == run.sources[0][2]
    for operation in ("FIT", "REFIT", "CALIBRATE", "TRAIN", "PROMOTE"):
        assert not hasattr(model, operation.lower())
        payload = json.loads(bundle[0])
        payload["forbidden_operation"] = operation
        unsigned = signed(policy=payload, manifest_updates={"max_bytes": 65536, "max_nodes": 1024})
        provider = synthetic_reader_provider(unsigned, packet, prediction_plugins())
        changed = replace(
            run,
            sources=((row.context.instrument.value, SourceKind.TRAINED_MODEL, provider.sha256),),
        )
        denied = evaluate_prediction(
            provider, row, changed, load_policy(), row.available_at, **args
        )
        assert denied.score is None and denied.audit.status == "NO_AUTHORITATIVE_PREDICTION"
        assert "Missing/extra model schema fields" in denied.audit.reason


def test_persistent_signed_packets_replay_both_sources_and_missing_models_without_effects():
    from tools.check_stage_b_predictions import prediction_proof

    report = prediction_proof()
    assert report["status"] == "PASS"
    assert report["core5_model_denials"] == 5
    assert report["signed_score_predictions"] == 2 and report["synthetic_reader_predictions"] == 1
    reports = report["source_reports"]
    assert len(reports["SIGNED_TEST_SCORE"]) == 2 and len(reports["TRAINED_MODEL"]) == 1
    assert reports["TRAINED_MODEL"][0]["instrument"] == "SYNTHETIC_6"
    assert all(row["role"] == "COMPUTE_AND_LOG_ONLY" for row in report["macro_observations"])
