"""Authenticate development fixture policies for EXT-06, never owner/live policy.

Allowed imports: stdlib, cryptography's Ed25519 verifier and unit 06 UTC primitives.
Untrusted bytes cross this boundary only after a domain-separated signature from
the caller's independently pinned public key. The signed manifest binds the exact
payload hash and resource limits. Outputs are immutable simulator identities and
validity metadata, not risk policy, entry eligibility, broker permits or model grants.
Byte verification stays pure. The separate on-disk function accepts a signed
intake policy and can read only the fixed three-file layout under repo fixtures,
using descriptor-relative, no-follow, bounded regular-file operations.
"""

import hashlib
import json
import os
import re
import stat
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from v3.offline.calendar_completion import ClockDenied, parse_utc, require_utc
from v3.offline.intent_identity import Digest, RunId, SimulatedAccountId

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
    FILESYSTEM = "FILESYSTEM"


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


@dataclass(frozen=True)
class IntakePolicy:
    """Signed FIXTURE_ONLY file/path/count/total bounds, scope and finite replay expiry."""

    relative_directory: str
    max_path_depth: int
    max_files: int
    max_file_bytes: int
    max_total_bytes: int
    run: RunId
    account: SimulatedAccountId
    valid_from: datetime
    valid_until: datetime
    payload_sha256: Digest

    def __post_init__(self) -> None:
        """Validate path syntax and bootstrap ceilings before any filesystem operation."""
        parts = self.relative_directory.split("/")
        if parts[0] != "stage_a" or any(not _IDENTITY.fullmatch(part) for part in parts):
            raise FixtureDenied(DenialReason.FILESYSTEM, "Invalid repository-fixture path")
        for value, maximum in (
            (self.max_path_depth, 8),
            (self.max_files, 3),
            (self.max_file_bytes, 1_048_576),
            (self.max_total_bytes, 1_052_801),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise FixtureDenied(DenialReason.RESOURCE_BOUND, "Invalid signed filesystem bound")
        if len(parts) > self.max_path_depth:
            raise FixtureDenied(DenialReason.RESOURCE_BOUND, "Signed path depth exceeded")
        require_utc(self.valid_from)
        require_utc(self.valid_until)
        if self.valid_until <= self.valid_from:
            raise FixtureDenied(DenialReason.TIME, "Invalid intake-policy validity interval")


@dataclass(frozen=True)
class FixtureFiles:
    """Verified immutable bytes from one bounded fixture directory; never executable data."""

    payload: bytes
    manifest: bytes
    signature: bytes
    payload_sha256: str
    intake_policy_sha256: str


def load_intake_policy(
    payload: bytes, manifest: bytes, signature: bytes, public_key: bytes
) -> IntakePolicy:
    """Authenticate closed filesystem policy bytes; reject unsigned scope/bounds; no I/O."""
    verified = authenticate_fixture(payload, manifest, signature, public_key)
    record = _parse(verified.payload, verified.bounds)
    fields = {
        "kind",
        "relative_directory",
        "max_path_depth",
        "max_files",
        "max_file_bytes",
        "max_total_bytes",
        "run_id",
        "account_id",
        "valid_from",
        "valid_until",
    }
    if set(record) != fields or record["kind"] != "FIXTURE_INTAKE_POLICY_V1":
        raise FixtureDenied(DenialReason.SCHEMA, "Invalid fixture-intake policy schema")
    return IntakePolicy(
        _text(record["relative_directory"]),
        _integer(record["max_path_depth"]),
        _integer(record["max_files"]),
        _integer(record["max_file_bytes"]),
        _integer(record["max_total_bytes"]),
        RunId(_identity(record["run_id"])),
        SimulatedAccountId(_identity(record["account_id"])),
        parse_utc(_text(record["valid_from"])),
        parse_utc(_text(record["valid_until"])),
        Digest(verified.payload_sha256),
    )


def _read_regular(directory: int, name: str, maximum: int, stack: ExitStack) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_mode & 0o111:
        raise FixtureDenied(DenialReason.FILESYSTEM, "Fixture must be a non-linked regular file")
    if metadata.st_size > maximum:
        raise FixtureDenied(DenialReason.RESOURCE_BOUND, "Fixture file byte limit exceeded")
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = os.read(descriptor, maximum + 1 - size)
        if not chunk:
            return b"".join(chunks)
        size += len(chunk)
        if size > maximum:
            raise FixtureDenied(DenialReason.RESOURCE_BOUND, "Fixture grew beyond signed bound")
        chunks.append(chunk)


def read_fixture_directory(
    policy: IntakePolicy,
    public_key: bytes,
    run: RunId,
    account: SimulatedAccountId,
    at: datetime,
) -> FixtureFiles:
    """Read/authenticate fixed JSON fixture files or raise; no path outside repo fixtures.

    Every ancestor and file is opened no-follow relative to pinned descriptors.
    No directory recursion, executable format, caller-selected filename, hardlink,
    FIFO, unlisted file, credentials or archive extraction is permitted.
    """
    require_utc(at)
    if (
        policy.run != run
        or policy.account != account
        or not policy.valid_from <= at < policy.valid_until
    ):
        raise FixtureDenied(DenialReason.DOMAIN, "Intake scope or replay validity mismatch")
    expected = {"payload.json", "manifest.json", "manifest.sig"}
    try:
        with ExitStack() as stack:
            root = Path(__file__).resolve().parents[2] / "fixtures"
            directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            stack.callback(os.close, directory)
            for part in policy.relative_directory.split("/"):
                directory = os.open(
                    part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
                )
                stack.callback(os.close, directory)
            found = set()
            with os.scandir(directory) as entries:
                for entry in entries:
                    found.add(entry.name)
                    if entry.name not in expected or len(found) > policy.max_files:
                        raise FixtureDenied(
                            DenialReason.FILESYSTEM, "Unlisted or excessive fixture files"
                        )
            if found != expected:
                raise FixtureDenied(DenialReason.FILESYSTEM, "Incomplete fixture directory")
            manifest = _read_regular(
                directory, "manifest.json", min(4096, policy.max_file_bytes), stack
            )
            signature_text = _read_regular(
                directory, "manifest.sig", min(129, policy.max_file_bytes), stack
            )
            if len(signature_text) not in {128, 129} or (
                len(signature_text) == 129 and not signature_text.endswith(b"\n")
            ):
                raise FixtureDenied(DenialReason.SIGNATURE, "Invalid signature file shape")
            try:
                signature = bytes.fromhex(signature_text.decode("ascii"))
            except (ValueError, UnicodeDecodeError) as error:
                raise FixtureDenied(DenialReason.SIGNATURE, "Invalid signature encoding") from error
            payload = _read_regular(directory, "payload.json", policy.max_file_bytes, stack)
            if len(payload) + len(manifest) + len(signature_text) > policy.max_total_bytes:
                raise FixtureDenied(
                    DenialReason.RESOURCE_BOUND, "Signed total intake byte limit exceeded"
                )
            verified = authenticate_fixture(payload, manifest, signature, public_key)
            return FixtureFiles(
                payload, manifest, signature, verified.payload_sha256, policy.payload_sha256.value
            )
    except OSError as error:
        raise FixtureDenied(
            DenialReason.FILESYSTEM, "Fixture filesystem operation failed"
        ) from error
