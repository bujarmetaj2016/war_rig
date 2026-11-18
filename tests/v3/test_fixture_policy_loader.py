import hashlib
import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from hypothesis import given
from hypothesis import strategies as st

from v3.offline.fixture_policy_loader import (
    DenialReason,
    FixtureDenied,
    ResourceBounds,
    load_fixture_policy,
)

NOW = datetime(2026, 11, 18, 12, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[2]
POLICY: dict[str, object] = {
    "policy_id": "STAGE_A_SYNTHETIC",
    "run_id": "SYNTHETIC_RUN_001",
    "account_id": "SIMULATED_ACCOUNT",
    "instrument_ids": ["XAUUSD", "GER40", "US500", "EURUSD", "GBPUSD", "SYNTHETIC_6"],
    "valid_from": "2026-11-18T00:00:00Z",
    "valid_until": "2026-11-19T00:00:00Z",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def signed(
    *,
    policy: dict[str, object] | None = None,
    manifest_updates: dict[str, object] | None = None,
    raw_payload: bytes | None = None,
    raw_manifest: bytes | None = None,
) -> tuple[bytes, bytes, bytes, bytes]:
    payload = (
        raw_payload if raw_payload is not None else canonical(POLICY if policy is None else policy)
    )
    manifest: dict[str, object] = {
        "schema_version": 1,
        "domain": "FIXTURE_ONLY",
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "max_bytes": 16384,
        "max_depth": 8,
        "max_nodes": 128,
    }
    manifest.update(manifest_updates or {})
    record = canonical(manifest) if raw_manifest is None else raw_manifest
    key = Ed25519PrivateKey.generate()
    signature = key.sign(b"WAR_RIG_DEV_FIXTURE_V1\x00" + record)
    return payload, record, signature, key.public_key().public_bytes_raw()


def assert_denied(
    reason: DenialReason, bundle: tuple[bytes, bytes, bytes, bytes], at: datetime = NOW
) -> None:
    with pytest.raises(FixtureDenied) as result:
        load_fixture_policy(*bundle, at)
    assert result.value.reason is reason
    assert str(result.value)


def test_signed_policy_binds_identity_lineage_and_all_six_fixture_instruments() -> None:
    bundle = signed()
    loaded = load_fixture_policy(*bundle, NOW)
    assert loaded.policy_id == "STAGE_A_SYNTHETIC"
    assert loaded.run_id == "SYNTHETIC_RUN_001"
    assert loaded.account_id == "SIMULATED_ACCOUNT"
    assert loaded.instrument_ids == ("XAUUSD", "GER40", "US500", "EURUSD", "GBPUSD", "SYNTHETIC_6")
    assert loaded.valid_from == datetime(2026, 11, 18, tzinfo=UTC)
    assert loaded.valid_until == datetime(2026, 11, 19, tzinfo=UTC)
    assert loaded.payload_sha256 == hashlib.sha256(bundle[0]).hexdigest()
    assert loaded.manifest_sha256 == hashlib.sha256(bundle[1]).hexdigest()
    assert loaded.signer_sha256 == hashlib.sha256(bundle[3]).hexdigest()
    assert loaded.bounds == ResourceBounds(16384, 8, 128)
    assert load_fixture_policy(*bundle, NOW) == loaded
    with pytest.raises(FrozenInstanceError):
        loaded.account_id = "LIVE"
    assert not hasattr(loaded, "send_permit")
    assert not hasattr(loaded, "eligible")


def test_committed_fixture_is_verified_against_independently_pinned_public_key() -> None:
    fixture = ROOT / "fixtures/stage_a"
    public = json.loads((ROOT / "evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json").read_text())
    key = bytes.fromhex(public["public_key_hex"])
    assert hashlib.sha256(key).hexdigest() == public["sha256"]
    loaded = load_fixture_policy(
        (fixture / "policy.json").read_bytes(),
        (fixture / "manifest.json").read_bytes(),
        bytes.fromhex((fixture / "manifest.sig").read_text().strip()),
        key,
        NOW,
    )
    assert loaded.instrument_ids[-1] == "SYNTHETIC_6"
    assert loaded.signer_sha256 == public["sha256"]


@pytest.mark.parametrize("field", range(4))
def test_mutating_any_authenticated_input_denies(field: int) -> None:
    parts = list(signed())
    parts[field] += b"!"
    assert_denied(DenialReason.HASH if field == 0 else DenialReason.SIGNATURE, tuple(parts))


def test_untrusted_valid_key_cannot_replace_the_pinned_key() -> None:
    payload, manifest, signature, _ = signed()
    stranger = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    assert_denied(DenialReason.SIGNATURE, (payload, manifest, signature, stranger))


def test_signature_without_the_fixture_domain_is_not_accepted() -> None:
    payload, manifest, _, _ = signed()
    key = Ed25519PrivateKey.generate()
    assert_denied(
        DenialReason.SIGNATURE,
        (payload, manifest, key.sign(manifest), key.public_key().public_bytes_raw()),
    )


@pytest.mark.parametrize(
    "updates,reason",
    [
        ({"schema_version": 2}, DenialReason.SCHEMA),
        ({"schema_version": True}, DenialReason.SCHEMA),
        ({"extra": "owner_policy"}, DenialReason.SCHEMA),
        ({"domain": "OWNER_POLICY"}, DenialReason.DOMAIN),
        ({"domain": "LIVE"}, DenialReason.DOMAIN),
        ({"payload_sha256": "0" * 64}, DenialReason.HASH),
        ({"payload_sha256": "not-a-hash"}, DenialReason.SCHEMA),
        ({"payload_sha256": 42}, DenialReason.SCHEMA),
        ({"max_bytes": 1}, DenialReason.RESOURCE_BOUND),
        ({"max_bytes": 0}, DenialReason.RESOURCE_BOUND),
        ({"max_depth": -1}, DenialReason.RESOURCE_BOUND),
        ({"max_nodes": 10001}, DenialReason.RESOURCE_BOUND),
        ({"max_bytes": True}, DenialReason.SCHEMA),
        ({"max_depth": 1}, DenialReason.RESOURCE_BOUND),
        ({"max_nodes": 1}, DenialReason.RESOURCE_BOUND),
    ],
)
def test_signed_manifest_still_cannot_widen_scope_or_skip_bounds(
    updates: dict[str, object], reason: DenialReason
) -> None:
    assert_denied(reason, signed(manifest_updates=updates))


@pytest.mark.parametrize(
    "updates,reason",
    [
        ({"account_id": "REAL_ACCOUNT"}, DenialReason.DOMAIN),
        ({"run_id": ""}, DenialReason.SCHEMA),
        ({"run_id": "../outside"}, DenialReason.SCHEMA),
        ({"run_id": "\u202e"}, DenialReason.SCHEMA),
        ({"run_id": "r" * 65}, DenialReason.SCHEMA),
        ({"policy_id": None}, DenialReason.SCHEMA),
        ({"instrument_ids": []}, DenialReason.SCHEMA),
        ({"instrument_ids": "EURUSD"}, DenialReason.SCHEMA),
        ({"instrument_ids": ["EURUSD", "EURUSD"]}, DenialReason.SCHEMA),
        ({"instrument_ids": [False]}, DenialReason.SCHEMA),
        ({"valid_from": "2026-11-20T00:00:00Z"}, DenialReason.TIME),
        ({"valid_until": "2026-11-18T00:00:00Z"}, DenialReason.TIME),
        ({"valid_until": "bad-time"}, DenialReason.TIME),
        ({"valid_until": "2026-11-19T00:00:00"}, DenialReason.TIME),
        ({"valid_from": False}, DenialReason.SCHEMA),
        ({"entry_enabled": True}, DenialReason.SCHEMA),
        ({"broker": "IG"}, DenialReason.SCHEMA),
        ({"risk_fraction": "0.01"}, DenialReason.SCHEMA),
    ],
)
def test_signed_payload_cannot_load_unsupported_policy(
    updates: dict[str, object], reason: DenialReason
) -> None:
    assert_denied(reason, signed(policy=POLICY | updates))


def test_missing_fields_never_default() -> None:
    policy = POLICY.copy()
    del policy["valid_until"]
    assert_denied(DenialReason.SCHEMA, signed(policy=policy))
    assert_denied(DenialReason.SCHEMA, signed(raw_manifest=b"{}"))


def test_duplicate_key_cannot_override_an_otherwise_valid_signed_policy() -> None:
    payload = canonical(POLICY)[:-1] + b',"run_id":"OVERRIDE"}'
    assert_denied(DenialReason.JSON, signed(raw_payload=payload))


def test_signed_resource_bounds_accept_the_exact_byte_depth_and_node_boundary() -> None:
    payload = canonical(POLICY)
    loaded = load_fixture_policy(
        *signed(
            raw_payload=payload,
            manifest_updates={"max_bytes": len(payload), "max_depth": 3, "max_nodes": 13},
        ),
        NOW,
    )
    assert loaded.bounds == ResourceBounds(len(payload), 3, 13)
    _, record, _, _ = signed()
    bundle = signed(raw_manifest=record + b" " * (4096 - len(record)))
    assert load_fixture_policy(*bundle, NOW).run_id == "SYNTHETIC_RUN_001"


@pytest.mark.parametrize(
    "raw,reason",
    [
        (b'{"domain":"FIXTURE_ONLY","domain":"LIVE"}', DenialReason.JSON),
        (b'{"a":1.5}', DenialReason.JSON),
        (b'{"a":NaN}', DenialReason.JSON),
        (b'{"a":Infinity}', DenialReason.JSON),
        (b'{"a":-Infinity}', DenialReason.JSON),
        (b'{"a":1e9999}', DenialReason.JSON),
        (b'{"a":' + b"9" * 5000 + b"}", DenialReason.JSON),
        (b"\xff", DenialReason.JSON),
        (b"{", DenialReason.JSON),
        (b'{"x":true} trailing', DenialReason.JSON),
        (b"[]", DenialReason.SCHEMA),
        (b"null", DenialReason.SCHEMA),
        (b'{"a":' + b"[" * 1100 + b"0" + b"]" * 1100 + b"}", DenialReason.RESOURCE_BOUND),
        (b'{"a":' + b"[" * 10 + b"0" + b"]" * 10 + b"}", DenialReason.RESOURCE_BOUND),
        (b'{"a":"escaped\\\\and\\"quoted{[value"}', DenialReason.SCHEMA),
    ],
)
def test_hostile_json_is_never_deserialized_as_policy(raw: bytes, reason: DenialReason) -> None:
    assert_denied(reason, signed(raw_payload=raw))


def test_manifest_has_an_independent_bootstrap_bound() -> None:
    assert_denied(DenialReason.RESOURCE_BOUND, signed(raw_manifest=b" " * 4097))
    assert_denied(
        DenialReason.RESOURCE_BOUND, signed(raw_manifest=canonical({"x": list(range(33))}))
    )


def test_validity_is_half_open_and_never_uses_wall_time() -> None:
    bundle = signed()
    start = datetime(2026, 11, 18, tzinfo=UTC)
    end = start + timedelta(days=1)
    assert load_fixture_policy(*bundle, start).valid_from == start
    assert load_fixture_policy(*bundle, end - timedelta(microseconds=1)).valid_until == end
    for at in (start - timedelta(microseconds=1), end, NOW.replace(tzinfo=None)):
        assert_denied(DenialReason.TIME, bundle, at)


@pytest.mark.parametrize(
    "field,maximum", [("max_bytes", 1048576), ("max_depth", 32), ("max_nodes", 10000)]
)
def test_resource_limits_have_exact_boundaries(field: str, maximum: int) -> None:
    base = {"max_bytes": 1, "max_depth": 1, "max_nodes": 1}
    for value in (1, maximum):
        assert getattr(ResourceBounds(**(base | {field: value})), field) == value
    for value in (-1, 0, maximum + 1, True):
        with pytest.raises(FixtureDenied) as result:
            ResourceBounds(**(base | {field: value}))
        assert result.value.reason is DenialReason.RESOURCE_BOUND


@given(st.binary(min_size=1, max_size=100))
def test_arbitrary_payload_tampering_cannot_preserve_a_valid_policy(suffix: bytes) -> None:
    payload, manifest, signature, public_key = signed()
    assert_denied(DenialReason.HASH, (payload + suffix, manifest, signature, public_key))
