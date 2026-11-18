"""Create only new signed Stage A fixture slices inside the verified sandbox."""

import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.create_stage_a_calendar_fixtures import write_fixture

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    key = serialization.load_pem_private_key(
        (ROOT / "keys/dev_fixture_signing.key").read_bytes(), password=None
    )
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Expected the existing development-only signer")
    public = json.loads((ROOT / "evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json").read_text())
    if key.public_key().public_bytes_raw().hex() != public["public_key_hex"]:
        raise ValueError("Pinned public key mismatch")
    write_fixture(
        "a3",
        {
            "kind": "FIXTURE_TIER_POLICY_V1",
            "scope": "FIXTURE_ONLY",
            "policy_id": "SYNTHETIC_TIER_POLICY",
            "run_id": "SYNTHETIC_RUN_001",
            "account_id": "SIMULATED_ACCOUNT",
            "instrument_ids": ["XAUUSD", "GER40", "US500", "EURUSD", "GBPUSD", "SYNTHETIC_6"],
            "valid_from": "2027-01-01T00:00:00Z",
            "valid_until": "2028-01-01T00:00:00Z",
            "scenario_sha256": "5" * 64,
            "seed": 0,
            "required_checks": ["SIGNATURE", "COMPLETED_DATA", "SOURCE_BINDING", "SESSION"],
            "directions": ["BULLISH", "BEARISH"],
            "entry_types": ["MARKET"],
            "minimum_rr": {"BULLISH": "2", "BEARISH": "2"},
            "rr_bounds": {"lower_exclusive": "0", "upper_inclusive": "10"},
            "evaluation_budget_seconds": "1",
            "budget_bounds": {"lower_exclusive": "0", "upper_inclusive": "5"},
            "required_strategy_entry_type": "MARKET",
            "t3": {
                "directions": ["BULLISH"],
                "entry_types": ["MARKET"],
                "minimum_rr": {"BULLISH": "3", "BEARISH": None},
                "deny_market_entry": False,
            },
        },
        key,
    )
    print("Signed explicit non-authoritative A3 policy example")


if __name__ == "__main__":
    main()
