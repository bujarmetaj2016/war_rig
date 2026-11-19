import copy
import hashlib
import json
from dataclasses import replace
from decimal import Decimal

import pytest
from test_fixture_policy_loader import signed
from test_prediction_pipeline import load_feature, load_policy, prediction_plugins, run_body, signal

from v3.offline.model_intake import (
    ModelDenied,
    _array,
    _integer,
    _json,
    _numeric,
    _object,
    _parameter,
    _tree,
    load_synthetic_model,
    unavailable_core5,
)
from v3.offline.offline_scenario_runner import (
    SourceKind,
    canonical,
    grouped_report,
    load_run_manifest,
)


def artifact_bodies():
    # Hand-authored 3-node numeric tree. (x-10)/2 < 0 => -2, else +2.
    # Isotonic step: -2 -> .1; 0 -> .5; 2 -> .9. No learned/generated weights.
    tree = {
        "base_weights": [0, -2, 2],
        "categories": [],
        "categories_nodes": [],
        "categories_segments": [],
        "categories_sizes": [],
        "default_left": [1, 0, 0],
        "id": 0,
        "left_children": [1, -1, -1],
        "loss_changes": [0, 0, 0],
        "parents": [2147483647, 0, 0],
        "right_children": [2, -1, -1],
        "split_conditions": [0, -2, 2],
        "split_indices": [0, 0, 0],
        "split_type": [0, 0, 0],
        "sum_hessian": [2, 1, 1],
        "tree_param": {
            "num_deleted": "0",
            "num_feature": "1",
            "num_nodes": "3",
            "size_leaf_vector": "1",
        },
    }
    return {
        "schema.json": {"names": ["x"], "dtypes": ["DECIMAL"], "missing_rule": "TREE_DEFAULT"},
        "scaler.json": {"kind": "STANDARD", "columns": ["x"], "center": [10], "scale": [2]},
        "calibration.json": {
            "kind": "ISOTONIC_STEP",
            "x": [-2, 0, 2],
            "y": [Decimal("0.1"), Decimal("0.5"), Decimal("0.9")],
        },
        "model.json": {
            "version": [2, 0, 3],
            "learner": {
                "attributes": {},
                "feature_names": ["x"],
                "feature_types": ["float"],
                "gradient_booster": {
                    "name": "gbtree",
                    "model": {
                        "gbtree_model_param": {"num_parallel_tree": "1", "num_trees": "1"},
                        "iteration_indptr": [0, 1],
                        "tree_info": [0],
                        "trees": [tree],
                    },
                },
                "learner_model_param": {
                    "base_score": "0",
                    "num_class": "0",
                    "num_feature": "1",
                    "num_target": "1",
                },
                "objective": {
                    "name": "reg:squarederror",
                    "reg_loss_param": {"scale_pos_weight": "1"},
                },
            },
        },
    }


def native_bytes(value):
    # Test-only native numeric JSON emitter; constants above are independent of reader.
    return json.dumps(value, separators=(",", ":"), default=float).encode()


