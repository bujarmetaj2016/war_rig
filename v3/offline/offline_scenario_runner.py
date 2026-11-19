"""EXT-06 pure prediction contracts/composition; no model import, transport or authority.

Only signed fixture/schema, clock and identity primitives are dependencies. Source
selection is immutable per run. Feature lineage and evidence labels participate in
canonical prediction identity; canonical intent identity excludes artifact reruns.
"""

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from v3.offline.calendar_completion import (
    DataVerdict,
    ReplayClock,
    SignedSnapshot,
    assess_snapshot,
    require_utc,
)
from v3.offline.data_intake_schema import digest, object_fields, utc
from v3.offline.effective_policy import _strings
from v3.offline.fixture_policy_loader import (
    JsonValue,
    _identity,
    _parse,
    _text,
    authenticate_fixture,
)
from v3.offline.intent_identity import Digest, Identity, RunContext
from v3.offline.plugin_manifest import (
    BuildArtifact,
    PluginManifest,
    PluginRegistration,
    build_fingerprint,
)

PREDICTION_INTERFACES = {
    "SIGNED_SCORE_V1": ("v3.offline.offline_scenario_runner", "PURE_SIGNED_SCORE"),
    "MODEL_SCORE_V1": ("v3.offline.model_intake", "NONEXECUTABLE_JSON_READER"),
    "MACRO_OBSERVATION_V1": ("v3.offline.macro_features", "COMPUTE_AND_LOG_ONLY"),
}


class PredictionDenied(ValueError):
    """Explicit prediction validation failure; never a neutral score or fallback."""


class SourceKind(StrEnum):
    """The two and only two MS-B inference sources."""

    SIGNED_TEST_SCORE = "SIGNED_TEST_SCORE"
    TRAINED_MODEL = "TRAINED_MODEL"


