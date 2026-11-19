"""MS-B sole non-executable model reader; synthetic mechanics, no Core-5 authority.

Artifacts arrive as explicitly named immutable bytes after signed fixture intake.
No directory discovery, deserialization library, executable format, model creation,
training or fallback exists here. Real owner registration remains unavailable.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from v3.offline.calendar_completion import parse_utc
from v3.offline.intent_identity import Digest
from v3.offline.offline_scenario_runner import (
    FeatureRow,
    PredictionDenied,
    SourceKind,
    SourceScore,
    canonical,
    signed_record,
)
from v3.offline.plugin_manifest import PluginManifest

type Native = None | bool | int | Decimal | str | list[Native] | dict[str, Native]
CORE5 = frozenset({"Gold", "XAUUSD", "GER40", "US500", "EURUSD", "GBPUSD"})
FORMATS = {
    "model.json": "AF-1",
    "scaler.json": "AF-2",
    "calibration.json": "AF-3",
    "schema.json": "AF-4",
}


class ModelDenied(PredictionDenied):
    """Explicit unauthoritative model failure, never an old/fixture/model fallback."""


def _pairs(pairs: list[tuple[str, Native]]) -> dict[str, Native]:
    result: dict[str, Native] = {}
    for key, value in pairs:
        if key in result:
            raise ModelDenied("Duplicate model JSON member")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ModelDenied("Nonfinite JSON model constant: " + value)


def _json(raw: bytes) -> Native:
    if not raw or len(raw) > 65536:
        raise ModelDenied("Model JSON byte bound")
    depth = 0
    string = escaped = False
    for byte in raw:
        if string:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                string = False
        elif byte == 34:
            string = True
        elif byte in (91, 123):
            depth += 1
            if depth > 16:
                raise ModelDenied("Model JSON depth bound")
        elif byte in (93, 125):
            depth -= 1
    try:
        value: Native = json.loads(
            raw, object_pairs_hook=_pairs, parse_float=Decimal, parse_constant=_constant
        )
    except (ValueError, UnicodeError) as error:
        raise ModelDenied("Invalid non-executable JSON") from error
    return value


def _object(value: Native, fields: set[str]) -> dict[str, Native]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ModelDenied("Missing/extra model schema fields")
    return value


def _array(value: Native) -> list[Native]:
    if not isinstance(value, list):
        raise ModelDenied("Expected model JSON array")
    return value


def _numeric(value: Native) -> Decimal:
    if type(value) is int and abs(value) <= 10**30:
        return Decimal(value)
    if isinstance(value, Decimal) and value.is_finite() and abs(value) <= Decimal("1e30"):
        return value
    raise ModelDenied("Finite bounded native JSON number required")


def _integer(value: Native) -> int:
    if type(value) is not int:
        raise ModelDenied("Exact model integer required")
    return value


def _parameter(value: Native) -> Decimal:
    if not isinstance(value, str) or len(value) > 40:
        raise ModelDenied("Native XGBoost parameter string required")
    try:
        result = Decimal(value)
    except ArithmeticError as error:
        raise ModelDenied("Invalid native XGBoost parameter") from error
    if not result.is_finite() or abs(result) > Decimal("1e30"):
        raise ModelDenied("Nonfinite/unbounded native XGBoost parameter")
    return result


def _digest(value: Native) -> str:
    if not isinstance(value, str):
        raise ModelDenied("Explicit model provenance digest required")
    try:
        return Digest(value).value
    except ValueError as error:
        raise ModelDenied("Invalid model provenance digest") from error


@dataclass(frozen=True)
class Tree:
    """Validated numeric binary gbtree; categorical/multitarget trees are not approved."""

    left: tuple[int, ...]
    right: tuple[int, ...]
    split: tuple[int, ...]
    default_left: tuple[int, ...]
    conditions: tuple[Decimal, ...]

    def evaluate(self, values: tuple[Decimal | None, ...]) -> Decimal:
        """Traverse only a prevalidated finite tree, honoring its explicit missing branch."""
        node = 0
        while self.left[node] != -1:
            value = values[self.split[node]]
            go_left = (
                bool(self.default_left[node]) if value is None else value < self.conditions[node]
            )
            node = self.left[node] if go_left else self.right[node]
        return self.conditions[node]


def _tree(value: Native, feature_count: int, index: int) -> Tree:
    record = _object(
        value,
        {
            "base_weights",
            "categories",
            "categories_nodes",
            "categories_segments",
            "categories_sizes",
            "default_left",
            "id",
            "left_children",
            "loss_changes",
            "parents",
            "right_children",
            "split_conditions",
            "split_indices",
            "split_type",
            "sum_hessian",
            "tree_param",
        },
    )
    params = _object(
        record["tree_param"], {"num_deleted", "num_feature", "num_nodes", "size_leaf_vector"}
    )
    left = tuple(_integer(v) for v in _array(record["left_children"]))
    right = tuple(_integer(v) for v in _array(record["right_children"]))
    splits = tuple(_integer(v) for v in _array(record["split_indices"]))
    defaults = tuple(_integer(v) for v in _array(record["default_left"]))
    conditions = tuple(_numeric(v) for v in _array(record["split_conditions"]))
    parents = tuple(_integer(v) for v in _array(record["parents"]))
    count = len(left)
    if (
        not 1 <= count <= 127
        or _integer(record["id"]) != index
        or params
        != {
            "num_deleted": "0",
            "num_feature": str(feature_count),
            "num_nodes": str(count),
            "size_leaf_vector": "1",
        }
        or any(
            record[name] != []
            for name in (
                "categories",
                "categories_nodes",
                "categories_segments",
                "categories_sizes",
            )
        )
        or any(_integer(v) != 0 for v in _array(record["split_type"]))
        or any(
            len(_array(record[name])) != count
            for name in (
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
            )
        )
        or any(v not in (0, 1) for v in defaults)
        or parents[0] != 2147483647
    ):
        raise ModelDenied("Unsupported or malformed native numeric tree")
    for name in ("base_weights", "loss_changes", "sum_hessian"):
        for value in _array(record[name]):
            _numeric(value)
    visited: set[int] = set()

    def visit(node: int, parent: int) -> None:
        if node < 0 or node >= count or node in visited or parents[node] != parent:
            raise ModelDenied("Invalid/cyclic/shared tree edge")
        visited.add(node)
        if left[node] == -1:
            if right[node] != -1:
                raise ModelDenied("Malformed leaf")
        else:
            if not 0 <= splits[node] < feature_count:
                raise ModelDenied("Feature split index outside schema")
            visit(left[node], node)
            visit(right[node], node)

    visit(0, 2147483647)
    if len(visited) != count:
        raise ModelDenied("Unreachable hidden tree nodes")
    return Tree(left, right, splits, defaults, conditions)


@dataclass(frozen=True)
class SyntheticModel:
    """Signed synthetic reader proof, explicitly NOT a VALIDATED/serving real model."""

    sha256: str
    build_sha256: str
    schema_sha256: str
    names: tuple[str, ...]
    missing: str
    centers: tuple[Decimal, ...]
    scales: tuple[Decimal, ...]
    trees: tuple[Tree, ...]
    objective: str
    base_score: Decimal
    calibration: str
    calibration_x: tuple[Decimal, ...]
    calibration_y: tuple[Decimal, ...]
    direction: str
    lower_bound: Decimal | None
    valid_until: datetime
    registered_at: datetime
    runtime_profile: str

    @property
    def kind(self) -> SourceKind:
        """Keep trained-model provenance on synthetic mechanics; never relabel a fixture table."""
        return SourceKind.TRAINED_MODEL

    def score(self, row: FeatureRow) -> SourceScore:
        """Evaluate the complete raw-row/scaler/tree/calibration path; no eligibility grant."""
        if (
            row.context.instrument.value != "SYNTHETIC_6"
            or row.schema_sha256 != self.schema_sha256
            or not self.registered_at <= row.available_at < self.valid_until
        ):
            raise ModelDenied("Synthetic proof cannot serve Core-5 or a different schema")
        return self._evaluate(row.names, row.dtypes, row.values, row.row_sha256)

    def _evaluate(
        self,
        names: tuple[str, ...],
        dtypes: tuple[str, ...],
        raw_values: tuple[Decimal | None, ...],
        row_sha256: str,
    ) -> SourceScore:
        if (
            names != self.names
            or dtypes != ("DECIMAL",) * len(self.names)
            or len(raw_values) != len(self.names)
            or any(value is None for value in raw_values)
            and self.missing == "DENY"
            or any(
                value is not None and (not value.is_finite() or abs(value) > Decimal("1e30"))
                for value in raw_values
            )
        ):
            raise ModelDenied("Feature schema order/name/count/dtype/missing mismatch")
        values = tuple(
            None if v is None else (v - center) / scale
            for v, center, scale in zip(raw_values, self.centers, self.scales, strict=True)
        )
        margin = self.base_score
        if self.objective == "binary:logistic":
            margin = (margin / (1 - margin)).ln()
        margin += sum(tree.evaluate(values) for tree in self.trees)
        if abs(margin) > 100:
            raise ModelDenied("Model numeric domain exceeded")
        raw = 1 / (1 + (-margin).exp()) if self.objective == "binary:logistic" else margin
        if self.calibration == "NONE_DECLARED":
            probability = None
        elif self.calibration == "PLATT":
            calibrated_margin = self.calibration_x[0] * raw + self.calibration_y[0]
            if abs(calibrated_margin) > 100:
                raise ModelDenied("Calibration numeric domain exceeded")
            probability = 1 / (1 + (-calibrated_margin).exp())
        else:
            eligible = [
                y for x, y in zip(self.calibration_x, self.calibration_y, strict=True) if raw >= x
            ]
            if not eligible:
                raise ModelDenied("ISOTONIC_STEP input outside registered support")
            probability = eligible[-1]
        if (
            not raw.is_finite()
            or (probability is not None and not 0 <= probability <= 1)
            or (
                self.lower_bound is not None
                and (probability is None or not 0 <= self.lower_bound <= probability)
            )
        ):
            raise ModelDenied("Nonfinite/out-of-domain model output; never repair or clip")
        return SourceScore(
            SourceKind.TRAINED_MODEL,
            self.sha256,
            row_sha256,
            self.direction,
            raw,
            probability,
            self.lower_bound,
            "SIGNED_SYNTHETIC_NOT_EMPIRICAL",
            self.build_sha256,
            self.valid_until,
            self.runtime_profile,
        )


def load_synthetic_model(
    payload: bytes,
    manifest: bytes,
    signature: bytes,
    key: bytes,
    artifacts: tuple[tuple[str, bytes], ...],
    plugins: PluginManifest,
) -> SyntheticModel:
    """Authenticate explicit synthetic artifacts and hand-derived full-path references.

    This proof is never an owner registration, original-library parity certificate,
    VALIDATED transition or Core-5 serving artifact. Those remain unavailable.
    """
    # The outer signature pins the exact AF-5 manifest bytes and every AF-1..4 file.
    plugins.require("MODEL_SCORE", "MODEL_SCORE_V1")
    outer = signed_record(payload, manifest, signature, key)
    native: Native = _json(canonical(outer))
    record = _object(
        native,
        {
            "kind",
            "model_set_id",
            "instrument_scope",
            "role",
            "objective",
            "files",
            "feature_schema_sha256",
            "calibration_required",
            "state",
            "promoted_for_live",
            "direction",
            "lower_bound",
            "golden_vectors",
            "tolerance",
            "tolerance_justification",
            "scaler_sha256",
            "calibration_sha256",
            "training_snapshot_sha256_and_bar_range",
            "fit_procedure_code_sha256",
            "producer_environment_identity",
            "conversion_record_sha256",
            "conversion_record",
            "authorisation",
            "registered_utc",
        },
    )
    if (
        record["kind"] != "SYNTHETIC_READER_MECHANICS_ONLY_V1"
        or record["instrument_scope"] != "NONE_NOT_CORE5"
        or record["role"] != "SIGNAL_SCORE"
        or record["state"] != "REGISTERED_IMMUTABLE"
        or record["promoted_for_live"] is not False
        or record["direction"] not in ("BULLISH", "BEARISH")
        or not isinstance(record["model_set_id"], str)
        or not record["model_set_id"]
        or not isinstance(record["calibration_required"], bool)
    ):
        raise ModelDenied("Synthetic-only scope/state/role; real owner registration unavailable")
    supplied = dict(artifacts)
    if len(supplied) != len(artifacts):
        raise ModelDenied("Duplicate model artifact names")
    listed: set[str] = set()
    parsed: dict[str, Native] = {}
    for entry in _array(record["files"]):
        file = _object(entry, {"name", "format", "sha256", "bytes"})
        name = file["name"]
        if (
            not isinstance(name, str)
            or name not in FORMATS
            or file["format"] != FORMATS[name]
            or name in listed
        ):
            raise ModelDenied("Executable/unapproved/duplicate model format")
        listed.add(name)
        raw = supplied.get(name)
        if (
            raw is None
            or len(raw) != _integer(file["bytes"])
            or hashlib.sha256(raw).hexdigest() != file["sha256"]
        ):
            raise ModelDenied("Missing/tampered model file: " + name)
        parsed[name] = _json(raw)
    if set(supplied) != listed or not {"model.json", "schema.json"} <= listed:
        raise ModelDenied("Missing or unlisted model artifact")
    for name, field in (
        ("scaler.json", "scaler_sha256"),
        ("calibration.json", "calibration_sha256"),
    ):
        actual = hashlib.sha256(supplied[name]).hexdigest() if name in supplied else "NONE_DECLARED"
        if record[field] != actual:
            raise ModelDenied("Declared scaler/calibration hash mismatch: " + name)
    auth = _object(
        record["authorisation"],
        {
            "owner_signature_ref",
            "scope",
            "valid_until",
            "runtime_profile",
        },
    )
    if (
        auth["owner_signature_ref"] != "DEVELOPMENT_FIXTURE_SIGNER_NOT_OWNER"
        or auth["scope"] != "OFFLINE_SIMULATOR_ONLY"
        or auth["runtime_profile"] != "G1_R"
        or record["producer_environment_identity"] != "SYNTHETIC_HAND_AUTHORED_NOT_TRAINED"
        or not isinstance(auth["valid_until"], str)
        or not isinstance(record["registered_utc"], str)
    ):
        raise ModelDenied("No real owner signature/authority is represented by synthetic mechanics")
    registered, expires = parse_utc(record["registered_utc"]), parse_utc(auth["valid_until"])
    if expires <= registered:
        raise ModelDenied("Finite model authorization validity required")
    training = _object(
        record["training_snapshot_sha256_and_bar_range"],
        {
            "kind",
            "snapshot_sha256",
            "bar_start",
            "bar_end",
        },
    )
    if (
        training["kind"] != "HAND_AUTHORED_SYNTHETIC_NO_TRAINING"
        or not _digest(training["snapshot_sha256"])
        or not isinstance(training["bar_start"], str)
        or not isinstance(training["bar_end"], str)
        or parse_utc(training["bar_start"]) >= parse_utc(training["bar_end"])
        or not _digest(record["fit_procedure_code_sha256"])
    ):
        raise ModelDenied("Explicit no-training synthetic provenance required")
    conversion = _object(
        record["conversion_record"],
        {
            "kind",
            "before_sha256",
            "after_sha256",
            "converter_code_sha256",
            "golden_reference_sha256",
            "golden_vector_count",
            "tolerance",
            "justification",
        },
    )
    if (
        conversion["kind"] != "IDENTITY_OF_HAND_AUTHORED_JSON_NOT_REAL_MODEL_CONVERSION"
        or conversion["before_sha256"] != hashlib.sha256(supplied["model.json"]).hexdigest()
        or conversion["after_sha256"] != conversion["before_sha256"]
        or conversion["converter_code_sha256"] != record["fit_procedure_code_sha256"]
        or conversion["golden_reference_sha256"]
        != hashlib.sha256(canonical(record["golden_vectors"])).hexdigest()
        or conversion["golden_vector_count"] != len(_array(record["golden_vectors"]))
        or conversion["tolerance"] != record["tolerance"]
        or conversion["justification"] != record["tolerance_justification"]
        or record["conversion_record_sha256"] != hashlib.sha256(canonical(conversion)).hexdigest()
    ):
        raise ModelDenied("Unregistered conversion/reference/tolerance provenance")
    schema = _object(parsed["schema.json"], {"names", "dtypes", "missing_rule"})
    names_raw = _array(schema["names"])
    if (
        not names_raw
        or len(names_raw) > 64
        or any(not isinstance(v, str) or not v.isidentifier() or not v.isascii() for v in names_raw)
        or len(set(str(v) for v in names_raw)) != len(names_raw)
        or schema["dtypes"] != ["DECIMAL"] * len(names_raw)
        or schema["missing_rule"] not in ("DENY", "TREE_DEFAULT")
        or hashlib.sha256(supplied["schema.json"]).hexdigest() != record["feature_schema_sha256"]
    ):
        raise ModelDenied("Invalid ordered feature schema/hash/missing rule")
    names = tuple(str(v) for v in names_raw)
    centers, scales = (Decimal(0),) * len(names), (Decimal(1),) * len(names)
    if "scaler.json" in parsed:
        scaler = _object(parsed["scaler.json"], {"kind", "columns", "center", "scale"})
        centers = tuple(_numeric(v) for v in _array(scaler["center"]))
        scales = tuple(_numeric(v) for v in _array(scaler["scale"]))
        if (
            scaler["kind"] not in ("ROBUST", "STANDARD")
            or scaler["columns"] != list(names)
            or len(centers) != len(names)
            or len(scales) != len(names)
            or any(v <= 0 for v in scales)
        ):
            raise ModelDenied("Scaler kind/columns/shape/scale mismatch")
    model = _object(parsed["model.json"], {"learner", "version"})
    learner = _object(
        model["learner"],
        {
            "attributes",
            "feature_names",
            "feature_types",
            "gradient_booster",
            "learner_model_param",
            "objective",
        },
    )
    params = _object(
        learner["learner_model_param"], {"base_score", "num_class", "num_feature", "num_target"}
    )
    objective = _object(learner["objective"], {"name", "reg_loss_param"})
    booster = _object(learner["gradient_booster"], {"name", "model"})
    forest = _object(
        booster["model"], {"gbtree_model_param", "iteration_indptr", "tree_info", "trees"}
    )
    raw_trees = _array(forest["trees"])
    if (
        model["version"] != [2, 0, 3]
        or learner["attributes"] != {}
        or learner["feature_names"] != list(names)
        or learner["feature_types"] != ["float"] * len(names)
        or booster["name"] != "gbtree"
        or not 1 <= len(raw_trees) <= 16
        or forest["gbtree_model_param"]
        != {"num_parallel_tree": "1", "num_trees": str(len(raw_trees))}
        or forest["tree_info"] != [0] * len(raw_trees)
        or forest["iteration_indptr"] != list(range(len(raw_trees) + 1))
        or params["num_class"] != "0"
        or params["num_feature"] != str(len(names))
        or params["num_target"] != "1"
        or objective["name"] not in ("binary:logistic", "reg:squarederror")
        or objective["name"] != record["objective"]
        or objective["reg_loss_param"] != {"scale_pos_weight": "1"}
    ):
        raise ModelDenied("Unsupported native gbtree/version/objective/feature metadata")
    base = _parameter(params["base_score"])
    if objective["name"] == "binary:logistic" and not 0 < base < 1:
        raise ModelDenied("Invalid logistic base score")
    calibration = "NONE_DECLARED"
    xs: tuple[Decimal, ...] = ()
    ys: tuple[Decimal, ...] = ()
    if "calibration.json" in parsed:
        cal = _object(parsed["calibration.json"], {"kind", "x", "y"})
        calibration = str(cal["kind"])
        xs, ys = (
            tuple(_numeric(v) for v in _array(cal["x"])),
            tuple(_numeric(v) for v in _array(cal["y"])),
        )
        if (
            calibration not in ("PLATT", "ISOTONIC_STEP")
            or not xs
            or len(xs) != len(ys)
            or calibration == "PLATT"
            and len(xs) != 1
            or calibration == "ISOTONIC_STEP"
            and (
                any(not 0 <= y <= 1 for y in ys)
                or any(a >= b for a, b in zip(xs, xs[1:], strict=False))
                or any(a > b for a, b in zip(ys, ys[1:], strict=False))
            )
        ):
            raise ModelDenied("Invalid calibration kind/parameters/monotonicity")
    if record["calibration_required"] and calibration == "NONE_DECLARED":
        raise ModelDenied("Required calibration absent")
    lower = None if record["lower_bound"] is None else _parameter(record["lower_bound"])
    result = SyntheticModel(
        hashlib.sha256(payload).hexdigest(),
        plugins.build_sha256.value,
        str(record["feature_schema_sha256"]),
        names,
        str(schema["missing_rule"]),
        centers,
        scales,
        tuple(_tree(v, len(names), i) for i, v in enumerate(raw_trees)),
        str(objective["name"]),
        base,
        calibration,
        xs,
        ys,
        str(record["direction"]),
        lower,
        expires,
        registered,
        str(auth["runtime_profile"]),
    )
    tolerance = _parameter(record["tolerance"])
    if (
        not 0 < tolerance <= Decimal("0.000001")
        or not isinstance(record["tolerance_justification"], str)
        or not record["tolerance_justification"]
    ):
        raise ModelDenied("Separately registered justified synthetic reference tolerance required")
    vectors = _array(record["golden_vectors"])
    if not vectors:
        raise ModelDenied("Full-path independent golden vectors required")
    # References are signed constants with raw input, not tree-only expected margins.
    for entry in vectors:
        vector = _object(
            entry, {"raw_values", "expected_raw", "expected_probability", "derivation"}
        )
        if not isinstance(vector["derivation"], str) or not vector["derivation"].startswith(
            "HAND_DERIVED:"
        ):
            raise ModelDenied("Independent hand-derived synthetic reference required")
        values = tuple(None if v is None else _parameter(v) for v in _array(vector["raw_values"]))
        # A feature-only witness cannot grant run/source/snapshot permission.
        score = _proof_score(result, values)
        expected_raw = _parameter(vector["expected_raw"])
        expected_probability = (
            None
            if vector["expected_probability"] is None
            else _parameter(vector["expected_probability"])
        )
        if (
            abs(score.raw_score - expected_raw) > tolerance
            or (score.probability is None) != (expected_probability is None)
            or (
                score.probability is not None
                and expected_probability is not None
                and abs(score.probability - expected_probability) > tolerance
            )
        ):
            raise ModelDenied("Full raw/scaler/tree/calibration synthetic golden mismatch")
    return result


def _proof_score(model: SyntheticModel, values: tuple[Decimal | None, ...]) -> SourceScore:
    """Validate full-path constants without manufacturing an authenticated feature row."""
    return model._evaluate(model.names, ("DECIMAL",) * len(model.names), values, "0" * 64)


@dataclass(frozen=True)
class ModelFailure:
    """Explicit auditable absence/failure; carries no score, fallback or entry authority."""

    instrument: str
    status: str
    reason: str


def unavailable_core5(instrument: str) -> ModelFailure:
    """Report each real Core-5 model honestly; never fit, substitute or synthesize one."""
    if instrument not in CORE5:
        raise PredictionDenied("Unknown real Core-5 instrument")
    return ModelFailure(
        instrument,
        "NO_AUTHORITATIVE_PREDICTION",
        "CORE5_ARTIFACT_UNAVAILABLE_NOT_VERIFIED; NO_FALLBACK",
    )