def model_body(bodies=None):
    bodies = artifact_bodies() if bodies is None else bodies
    files = tuple((name, native_bytes(value)) for name, value in bodies.items())
    formats = {
        "model.json": "AF-1",
        "scaler.json": "AF-2",
        "calibration.json": "AF-3",
        "schema.json": "AF-4",
    }
    return {
        "kind": "SYNTHETIC_READER_MECHANICS_ONLY_V1",
        "model_set_id": "HAND_TREE_1",
        "instrument_scope": "NONE_NOT_CORE5",
        "role": "SIGNAL_SCORE",
        "objective": "reg:squarederror",
        "files": [
            {
                "name": name,
                "format": formats[name],
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
            for name, raw in files
        ],
        "feature_schema_sha256": hashlib.sha256(dict(files)["schema.json"]).hexdigest(),
        "calibration_required": True,
        "state": "REGISTERED_IMMUTABLE",
        "promoted_for_live": False,
        "direction": "BULLISH",
        "lower_bound": "0.05",
        "tolerance": "0.000001",
        "tolerance_justification": (
            "Hand constants exact; 1e-6 only bounds numeric evaluation, not real-model parity."
        ),
        "golden_vectors": [
            {
                "raw_values": ["6"],
                "expected_raw": "-2",
                "expected_probability": "0.1",
                "derivation": "HAND_DERIVED: (6-10)/2=-2<0; left=-2; isotonic(-2)=0.1",
            },
            {
                "raw_values": ["14"],
                "expected_raw": "2",
                "expected_probability": "0.9",
                "derivation": "HAND_DERIVED: (14-10)/2=2>=0; right=2; isotonic(2)=0.9",
            },
            {
                "raw_values": [None],
                "expected_raw": "-2",
                "expected_probability": "0.1",
                "derivation": "HAND_DERIVED: missing follows default_left; leaf=-2; isotonic=0.1",
            },
        ],
    }, files


def load_model(body=None, files=None, *, metadata_updates=None, nested_updates=None):
    original, artifacts = model_body()
    value = original if body is None else copy.deepcopy(body)
    actual_files = artifacts if files is None else files
    hashes = {entry["name"]: entry["sha256"] for entry in value["files"]}
    value.update(
        scaler_sha256=hashes.get("scaler.json", "NONE_DECLARED"),
        calibration_sha256=hashes.get("calibration.json", "NONE_DECLARED"),
        training_snapshot_sha256_and_bar_range={
            "kind": "HAND_AUTHORED_SYNTHETIC_NO_TRAINING",
            "snapshot_sha256": "1" * 64,
            "bar_start": "2027-01-01T00:00:00Z",
            "bar_end": "2027-01-02T00:00:00Z",
        },
        fit_procedure_code_sha256="2" * 64,
        producer_environment_identity="SYNTHETIC_HAND_AUTHORED_NOT_TRAINED",
        authorisation={
            "owner_signature_ref": "DEVELOPMENT_FIXTURE_SIGNER_NOT_OWNER",
            "scope": "OFFLINE_SIMULATOR_ONLY",
            "runtime_profile": "G1_R",
            "valid_until": "2028-01-01T00:00:00Z",
        },
        registered_utc="2027-01-01T00:00:00Z",
    )
    conversion = {
        "kind": "IDENTITY_OF_HAND_AUTHORED_JSON_NOT_REAL_MODEL_CONVERSION",
        "before_sha256": hashes["model.json"],
        "after_sha256": hashes["model.json"],
        "converter_code_sha256": "2" * 64,
        "golden_reference_sha256": hashlib.sha256(canonical(value["golden_vectors"])).hexdigest(),
        "golden_vector_count": len(value["golden_vectors"]),
        "tolerance": value["tolerance"],
        "justification": value["tolerance_justification"],
    }
    value["conversion_record"] = conversion
    value["conversion_record_sha256"] = hashlib.sha256(canonical(conversion)).hexdigest()
    value.update(metadata_updates or {})
    if nested_updates is not None:
        field, updates = nested_updates
        value[field].update(updates)
    return load_synthetic_model(
        *signed(
            policy=value,
            manifest_updates={"max_bytes": 65536, "max_nodes": 1024, "max_depth": 12},
        ),
        actual_files,
        prediction_plugins(),
    )


def native_tree():
    return artifact_bodies()["model.json"]["learner"]["gradient_booster"]["model"]["trees"][0]


def test_full_path_hand_constants_signed_artifacts_determinism_and_source_separation():
    model = load_model()
    assert model.kind is SourceKind.TRAINED_MODEL
    row = load_feature(schema_sha256=model.schema_sha256)
    score = model.score(row)
    assert score.raw_score == -2 and score.probability == Decimal("0.1")
    assert score.kind is SourceKind.TRAINED_MODEL
    assert load_model().score(row) == score
    run = load_run_manifest(*signed(policy=run_body(row, score)))
    result = signal(row, score, run, load_policy())
    assert result.evidence_class == "OFFLINE_MODEL_BEHAVIOUR"
    assert result.labels == (
        "OFFLINE_SIMULATED_MODEL_BEHAVIOUR",
        "not verified forward or live trading performance",
    )
    assert dict(grouped_report((result,)))[SourceKind.SIGNED_TEST_SCORE] == ()
    assert not hasattr(result, "entry_permit")
    assert model.score(replace(row, values=(None,))).raw_score == -2
    assert model.score(replace(row, values=(Decimal(14),))).probability == Decimal("0.9")
    with pytest.raises(ModelDenied):
        model.score(
            replace(
                row, context=replace(row.context, instrument=type(row.context.instrument)("EURUSD"))
            )
        )
    with pytest.raises(ModelDenied):
        model.score(replace(row, schema_sha256="9" * 64))


@pytest.mark.parametrize("instrument", ["Gold", "XAUUSD", "GER40", "US500", "EURUSD", "GBPUSD"])
def test_each_real_core5_model_is_unavailable_without_any_fallback(instrument):
    result = unavailable_core5(instrument)
    assert result.status == "NO_AUTHORITATIVE_PREDICTION"
    assert result.reason == "CORE5_ARTIFACT_UNAVAILABLE_NOT_VERIFIED; NO_FALLBACK"
    assert not hasattr(result, "score")


def test_unknown_real_instrument_is_not_a_synthetic_fallback():
    with pytest.raises(ValueError):
        unavailable_core5("OTHER")


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "OWNER_APPROVED"),
        ("instrument_scope", "EURUSD"),
        ("role", "SHADOW_ONLY"),
        ("state", "VALIDATED"),
        ("state", "SERVING_AUTHORIZED_OFFLINE_ONLY"),
        ("promoted_for_live", True),
        ("direction", "NONE"),
        ("model_set_id", ""),
        ("calibration_required", 1),
        ("feature_schema_sha256", "9" * 64),
        ("tolerance", None),
        ("tolerance", "0"),
        ("tolerance", "1"),
        ("tolerance_justification", ""),
        ("golden_vectors", []),
    ],
)
def test_no_forged_owner_scope_state_or_unregistered_tolerance(field, value):
    body, files = model_body()
    body[field] = value
    with pytest.raises(ValueError):
        load_model(body, files)


