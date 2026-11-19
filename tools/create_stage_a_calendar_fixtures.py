"""Sign synthetic calendar fixtures inside the already verified pinned sandbox."""

import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def write_fixture(
    name: str, value: object, key: Ed25519PrivateKey, *, max_nodes: int = 256
) -> None:
    target = ROOT / "fixtures/stage_a" / name
    target.mkdir(parents=True, exist_ok=True)
    payload = canonical(value)
    manifest = canonical(
        {
            "schema_version": 1,
            "domain": "FIXTURE_ONLY",
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "max_bytes": 65536,
            "max_depth": 8,
            "max_nodes": max_nodes,
        }
    )
    (target / "payload.json").write_bytes(payload)
    (target / "manifest.json").write_bytes(manifest)
    (target / "manifest.sig").write_text(
        key.sign(b"WAR_RIG_DEV_FIXTURE_V1\x00" + manifest).hex() + "\n"
    )


def main() -> None:
    key = serialization.load_pem_private_key(
        (ROOT / "keys/dev_fixture_signing.key").read_bytes(), password=None
    )
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Expected the existing development-only Ed25519 key")
    public = json.loads((ROOT / "evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json").read_text())
    if key.public_key().public_bytes_raw().hex() != public["public_key_hex"]:
        raise ValueError("Pinned fixture public key mismatch")
    version = Path("/usr/share/zoneinfo/tzdata.zi").read_text().splitlines()[0].split()[-1]
    zones = {
        name: base64.b64encode(Path("/usr/share/zoneinfo", name).read_bytes()).decode()
        for name in ("UTC", "Europe/London", "Europe/Berlin", "America/New_York")
    }
    write_fixture(
        "calendar_sources",
        {
            "kind": "PINNED_IMAGE_TZDATA_FIXTURE",
            "timezone_version": version,
            "image_sha256": "5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b",
            "tzif_by_name": zones,
        },
        key,
    )
    write_fixture(
        "a2",
        {
            "kind": "SYNTHETIC_COMPLETED_SNAPSHOT",
            "source_quality": "COMPLETE",
            "run_id": "SYNTHETIC_RUN_001",
            "account_id": "SIMULATED_ACCOUNT",
            "instrument_id": "EURUSD",
            "source_id": "SYNTHETIC_BARS",
            "source_version": "1.0.0",
            "policy_sha256": "1" * 64,
            "feature_schema_sha256": "2" * 64,
            "price_unit": "REFERENCE_POINT",
            "currency": "USD",
            "timezone": "Europe/London",
            "timezone_version": version,
            "timezone_tzif_base64": zones["Europe/London"],
            "session_open": "2027-03-15T08:00:00Z",
            "session_close": "2027-03-15T17:00:00Z",
            "expected_close": "2027-03-15T12:00:00Z",
            "expected_local_close": "2027-03-15T12:00:00+0000",
            "interval_seconds": 300,
            "max_age_seconds": 60,
            "max_publication_delay_seconds": 10,
            "snapshot_id": "SNAPSHOT_001",
            "source_event_id": "BAR_EVENT_001",
            "feature_row_sha256": "3" * 64,
            "bar_start": "2027-03-15T11:55:00Z",
            "bar_end": "2027-03-15T12:00:00Z",
            "bar": {
                "start": "2027-03-15T11:55:00Z",
                "end": "2027-03-15T12:00:00Z",
                "price": "1.25000",
                "complete": True,
                "published_at": "2027-03-15T12:00:02Z",
                "observed_at": "2027-03-15T12:00:04Z",
                "vintage_available_at": "2027-03-15T12:00:02Z",
                "revision_available_at": "2027-03-15T12:00:02Z",
            },
            "clock": {
                "at": "2027-03-15T12:00:05Z",
                "monotonic_ns": 5_000_000_000,
                "domain": "SIMULATED_REPLAY",
                "source_clock_id": "REPLAY_CLOCK_001",
                "skew_bound_microseconds": 0,
                "evidence_sha256": "4" * 64,
            },
        },
        key,
    )
    print("Signed calendar/snapshot fixtures; tzdata=" + version)


if __name__ == "__main__":
    main()