def canonical(value: object) -> bytes:
    """Serialize immutable decision evidence deterministically; no I/O."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def fingerprint(value: object) -> str:
    """Return a content identifier, not a signature or authorization."""
    return hashlib.sha256(canonical(value)).hexdigest()


def number(value: JsonValue) -> Decimal:
    """Parse bounded signed exact decimal strings; no float/nonfinite/coercion."""
    text = _text(value)
    if not re.fullmatch(r"-?(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,18})?", text):
        raise PredictionDenied("Invalid exact numeric string")
    return Decimal(text)


def signed_record(
    payload: bytes, manifest: bytes, signature: bytes, key: bytes
) -> dict[str, JsonValue]:
    """Authenticate fixture bytes before closed consumer-specific schema parsing."""
    verified = authenticate_fixture(payload, manifest, signature, key)
    return _parse(verified.payload, verified.bounds)


def load_prediction_plugins(
    payload: bytes,
    manifest: bytes,
    signature: bytes,
    key: bytes,
    artifacts: tuple[BuildArtifact, ...],
) -> PluginManifest:
    """Use EXT-02 manifest types for a closed, build-bound MS-B interface registry.

    Stage A's accepted interface allowlist and signed artifacts stay unchanged.
    Neither manifest consumer performs discovery or dynamic importing.
    """
    record = object_fields(
        signed_record(payload, manifest, signature, key), {"kind", "build_sha256", "entries"}
    )
    build = build_fingerprint(artifacts)
    if record["kind"] != "FIXTURE_PREDICTION_PLUGINS_V1" or record["build_sha256"] != build.value:
        raise PredictionDenied("Unregistered prediction build")
    sources = {artifact.module: artifact for artifact in artifacts}
    entries: list[PluginRegistration] = []
    for raw in _nonempty_list(record["entries"]):
        entry = object_fields(
            raw,
            {
                "plugin_id",
                "interface_id",
                "version",
                "artifact_sha256",
                "schema_version",
                "capabilities",
                "source_import_path",
                "permitted_build_id",
                "dependencies",
            },
        )
        plugin_id, interface = _identity(entry["plugin_id"]), _identity(entry["interface_id"])
        path = _identity(entry["source_import_path"])
        dependencies = tuple(sorted(digest(v) for v in _list(entry["dependencies"])))
        if (
            interface not in PREDICTION_INTERFACES
            or PREDICTION_INTERFACES[interface][0] != path
            or set(_strings(entry["capabilities"])) != {PREDICTION_INTERFACES[interface][1]}
            or entry["version"] != "1.0.0"
            or entry["schema_version"] != "1.0.0"
            or entry["permitted_build_id"] != build.value
            or path not in sources
            or entry["artifact_sha256"] != sources[path].sha256.value
            or dependencies != tuple(sorted(sources[path].dependencies))
            or any(old.plugin_id.value == plugin_id for old in entries)
        ):
            raise PredictionDenied(
                "Unregistered prediction interface/capability/artifact/dependency"
            )
        entries.append(
            PluginRegistration(
                Identity(plugin_id), interface, "1.0.0", sources[path].sha256, path, dependencies
            )
        )
    if {entry.interface_id for entry in entries} != set(PREDICTION_INTERFACES):
        raise PredictionDenied(
            "Both prediction sources and observational macro interface are required"
        )
    return PluginManifest(tuple(entries), build, Digest(hashlib.sha256(payload).hexdigest()))


def _list(value: JsonValue) -> list[JsonValue]:
    if not isinstance(value, list):
        raise PredictionDenied("Explicit prediction list required")
    return value


def _nonempty_list(value: JsonValue) -> list[JsonValue]:
    result = _list(value)
    if not result:
        raise PredictionDenied("Nonempty prediction registry required")
    return result


@dataclass(frozen=True)
class FeatureRow:
    """Signed ordered features and immutable PIT source/bar/run lineage, not outcomes."""

    names: tuple[str, ...]
    dtypes: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    row_sha256: str
    snapshot_id: str
    snapshot_sha256: str
    schema_sha256: str
    event_id: str
    bar_start: datetime
    bar_end: datetime
    available_at: datetime
    expires_at: datetime
    context: RunContext


def load_feature_row(
    payload: bytes,
    manifest: bytes,
    signature: bytes,
    key: bytes,
    snapshot: SignedSnapshot,
    context: RunContext,
) -> FeatureRow:
    """Bind signed features to a completed signed snapshot and exact source/run identity."""
    item = object_fields(
        signed_record(payload, manifest, signature, key),
        {
            "kind",
            "names",
            "dtypes",
            "values",
            "row_sha256",
            "snapshot_sha256",
            "schema_sha256",
            "event_id",
            "available_at",
            "context_sha256",
        },
    )
    names = _strings(item["names"])
    raw_dtypes = item["dtypes"]
    if not isinstance(raw_dtypes, list):
        raise PredictionDenied("Declared feature dtypes required")
    dtypes = tuple(_identity(value) for value in raw_dtypes)
    raw = item["values"]
    if not isinstance(raw, list) or len(raw) != len(names) or len(dtypes) != len(names):
        raise PredictionDenied("Feature count/type mismatch")
    values = tuple(None if value is None else number(value) for value in raw)
    row_hash = fingerprint({"names": list(names), "dtypes": list(dtypes), "values": raw})
    max_age = snapshot.calendar.max_age_seconds
    if (
        item["kind"] != "SIGNED_FEATURE_ROW_V1"
        or max_age is None
        or item["event_id"] != snapshot.lineage.source_event_id
        or set(dtypes) != {"DECIMAL"}
        or digest(item["row_sha256"]) != row_hash
        or row_hash != snapshot.lineage.feature_row_sha256
        or digest(item["snapshot_sha256"]) != snapshot.lineage.snapshot_sha256
        or digest(item["schema_sha256"]) != context.feature_schema_sha256.value
        or snapshot.binding.feature_schema_sha256 != context.feature_schema_sha256.value
        or context.source_sha256.value != snapshot.lineage.snapshot_sha256
        or item["context_sha256"] != context.sha256
        or snapshot.binding.instrument_id != context.instrument.value
        or snapshot.binding.run_id != context.run.value
        or snapshot.binding.account_id != context.account.value
        or snapshot.binding.policy_sha256 != context.policy_sha256.value
        or context.clock_id.value != snapshot.clock.source_clock_id
        or not context.valid_from <= snapshot.clock.at < context.valid_until
        or not snapshot.lineage.bar_end <= utc(item["available_at"]) <= snapshot.clock.at
        or assess_snapshot(snapshot, snapshot.binding, ReplayClock(snapshot.clock.at)).verdict
        is not DataVerdict.COMPLETED_FIXTURE_ONLY
    ):
        raise PredictionDenied("Unproven feature lineage or completed data")
    return FeatureRow(
        names,
        dtypes,
        values,
        row_hash,
        snapshot.lineage.snapshot_id,
        snapshot.lineage.snapshot_sha256,
        digest(item["schema_sha256"]),
        _identity(item["event_id"]),
        snapshot.lineage.bar_start,
        snapshot.lineage.bar_end,
        utc(item["available_at"]),
        min(
            context.valid_until,
            snapshot.calendar.session_close,
            snapshot.lineage.bar_end + timedelta(seconds=max_age),
        ),
        context,
    )


@dataclass(frozen=True)
class RunManifest:
    """Signed immutable source declaration; cannot substitute after failure or reload."""

    run_id: str
    account_id: str
    runtime_profile: str
    valid_from: datetime
    valid_until: datetime
    sources: tuple[tuple[str, SourceKind, str], ...]
    sha256: str


def load_run_manifest(payload: bytes, manifest: bytes, signature: bytes, key: bytes) -> RunManifest:
    """Verify source kinds, distinct instrument bindings and finite UTC validity."""
    item = object_fields(
        signed_record(payload, manifest, signature, key),
        {
            "kind",
            "run_id",
            "account_id",
            "runtime_profile",
            "valid_from",
            "valid_until",
            "sources",
        },
    )
    raw = item["sources"]
    if item["kind"] != "FIXTURE_PREDICTION_RUN_V1" or not isinstance(raw, list) or not raw:
        raise PredictionDenied("Explicit signed run sources required")
    entries: list[tuple[str, SourceKind, str]] = []
    for source in raw:
        entry = object_fields(source, {"instrument", "source_kind", "fingerprint"})
        entries.append(
            (
                _identity(entry["instrument"]),
                SourceKind(_text(entry["source_kind"])),
                digest(entry["fingerprint"]),
            )
        )
    if len({entry[0] for entry in entries}) != len(entries) or utc(item["valid_until"]) <= utc(
        item["valid_from"]
    ):
        raise PredictionDenied("Conflicting sources or invalid run validity")
    account = _identity(item["account_id"])
    if not account.startswith("SIMULATED_"):
        raise PredictionDenied("Only simulated prediction runs are available")
    return RunManifest(
        _identity(item["run_id"]),
        account,
        _identity(item["runtime_profile"]),
        utc(item["valid_from"]),
        utc(item["valid_until"]),
        tuple(entries),
        hashlib.sha256(payload).hexdigest(),
    )


@dataclass(frozen=True)
class SourceScore:
    """Source-produced score, side-specific probability and bound, without a grade/risk grant."""

    kind: SourceKind
    source_fingerprint: str
    feature_row_sha256: str
    direction: str
    raw_score: Decimal
    probability: Decimal | None
    lower_bound: Decimal | None
    calibration_status: str
    producer_build_sha256: str
    valid_until: datetime
    runtime_profile: str


@dataclass(frozen=True)
class ScoreTable:
    """Signed synthetic scores; cannot carry a trained-model evidence label."""

    rows: tuple[tuple[str, str, Decimal, Decimal, Decimal], ...]
    sha256: str
    build_sha256: str

    @property
    def kind(self) -> SourceKind:
        """Fix the evidence source in the registered producer, never in the caller."""
        return SourceKind.SIGNED_TEST_SCORE

    def score(self, row: FeatureRow) -> SourceScore:
        """Resolve an exact signed feature row; no model files, randomness or I/O."""
        for feature, direction, raw, probability, lower in self.rows:
            if feature == row.row_sha256:
                return SourceScore(
                    SourceKind.SIGNED_TEST_SCORE,
                    self.sha256,
                    feature,
                    direction,
                    raw,
                    probability,
                    lower,
                    "SIGNED_SYNTHETIC_NOT_EMPIRICAL",
                    self.build_sha256,
                    row.context.valid_until,
                    "G1_R",
                )
        raise PredictionDenied("NOT_PROVEN: unregistered feature/score row")


def load_score_table(
    payload: bytes,
    manifest: bytes,
    signature: bytes,
    key: bytes,
    plugins: PluginManifest,
) -> ScoreTable:
    """Load exact signed test scores, never execute scoring code or infer a model label."""
    plugins.require("SIGNED_SCORE", "SIGNED_SCORE_V1")
    item = object_fields(signed_record(payload, manifest, signature, key), {"kind", "rows"})
    raw = item["rows"]
    if item["kind"] != "SIGNED_TEST_SCORE_V1" or not isinstance(raw, list) or not raw:
        raise PredictionDenied("NOT_PROVEN: invalid signed score table")
    entries: list[tuple[str, str, Decimal, Decimal, Decimal]] = []
    for value in raw:
        entry = object_fields(
            value, {"feature_row_sha256", "direction", "raw", "probability", "lower_bound"}
        )
        feature, direction = digest(entry["feature_row_sha256"]), _identity(entry["direction"])
        score, probability, lower = (
            number(entry["raw"]),
            number(entry["probability"]),
            number(entry["lower_bound"]),
        )
        if (
            direction not in {"BULLISH", "BEARISH"}
            or not 0 <= lower <= probability <= 1
            or any(old[0] == feature for old in entries)
        ):
            raise PredictionDenied("NOT_PROVEN: invalid score domain or duplicate row")
        entries.append((feature, direction, score, probability, lower))
    return ScoreTable(
        tuple(entries), hashlib.sha256(payload).hexdigest(), plugins.build_sha256.value
    )


@dataclass(frozen=True)
class ConfidencePolicy:
    """Explicit signed synthetic grades/tiers and caps; not a monetary permit."""

    bands: tuple[tuple[str, Decimal, Decimal], ...]
    cap: Decimal
    sha256: str


def load_confidence_policy(
    payload: bytes, manifest: bytes, signature: bytes, key: bytes
) -> ConfidencePolicy:
    """Require ordered complete A/B/C/D thresholds and monotonic bounded base tiers."""
    item = object_fields(signed_record(payload, manifest, signature, key), {"kind", "bands", "cap"})
    raw = item["bands"]
    if item["kind"] != "FIXTURE_CONFIDENCE_POLICY_V1" or not isinstance(raw, list):
        raise PredictionDenied("Unselected confidence policy")
    bands = []
    for value in raw:
        entry = object_fields(value, {"grade", "threshold", "tier"})
        bands.append((_identity(entry["grade"]), number(entry["threshold"]), number(entry["tier"])))
    cap = number(item["cap"])
    if (
        tuple(band[0] for band in bands) != ("A", "B", "C", "D")
        or not 0 <= cap <= 1
        or bands[-1][1] != 0
        or any(not 0 <= threshold <= 1 or not 0 <= tier <= 1 for _, threshold, tier in bands)
        or any(
            left[1] <= right[1] or left[2] < right[2]
            for left, right in zip(bands, bands[1:], strict=False)
        )
    ):
        raise PredictionDenied("Invalid grade bands or tier monotonicity")
    return ConfidencePolicy(tuple(bands), cap, hashlib.sha256(payload).hexdigest())


@dataclass(frozen=True)
class SignalScore:
    """MS-B common immutable prediction; labels/lineage fixed by the validated source."""

    prediction_id: str
    intent_id: str
    instrument: str
    context_sha256: str
    created_at: datetime
    source_kind: SourceKind
    source_fingerprint: str
    evidence_class: str
    labels: tuple[str, ...]
    feature_row_sha256: str
    snapshot_id: str
    snapshot_sha256: str
    feature_schema_sha256: str
    bar_start: datetime
    bar_end: datetime
    direction: str
    raw_score: Decimal
    calibrated_probability: Decimal
    calibration_status: str
    lower_bound: Decimal
    data_quality: Decimal
    climate: Decimal | None
    confidence: Decimal
    grade: str
    base_tier: Decimal
    conservative_tier: Decimal
    policy_sha256: str
    run_manifest_sha256: str

    @property
    def encoded(self) -> bytes:
        """Return deterministic report bytes without changing source evidence labels."""
        return canonical(asdict(self))


def make_signal(
    score: SourceScore,
    row: FeatureRow,
    run: RunManifest,
    policy: ConfidencePolicy,
    at: datetime,
    *,
    runtime_profile: str,
    data_quality: Decimal,
    climate: Decimal | None,
    conservative_cap: Decimal,
) -> SignalScore:
    """Validate immutable source selection and conservative confidence caps; no entry or sizing."""
    require_utc(at)
    if (
        (row.context.instrument.value, score.kind, score.source_fingerprint) not in run.sources
        or run.run_id != row.context.run.value
        or run.account_id != row.context.account.value
        or run.runtime_profile != runtime_profile
        or not row.context.valid_from <= at < row.context.valid_until
        or not run.valid_from <= row.available_at <= at < run.valid_until
        or at > row.expires_at
        or policy.sha256 != row.context.policy_sha256.value
        or score.feature_row_sha256 != row.row_sha256
        or score.producer_build_sha256 != row.context.build_sha256.value
        or at >= score.valid_until
        or score.runtime_profile != runtime_profile
        or score.direction not in {"BULLISH", "BEARISH"}
        or score.calibration_status
        not in {"SIGNED_SYNTHETIC_NOT_EMPIRICAL", "VERIFIED_ARTIFACT_PARAMETERS"}
        or score.probability is None
        or score.lower_bound is None
        or not score.raw_score.is_finite()
        or not score.probability.is_finite()
        or not score.lower_bound.is_finite()
        or not 0 <= score.lower_bound <= score.probability <= 1
        or not data_quality.is_finite()
        or not 0 <= data_quality <= 1
        or not conservative_cap.is_finite()
        or not 0 <= conservative_cap <= 1
        or (climate is not None and (not climate.is_finite() or not 0 <= climate <= 100))
    ):
        raise PredictionDenied(
            "NO_AUTHORITATIVE_PREDICTION: source, calibration, scope or domain mismatch"
        )
    confidence = score.lower_bound
    grade, _, tier = next(band for band in policy.bands if confidence >= band[1])
    model = score.kind is SourceKind.TRAINED_MODEL
    labels = (
        ("OFFLINE_SIMULATED_MODEL_BEHAVIOUR", "not verified forward or live trading performance")
        if model
        else ("NOT_PERFORMANCE_EVIDENCE", "NOT_A_MODEL_PREDICTION")
    )
    intent = fingerprint(
        (
            "FIXTURE_SOURCE_EVENT_INTENT_V1",
            row.context.account.value,
            row.context.market.value,
            row.context.instrument.value,
            row.event_id,
            score.direction,
        )
    )
    identity = fingerprint(
        (
            asdict(score),
            row.snapshot_sha256,
            row.schema_sha256,
            row.context.sha256,
            run.sha256,
            policy.sha256,
            at,
            data_quality,
            climate,
            conservative_cap,
        )
    )
    return SignalScore(
        identity,
        intent,
        row.context.instrument.value,
        row.context.sha256,
        at,
        score.kind,
        score.source_fingerprint,
        "OFFLINE_MODEL_BEHAVIOUR" if model else "PIPELINE_VALIDATION_ONLY",
        labels,
        row.row_sha256,
        row.snapshot_id,
        row.snapshot_sha256,
        row.schema_sha256,
        row.bar_start,
        row.bar_end,
        score.direction,
        score.raw_score,
        score.probability,
        score.calibration_status,
        score.lower_bound,
        data_quality,
        climate,
        confidence,
        grade,
        tier,
        min(tier, policy.cap, data_quality, conservative_cap),
        policy.sha256,
        run.sha256,
    )


def grouped_report(
    scores: tuple[SignalScore, ...],
) -> tuple[tuple[SourceKind, tuple[bytes, ...]], ...]:
    """Keep source-kind reports separate; never pool fixture and model figures."""
    return tuple(
        (kind, tuple(score.encoded for score in scores if score.source_kind is kind))
        for kind in SourceKind
    )


@dataclass(frozen=True)
class ScoreProvider:
    """Injected registered source interface; orchestration cannot import a model reader."""

    kind: SourceKind
    sha256: str
    score: Callable[[FeatureRow], SourceScore]


@dataclass(frozen=True)
class PredictionAudit:
    """Pre-outcome inference witness; later durable-ledger persistence is a separate stage."""

    run_manifest_sha256: str
    event_id: str
    source_kind: SourceKind | None
    source_fingerprint: str | None
    status: str
    reason: str
    prediction_id: str | None


@dataclass(frozen=True)
class PredictionResult:
    """A denial never contains an authoritative-looking score or substitute."""

    score: SignalScore | None
    audit: PredictionAudit


def evaluate_prediction(
    provider: ScoreProvider | None,
    row: FeatureRow,
    run: RunManifest,
    policy: ConfidencePolicy,
    at: datetime,
    *,
    runtime_profile: str,
    data_quality: Decimal,
    climate: Decimal | None,
    conservative_cap: Decimal,
) -> PredictionResult:
    """Call only the run-declared producer once; record deterministic success or denial."""
    declarations = tuple(
        source for source in run.sources if source[0] == row.context.instrument.value
    )
    declared = declarations[0] if len(declarations) == 1 else None
    kind, source_hash = (None, None) if declared is None else (declared[1], declared[2])
    try:
        if provider is None or declared is None:
            raise PredictionDenied("Declared source unavailable; NO_FALLBACK")
        if provider.kind != kind or provider.sha256 != source_hash:
            raise PredictionDenied("Source replacement/relabel denied; NO_FALLBACK")
        source = provider.score(row)
        if source.kind != provider.kind or source.source_fingerprint != provider.sha256:
            raise PredictionDenied("Producer source relabel/fingerprint mismatch")
        result = make_signal(
            source,
            row,
            run,
            policy,
            at,
            runtime_profile=runtime_profile,
            data_quality=data_quality,
            climate=climate,
            conservative_cap=conservative_cap,
        )
    except PredictionDenied as error:
        status = (
            "NOT_PROVEN" if kind is SourceKind.SIGNED_TEST_SCORE else "NO_AUTHORITATIVE_PREDICTION"
        )
        return PredictionResult(
            None,
            PredictionAudit(run.sha256, row.event_id, kind, source_hash, status, str(error), None),
        )
    return PredictionResult(
        result,
        PredictionAudit(
            run.sha256,
            row.event_id,
            kind,
            source_hash,
            result.evidence_class,
            "EXACT_DECLARED_SOURCE_ONLY",
            result.prediction_id,
        ),
    )


class PredictionRecordKind(StrEnum):
    """Mandatory lineage surfaces; this contract does not create simulated lifecycle records."""

    ORDER = "ORDER"
    POSITION = "POSITION"
    EVENT = "EVENT"
    OUTCOME = "OUTCOME"
    AUDIT = "AUDIT"


@dataclass(frozen=True)
class PredictionReference:
    """Typed downstream lineage, not an order, outcome, broker authority or ledger."""

    record_kind: PredictionRecordKind
    record_id: str
    record_sha256: str
    prediction_id: str
    intent_id: str
    source_kind: SourceKind
    source_fingerprint: str
    policy_sha256: str
    run_manifest_sha256: str


def prediction_reference(
    score: SignalScore,
    kind: PredictionRecordKind,
    record_id: str,
    record_sha256: str,
) -> PredictionReference:
    """Require a linked prediction on every later record; never reconstruct from an outcome."""
    return PredictionReference(
        kind,
        Identity(record_id).value,
        Digest(record_sha256).value,
        score.prediction_id,
        score.intent_id,
        score.source_kind,
        score.source_fingerprint,
        score.policy_sha256,
        score.run_manifest_sha256,
    )