@pytest.mark.parametrize("name", ["model.json", "scaler.json", "calibration.json", "schema.json"])
def test_tamper_missing_duplicate_extra_files_name_audit_failure(name):
    body, files = model_body()
    modified = tuple((key, raw + b" " if key == name else raw) for key, raw in files)
    with pytest.raises(ModelDenied, match=name):
        load_model(body, modified)
    with pytest.raises(ModelDenied, match=name):
        load_model(body, tuple((key, raw) for key, raw in files if key != name))
    with pytest.raises(ModelDenied, match="Duplicate"):
        load_model(body, files + (files[0],))
    with pytest.raises(ModelDenied, match="unlisted"):
        load_model(body, files + (("hidden.json", b"{}"),))


@pytest.mark.parametrize(
    "raw",
    [
        b"not-json",
        b"\xff",
        b'{"a":1,"a":2}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b"",
        b" " * 65537,
        b"[" * 17 + b"]" * 17,
    ],
)
def test_non_executable_strict_json_with_resource_bounds(raw):
    with pytest.raises(ModelDenied):
        _json(raw)


def test_json_escaped_strings_and_native_numeric_types():
    assert _json(b'{"x":"a\\\\b\\"c","y":0.5,"z":[1]}') == {
        "x": 'a\\b"c',
        "y": Decimal("0.5"),
        "z": [1],
    }
    assert _numeric(1) == 1 and _parameter("1E-2") == Decimal("0.01")
    assert _integer(1) == 1
    for action, value in (
        (_array, {}),
        (_integer, True),
        (_numeric, True),
        (_numeric, Decimal("NaN")),
        (_numeric, 10**31),
        (_parameter, True),
        (_parameter, "bad"),
        (_parameter, "NaN"),
        (_parameter, "1" * 41),
    ):
        with pytest.raises(ModelDenied):
            action(value)
    with pytest.raises(ModelDenied):
        _object({}, {"x"})


@pytest.mark.parametrize("change", ["format", "name", "duplicate", "required", "none"])
def test_formats_and_required_artifact_set_are_closed(change):
    body, files = model_body()
    if change == "format":
        body["files"][0]["format"] = "PICKLE"
    elif change == "name":
        body["files"][0]["name"] = "evil.py"
    elif change == "duplicate":
        body["files"].append(body["files"][0])
    else:
        body["files"] = [
            v
            for v in body["files"]
            if v["name"] != ("schema.json" if change == "required" else "calibration.json")
        ]
        files = tuple(
            v
            for v in files
            if v[0] != ("schema.json" if change == "required" else "calibration.json")
        )
    with pytest.raises(ModelDenied):
        load_model(body, files)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", 1),
        ("categories", [1]),
        ("split_type", [1, 0, 0]),
        ("left_children", [0, -1, -1]),
        ("right_children", [1, -1, -1]),
        ("parents", [2147483647, 1, 0]),
        ("split_indices", [1, 0, 0]),
        ("right_children", [2, 1, -1]),
        ("sum_hessian", [1]),
    ],
)
def test_tree_structure_categorical_cycle_shared_node_and_hidden_edges_reject(field, value):
    tree = native_tree()
    tree[field] = value
    with pytest.raises(ModelDenied):
        _tree(tree, 1, 0)


