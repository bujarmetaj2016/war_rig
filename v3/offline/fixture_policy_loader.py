"""Authenticate development fixture policies for EXT-06, never owner/live policy.

Allowed imports: stdlib, cryptography's Ed25519 verifier and unit 06 UTC primitives.
Untrusted bytes cross this boundary only after a domain-separated signature from
the caller's independently pinned public key. The signed manifest binds the exact
payload hash and resource limits. Outputs are immutable simulator identities and
validity metadata, not risk policy, entry eligibility, broker permits or model grants.
This pure loader performs no filesystem access, dynamic imports or deserialisation
of executable formats; path-safe on-disk intake remains a later Stage A slice.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from v3.offline.calendar_completion import ClockDenied, parse_utc, require_utc

type JsonValue = str | int | bool | None | list[JsonValue] | dict[str, JsonValue]

SIGNATURE_DOMAIN = b"WAR_RIG_DEV_FIXTURE_V1\x00"
_MANIFEST_FIELDS = {
    "schema_version",
    "domain",
    "payload_sha256",
    "max_bytes",
    "max_depth",
    "max_nodes",
}
_POLICY_FIELDS = {
    "policy_id",
    "run_id",
    "account_id",
    "instrument_ids",
    "valid_from",
    "valid_until",
}
_IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", re.ASCII)
_SHA256 = re.compile(r"[0-9a-f]{64}", re.ASCII)


class DenialReason(StrEnum):
    """Typed intake failures; a denial is never eligible or a neutral observation."""

    SIGNATURE = "SIGNATURE"
    RESOURCE_BOUND = "RESOURCE_BOUND"
    JSON = "JSON"
    SCHEMA = "SCHEMA"
    DOMAIN = "DOMAIN"
    HASH = "HASH"
    TIME = "TIME"


class FixtureDenied(ValueError):
    """Expose the exact denial reason to the caller for durable audit; no fallback."""

    def __init__(self, reason: DenialReason, detail: str) -> None:
        """Create an explicit denial from a reason and non-secret diagnostic text."""
        super().__init__(detail)
        self.reason = reason


@dataclass(frozen=True)
class ResourceBounds:
    """Signed payload limits; bootstrap maxima bound parsing, not market/risk policy."""

    max_bytes: int
    max_depth: int
    max_nodes: int

    def __post_init__(self) -> None:
        """Reject booleans, zero, negative and excessive parser limits."""
        for value, maximum in (
            (self.max_bytes, 1_048_576),
            (self.max_depth, 32),
            (self.max_nodes, 10_000),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise FixtureDenied(DenialReason.RESOURCE_BOUND, "Invalid fixture resource limit")


@dataclass(frozen=True)
class FixturePolicy:
    """Verified FIXTURE_ONLY identity/validity metadata; never monetary authority."""

    policy_id: str
    run_id: str
    account_id: str
    instrument_ids: tuple[str, ...]
    valid_from: datetime
    valid_until: datetime
    manifest_sha256: str
    payload_sha256: str
    signer_sha256: str
    bounds: ResourceBounds


@dataclass(frozen=True)
class AuthenticatedFixture:
    """Bounded authenticated bytes, not a parsed policy, permission or eligibility."""

    payload: bytes
    manifest_sha256: str
    payload_sha256: str
    signer_sha256: str
    bounds: ResourceBounds


def _reject_number(value: str) -> None:
    raise FixtureDenied(DenialReason.JSON, "Float and nonfinite JSON numbers are forbidden")


def _unique_pairs(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise FixtureDenied(DenialReason.JSON, "Duplicate JSON object key")
        result[key] = value
    return result


def _parse(raw: bytes, bounds: ResourceBounds) -> dict[str, JsonValue]:
    # Bound container nesting before the stdlib decoder can exhaust its call stack.
    depth = 0
    in_string = False
    escaped = False
    for character in raw:
        if in_string:
            if escaped:
                escaped = False
            elif character == 92:
                escaped = True
            elif character == 34:
                in_string = False
        elif character == 34:
            in_string = True
        elif character in (123, 91):
            depth += 1
            if depth > bounds.max_depth:
                raise FixtureDenied(DenialReason.RESOURCE_BOUND, "Fixture nesting limit exceeded")
        elif character in (125, 93):
            depth -= 1
    try:
        value: JsonValue = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_pairs,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        if isinstance(error, FixtureDenied):
            raise
        raise FixtureDenied(DenialReason.JSON, "Invalid UTF-8/JSON fixture") from error
    pending = [(value, 1)]
    nodes = 0
    while pending:
        node, depth = pending.pop()
        nodes += 1
        if nodes > bounds.max_nodes or depth > bounds.max_depth:
            raise FixtureDenied(DenialReason.RESOURCE_BOUND, "Fixture structural limit exceeded")
        if isinstance(node, dict):
            pending.extend((child, depth + 1) for child in node.values())
        elif isinstance(node, list):
            pending.extend((child, depth + 1) for child in node)
    if not isinstance(value, dict):
        raise FixtureDenied(DenialReason.SCHEMA, "Fixture must be a JSON object")
    return value


def _text(value: JsonValue) -> str:
    if not isinstance(value, str):
        raise FixtureDenied(DenialReason.SCHEMA, "Expected fixture string field")
    return value


def _integer(value: JsonValue) -> int:
    if type(value) is not int:
        raise FixtureDenied(DenialReason.SCHEMA, "Expected fixture integer field")
    return value


def _identity(value: JsonValue) -> str:
    result = _text(value)
    if not _IDENTITY.fullmatch(result):
        raise FixtureDenied(DenialReason.SCHEMA, "Invalid bounded fixture identity")
    return result


def authenticate_fixture(
    payload: bytes,
    manifest: bytes,
    signature: bytes,
    public_key: bytes,
) -> AuthenticatedFixture:
    """Verify domain-separated manifest, byte bounds and hash, or raise FixtureDenied.

    The independently pinned raw public key is not taken from the payload.
    Callers must still validate their exact payload schema before consuming it.
    This pure byte boundary grants neither owner-policy nor broker authority.
    """
    # A fixed bootstrap ceiling applies before parsing any untrusted signed limits.
    if len(manifest) > 4096:
        raise FixtureDenied(DenialReason.RESOURCE_BOUND, "Fixture manifest too large")
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature, SIGNATURE_DOMAIN + manifest
        )
    except (ValueError, InvalidSignature) as error:
        raise FixtureDenied(DenialReason.SIGNATURE, "Untrusted fixture signature/key") from error
    record = _parse(manifest, ResourceBounds(4096, 8, 32))
    if set(record) != _MANIFEST_FIELDS or _integer(record["schema_version"]) != 1:
        raise FixtureDenied(DenialReason.SCHEMA, "Unsupported fixture manifest schema")
    if record["domain"] != "FIXTURE_ONLY":
        raise FixtureDenied(DenialReason.DOMAIN, "Fixture signatures cannot load owner/live policy")
    expected_hash = _text(record["payload_sha256"])
    if not _SHA256.fullmatch(expected_hash):
        raise FixtureDenied(DenialReason.SCHEMA, "Invalid payload SHA-256")
    bounds = ResourceBounds(
        _integer(record["max_bytes"]),
        _integer(record["max_depth"]),
        _integer(record["max_nodes"]),
    )
    if len(payload) > bounds.max_bytes:
        raise FixtureDenied(DenialReason.RESOURCE_BOUND, "Fixture payload too large")
    payload_hash = hashlib.sha256(payload).hexdigest()
    if payload_hash != expected_hash:
        raise FixtureDenied(DenialReason.HASH, "Fixture payload hash mismatch")
    return AuthenticatedFixture(
        payload,
        hashlib.sha256(manifest).hexdigest(),
        payload_hash,
        hashlib.sha256(public_key).hexdigest(),
        bounds,
    )


def load_fixture_policy(
    payload: bytes,
    manifest: bytes,
    signature: bytes,
    public_key: bytes,
    as_of: datetime,
) -> FixturePolicy:
    """Return verified immutable identity metadata, or raise FixtureDenied; no effects.

    The half-open fixture interval [valid_from, valid_until) uses supplied UTC.
    Unknown fields, including monetary or broker permissions, are never accepted.
    """
    authenticated = authenticate_fixture(payload, manifest, signature, public_key)
    policy = _parse(authenticated.payload, authenticated.bounds)
    if set(policy) != _POLICY_FIELDS:
        raise FixtureDenied(DenialReason.SCHEMA, "Unexpected/missing fixture policy fields")
    policy_id, run_id, account_id = (
        _identity(policy[field]) for field in ("policy_id", "run_id", "account_id")
    )
    if not account_id.startswith("SIMULATED_"):
        raise FixtureDenied(DenialReason.DOMAIN, "Fixture account must be explicitly SIMULATED")
    instruments = policy["instrument_ids"]
    if not isinstance(instruments, list) or not instruments:
        raise FixtureDenied(DenialReason.SCHEMA, "Fixture instrument list is required")
    instrument_ids = tuple(_identity(item) for item in instruments)
    if len(instrument_ids) != len(set(instrument_ids)):
        raise FixtureDenied(DenialReason.SCHEMA, "Duplicate fixture instrument identity")
    try:
        valid_from = parse_utc(_text(policy["valid_from"]))
        valid_until = parse_utc(_text(policy["valid_until"]))
        require_utc(as_of)
    except ClockDenied as error:
        raise FixtureDenied(DenialReason.TIME, str(error)) from error
    if not valid_from <= as_of < valid_until:
        raise FixtureDenied(DenialReason.TIME, "Fixture policy is not valid at the replay instant")
    return FixturePolicy(
        policy_id,
        run_id,
        account_id,
        instrument_ids,
        valid_from,
        valid_until,
        authenticated.manifest_sha256,
        authenticated.payload_sha256,
        authenticated.signer_sha256,
        authenticated.bounds,
    )
