"""Strict EXT-10 signed synthetic snapshot schema, not a market-data ingestion service.

Only the fixture verifier and pure calendar types are imported. Authenticated bytes
must match this closed schema; identifiers, exact prices, UTC and binary TZif bounds
are checked before typed immutable records cross the completion boundary.
"""

import base64
import re
from datetime import datetime
from decimal import Decimal

from v3.offline.calendar_completion import (
    CalendarPolicy,
    ClockDenied,
    CompletedBar,
    FeatureLineage,
    InputQuality,
    SignedSnapshot,
    SnapshotBinding,
    VerifiedEventClock,
    parse_utc,
)
from v3.offline.fixture_policy_loader import (
    DenialReason,
    FixtureDenied,
    JsonValue,
    _identity,
    _integer,
    _parse,
    _text,
    authenticate_fixture,
)

_FIELDS = {
    "kind",
    "source_quality",
    "run_id",
    "account_id",
    "instrument_id",
    "source_id",
    "source_version",
    "policy_sha256",
    "feature_schema_sha256",
    "price_unit",
    "currency",
    "timezone",
    "timezone_version",
    "timezone_tzif_base64",
    "session_open",
    "session_close",
    "expected_close",
    "expected_local_close",
    "interval_seconds",
    "max_age_seconds",
    "max_publication_delay_seconds",
    "bar",
    "clock",
    "snapshot_id",
    "source_event_id",
    "feature_row_sha256",
    "bar_start",
    "bar_end",
}
_BAR_FIELDS = {
    "start",
    "end",
    "price",
    "complete",
    "published_at",
    "observed_at",
    "vintage_available_at",
    "revision_available_at",
}
_CLOCK_FIELDS = {
    "at",
    "monotonic_ns",
    "domain",
    "source_clock_id",
    "skew_bound_microseconds",
    "evidence_sha256",
}


def object_fields(value: JsonValue, fields: set[str]) -> dict[str, JsonValue]:
    """Require one exact JSON-object shape or raise a typed schema denial."""
    if not isinstance(value, dict) or set(value) != fields:
        raise FixtureDenied(DenialReason.SCHEMA, "Missing, extra or wrong-typed schema fields")
    return value


def digest(value: JsonValue) -> str:
    """Validate a lowercase SHA-256 reference, never treat it as a signature."""
    text = _text(value)
    if not re.fullmatch(r"[a-f0-9]{64}", text, flags=re.ASCII):
        raise FixtureDenied(DenialReason.SCHEMA, "Invalid SHA-256 reference")
    return text


def utc(value: JsonValue) -> datetime:
    """Require supplied UTC evidence; translate clock failure into an intake denial."""
    try:
        return parse_utc(_text(value))
    except ClockDenied as error:
        raise FixtureDenied(DenialReason.TIME, str(error)) from error


def optional_integer(value: JsonValue) -> int | None:
    """Keep an unselected threshold absent; never replace it with a freshness default."""
    return None if value is None else _integer(value)


def exact_price(value: JsonValue) -> Decimal | None:
    """Parse a positive fixed-point string; an explicitly absent price stays absent."""
    if value is None:
        return None
    text = _text(value)
    if not re.fullmatch(r"(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,12})?", text):
        raise FixtureDenied(DenialReason.SCHEMA, "Expected bounded exact price string")
    price = Decimal(text)
    if price <= 0:
        raise FixtureDenied(DenialReason.SCHEMA, "Price must be positive")
    return price


def _bar(value: JsonValue) -> CompletedBar | None:
    if value is None:
        return None
    fields = object_fields(value, _BAR_FIELDS)
    if type(fields["complete"]) is not bool:
        raise FixtureDenied(DenialReason.SCHEMA, "Completion must be an explicit boolean")
    return CompletedBar(
        utc(fields["start"]),
        utc(fields["end"]),
        exact_price(fields["price"]),
        fields["complete"],
        utc(fields["published_at"]),
        utc(fields["observed_at"]),
        utc(fields["vintage_available_at"]),
        utc(fields["revision_available_at"]),
    )


def load_snapshot_fixture(
    payload: bytes, manifest: bytes, signature: bytes, public_key: bytes
) -> SignedSnapshot:
    """Authenticate and decode a synthetic snapshot or raise FixtureDenied; no I/O."""
    authenticated = authenticate_fixture(payload, manifest, signature, public_key)
    record = object_fields(_parse(authenticated.payload, authenticated.bounds), _FIELDS)
    if record["kind"] != "SYNTHETIC_COMPLETED_SNAPSHOT":
        raise FixtureDenied(DenialReason.DOMAIN, "Only synthetic completed snapshots are admitted")
    try:
        quality = InputQuality(_text(record["source_quality"]))
    except ValueError as error:
        raise FixtureDenied(DenialReason.SCHEMA, "Unknown fixture source quality") from error
    account = _identity(record["account_id"])
    if not account.startswith("SIMULATED_"):
        raise FixtureDenied(DenialReason.DOMAIN, "Real accounts are not snapshot fixtures")
    currency = _text(record["currency"])
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise FixtureDenied(DenialReason.SCHEMA, "Invalid explicit currency")
    try:
        tzif = base64.b64decode(_text(record["timezone_tzif_base64"]), validate=True)
    except ValueError as error:
        raise FixtureDenied(DenialReason.SCHEMA, "Invalid calendar encoding") from error
    if not 44 <= len(tzif) <= 16_384 or not tzif.startswith(b"TZif"):
        raise FixtureDenied(DenialReason.SCHEMA, "Invalid bounded TZif calendar")
    clock = object_fields(record["clock"], _CLOCK_FIELDS)
    return SignedSnapshot(
        SnapshotBinding(
            _identity(record["run_id"]),
            account,
            _identity(record["instrument_id"]),
            _identity(record["source_id"]),
            _identity(record["source_version"]),
            digest(record["policy_sha256"]),
            digest(record["feature_schema_sha256"]),
            _identity(record["price_unit"]),
            currency,
            _text(record["timezone"]),
            _identity(record["timezone_version"]),
        ),
        CalendarPolicy(
            tzif,
            utc(record["session_open"]),
            utc(record["session_close"]),
            utc(record["expected_close"]),
            _text(record["expected_local_close"]),
            _integer(record["interval_seconds"]),
            optional_integer(record["max_age_seconds"]),
            optional_integer(record["max_publication_delay_seconds"]),
        ),
        VerifiedEventClock(
            utc(clock["at"]),
            _integer(clock["monotonic_ns"]),
            _identity(clock["domain"]),
            _identity(clock["source_clock_id"]),
            _integer(clock["skew_bound_microseconds"]),
            digest(clock["evidence_sha256"]),
        ),
        FeatureLineage(
            _identity(record["snapshot_id"]),
            _identity(record["source_event_id"]),
            authenticated.payload_sha256,
            digest(record["feature_row_sha256"]),
            digest(record["feature_schema_sha256"]),
            utc(record["bar_start"]),
            utc(record["bar_end"]),
        ),
        _bar(record["bar"]),
        authenticated.manifest_sha256,
        authenticated.signer_sha256,
        quality,
    )
