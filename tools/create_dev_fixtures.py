"""Generate development-only Ed25519 keys/fixtures inside the network-denied sandbox."""

import hashlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def main() -> None:
    key_path = ROOT / "keys/dev_fixture_signing.key"
    key_path.parent.mkdir(exist_ok=True, mode=0o700)
    if key_path.exists():
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("Existing development key is not Ed25519")
    else:
        key = Ed25519PrivateKey.generate()
        raw = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        with key_path.open("xb") as target:
            os.chmod(key_path, 0o600)
            target.write(raw)
    public_key = key.public_key().public_bytes_raw()
    public_record = {
        "purpose": "SYNTHETIC_FIXTURES_ONLY_NOT_TRADING_POLICY",
        "algorithm": "Ed25519",
        "public_key_hex": public_key.hex(),
        "sha256": hashlib.sha256(public_key).hexdigest(),
    }
    public_path = ROOT / "evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json"
    if public_path.exists() and json.loads(public_path.read_text()) != public_record:
        raise ValueError("Development key changed; explicit fixture re-signing review required")
    public_path.write_text(json.dumps(public_record, indent=2) + "\n")
    fixture = ROOT / "fixtures/stage_a"
    fixture.mkdir(parents=True, exist_ok=True)
    payload = canonical(
        {
            "policy_id": "STAGE_A_SYNTHETIC",
            "run_id": "SYNTHETIC_RUN_001",
            "account_id": "SIMULATED_ACCOUNT",
            "instrument_ids": ["XAUUSD", "GER40", "US500", "EURUSD", "GBPUSD", "SYNTHETIC_6"],
            "valid_from": "2026-11-18T00:00:00Z",
            "valid_until": "2026-11-19T00:00:00Z",
        }
    )
    manifest = canonical(
        {
            "schema_version": 1,
            "domain": "FIXTURE_ONLY",
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "max_bytes": 16384,
            "max_depth": 8,
            "max_nodes": 128,
        }
    )
    (fixture / "policy.json").write_bytes(payload)
    (fixture / "manifest.json").write_bytes(manifest)
    (fixture / "manifest.sig").write_text(
        key.sign(b"WAR_RIG_DEV_FIXTURE_V1\x00" + manifest).hex() + "\n"
    )
    print("DEVELOPMENT_FIXTURE_SIGNER_SHA256=" + public_record["sha256"])


if __name__ == "__main__":
    main()