@pytest.mark.parametrize(
    "field,value",
    [
        ("names", ["x", "x"]),
        ("names", ["../x"]),
        ("names", []),
        ("dtypes", ["FLOAT"]),
        ("missing_rule", "FILL_ZERO"),
    ],
)
def test_ordered_schema_is_not_zero_filled_or_repaired(field, value):
    bodies = artifact_bodies()
    bodies["schema.json"][field] = value
    body, files = model_body(bodies)
    with pytest.raises(ModelDenied):
        load_model(body, files)


@pytest.mark.parametrize(
    "field,value", [("kind", "PICKLE"), ("columns", ["y"]), ("center", []), ("scale", [0])]
)
def test_scaler_shape_order_and_positive_scale(field, value):
    bodies = artifact_bodies()
    bodies["scaler.json"][field] = value
    body, files = model_body(bodies)
    with pytest.raises(ModelDenied):
        load_model(body, files)


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "FIT"),
        ("x", []),
        ("x", [-2, -2, 2]),
        ("y", [Decimal("0.9"), 0, 1]),
        ("y", [-1, 0, 1]),
        ("y", [0]),
    ],
)
def test_calibration_not_fitted_synthesized_or_reordered(field, value):
    bodies = artifact_bodies()
    bodies["calibration.json"][field] = value
    body, files = model_body(bodies)
    with pytest.raises(ModelDenied):
        load_model(body, files)


@pytest.mark.parametrize(
    "field,value",
    [
        ("raw_values", ["14"]),
        ("expected_raw", "0"),
        ("expected_probability", "0.9"),
        ("expected_probability", None),
        ("derivation", "GENERATED_BY_READER"),
    ],
)
def test_full_path_golden_constants_not_tree_only_or_generated(field, value):
    body, files = model_body()
    body["golden_vectors"][0][field] = value
    with pytest.raises(ModelDenied):
        load_model(body, files)


def test_missing_calibration_does_not_make_probability_by_climate():
    body, files = model_body()
    body["calibration_required"] = False
    body["lower_bound"] = None
    body["files"] = [v for v in body["files"] if v["name"] != "calibration.json"]
    files = tuple(v for v in files if v[0] != "calibration.json")
    for vector in body["golden_vectors"]:
        vector["expected_probability"] = None
    model = load_model(body, files)
    row = load_feature(schema_sha256=model.schema_sha256)
    score = model.score(row)
    assert score.probability is None
    run = load_run_manifest(*signed(policy=run_body(row, score)))
    with pytest.raises(ValueError, match="NO_AUTHORITATIVE"):
        signal(row, score, run, load_policy(), climate=Decimal(100))


def test_platt_and_logistic_numerics_are_pure_registered_constant_proofs():
    bodies = artifact_bodies()
    bodies["calibration.json"] = {"kind": "PLATT", "x": [0], "y": [0]}
    body, files = model_body(bodies)
    for vector in body["golden_vectors"]:
        vector["expected_probability"] = "0.5"
        vector["derivation"] += "; Platt(0*raw+0)=1/(1+exp(0))=0.5"
    model = load_model(body, files)
    row = load_feature(schema_sha256=model.schema_sha256)
    assert model.score(row).probability == Decimal("0.5")
    logistic = replace(model, objective="binary:logistic", base_score=Decimal("0.5"))
    assert abs(logistic.score(row).raw_score - Decimal("0.11920292202211755")) < Decimal("1e-16")
    assert (
        replace(model, calibration="PLATT", calibration_x=(Decimal(50),)).score(
            replace(row, values=(Decimal(10),))
        )
        is not None
    )
    with pytest.raises(ModelDenied, match="Calibration numeric"):
        replace(model, calibration_x=(Decimal(100),)).score(row)
    with pytest.raises(ModelDenied, match="Model numeric"):
        replace(model, base_score=Decimal(1000)).score(row)
    with pytest.raises(ModelDenied):
        replace(model, lower_bound=Decimal("0.9")).score(row)
    with pytest.raises(ModelDenied):
        replace(
            model,
            calibration="ISOTONIC_STEP",
            calibration_x=(Decimal(0),),
            calibration_y=(Decimal("0.5"),),
        ).score(row)


@pytest.mark.parametrize(
    "field,value",
    [
        ("names", ("y",)),
        ("dtypes", ("FLOAT",)),
        ("values", ()),
        ("values", (Decimal("NaN"),)),
    ],
)
def test_runtime_input_schema_mismatch_denies(field, value):
    model = load_model()
    row = load_feature(schema_sha256=model.schema_sha256)
    with pytest.raises(ModelDenied):
        model.score(replace(row, **{field: value}))
    with pytest.raises(ModelDenied):
        replace(model, missing="DENY").score(replace(row, values=(None,)))


def test_hidden_tree_nodes_and_unsupported_native_metadata_are_denied():
    tree = native_tree()
    for key in (
        "base_weights",
        "default_left",
        "left_children",
        "loss_changes",
        "parents",
        "right_children",
        "split_conditions",
        "split_indices",
        "split_type",
        "sum_hessian",
    ):
        tree[key].append(tree[key][-1])
    tree["tree_param"]["num_nodes"] = "4"
    with pytest.raises(ModelDenied, match="Unreachable"):
        _tree(tree, 1, 0)
    bodies = artifact_bodies()
    bodies["model.json"]["version"] = [3, 0, 0]
    body, files = model_body(bodies)
    with pytest.raises(ModelDenied, match="Unsupported native"):
        load_model(body, files)
    bodies = artifact_bodies()
    bodies["model.json"]["learner"]["objective"]["name"] = "binary:logistic"
    body, files = model_body(bodies)
    body["objective"] = "binary:logistic"
    with pytest.raises(ModelDenied, match="Invalid logistic"):
        load_model(body, files)


def test_explicit_no_scaler_uses_raw_features_not_an_inferred_scaler():
    bodies = artifact_bodies()
    del bodies["scaler.json"]
    body, files = model_body(bodies)
    body["golden_vectors"][0].update(
        expected_raw="2",
        expected_probability="0.9",
        derivation="HAND_DERIVED: no scaler; raw 6>=0; right=2; isotonic(2)=0.9",
    )
    model = load_model(body, files)
    assert model.score(load_feature(schema_sha256=model.schema_sha256)).raw_score == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("scaler_sha256", "9" * 64),
        ("calibration_sha256", "NONE_DECLARED"),
        ("producer_environment_identity", "REAL_TRAINING"),
        ("registered_utc", "2029-01-01T00:00:00Z"),
        ("conversion_record_sha256", "9" * 64),
        ("fit_procedure_code_sha256", True),
        ("fit_procedure_code_sha256", "g" * 64),
    ],
)
def test_manifest_provenance_fields_cannot_be_missing_or_fabricate_real_authority(field, value):
    with pytest.raises(ValueError):
        load_model(metadata_updates={field: value})


@pytest.mark.parametrize(
    "field,updates",
    [
        ("authorisation", {"owner_signature_ref": "OWNER_APPROVED"}),
        ("authorisation", {"scope": "LIVE"}),
        ("authorisation", {"runtime_profile": "LIVE"}),
        ("authorisation", {"valid_until": "2020-01-01T00:00:00Z"}),
        ("training_snapshot_sha256_and_bar_range", {"kind": "REAL_TRAINED_MODEL"}),
        ("training_snapshot_sha256_and_bar_range", {"bar_end": "2020-01-01T00:00:00Z"}),
        ("conversion_record", {"golden_reference_sha256": "9" * 64}),
    ],
)
def test_signed_metadata_nested_controls_are_constraints_not_owner_approval(field, updates):
    with pytest.raises(ValueError):
        load_model(nested_updates=(field, updates))


def test_declared_file_bytes_are_independent_of_correct_hashes():
    body, files = model_body()
    body["files"][0]["bytes"] += 1
    with pytest.raises(ModelDenied, match="schema.json"):
        load_model(body, files)
