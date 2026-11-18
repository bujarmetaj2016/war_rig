import hashlib
import os
import tempfile
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from test_fixture_policy_loader import NOW, ROOT, signed

from v3.offline import fixture_policy_loader as loader
from v3.offline.fixture_policy_loader import (
    DenialReason,
    FixtureDenied,
    IntakePolicy,
    load_intake_policy,
    read_fixture_directory,
)
from v3.offline.intent_identity import RunId, SimulatedAccountId

RUN = RunId("SYNTHETIC_RUN_001")
ACCOUNT = SimulatedAccountId("SIMULATED_ACCOUNT")


def policy_record(directory: str) -> dict[str, object]:
    return {
        "kind": "FIXTURE_INTAKE_POLICY_V1",
        "relative_directory": directory,
        "max_path_depth": 3,
        "max_files": 3,
        "max_file_bytes": 65536,
        "max_total_bytes": 70000,
        "run_id": RUN.value,
        "account_id": ACCOUNT.value,
        "valid_from": "2026-11-18T00:00:00Z",
        "valid_until": "2026-11-19T00:00:00Z",
    }


@pytest.fixture
def disk_fixture():
    with tempfile.TemporaryDirectory(prefix="intake-", dir=ROOT / "fixtures/stage_a") as folder:
        directory = Path(folder)
        bundle = signed()
        for name, value in zip(
            ("payload.json", "manifest.json", "manifest.sig"),
            (bundle[0], bundle[1], bundle[2].hex().encode() + b"\n"),
            strict=True,
        ):
            (directory / name).write_bytes(value)
        policy = load_intake_policy(
            *signed(policy=policy_record(str(directory.relative_to(ROOT / "fixtures"))))
        )
        yield directory, bundle, policy


def read(bundle, policy: IntakePolicy):
    return read_fixture_directory(policy, bundle[3], RUN, ACCOUNT, NOW)


def test_descriptor_intake_authenticates_exact_bytes_and_returns_immutable_provenance(disk_fixture):
    _, bundle, policy = disk_fixture
    result = read(bundle, policy)
    assert (result.payload, result.manifest, result.signature) == bundle[:3]
    assert result.payload_sha256 == hashlib.sha256(bundle[0]).hexdigest()
    assert result.intake_policy_sha256 == policy.payload_sha256.value
    assert read(bundle, policy) == result


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/stage_a/a3",
        "../keys",
        "stage_a/../keys",
        "stage_a//a3",
        "stage_a/.hidden",
        "stage_a/a\\b",
        "stage_a/a\nb",
        "stage_a/" + "a" * 65,
        "stage_a/\u00e9",
    ],
)
def test_unsafe_paths_deny_before_filesystem_operations(path, monkeypatch):
    monkeypatch.setattr(loader.os, "open", lambda *a, **k: pytest.fail("I/O before validation"))
    with pytest.raises(FixtureDenied):
        load_intake_policy(*signed(policy=policy_record(path)))


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_path_depth", 1),
        ("max_path_depth", 9),
        ("max_files", 0),
        ("max_files", 4),
        ("max_file_bytes", 0),
        ("max_file_bytes", 1048577),
        ("max_total_bytes", 1052802),
        ("max_files", True),
        ("kind", "OWNER_LIVE_POLICY"),
        ("max_files", "3"),
        ("valid_until", "2026-11-17T00:00:00Z"),
    ],
)
def test_signed_invalid_intake_policy_rejects(field, value):
    record = policy_record("stage_a/a3")
    record[field] = value
    with pytest.raises((FixtureDenied, ValueError)):
        load_intake_policy(*signed(policy=record))


@pytest.mark.parametrize("field", range(4))
def test_intake_policy_rejects_mutated_authentication_inputs(field):
    bundle = list(signed(policy=policy_record("stage_a/a3")))
    bundle[field] += b"!"
    with pytest.raises(FixtureDenied):
        load_intake_policy(*bundle)


@pytest.mark.parametrize("scope", ["run", "account", "expired"])
def test_scope_and_expiry_fail_before_io(disk_fixture, scope, monkeypatch):
    _, bundle, policy = disk_fixture
    monkeypatch.setattr(loader.os, "open", lambda *a, **k: pytest.fail("I/O before scope check"))
    with pytest.raises(FixtureDenied, match="scope"):
        read_fixture_directory(
            policy,
            bundle[3],
            RunId("OTHER") if scope == "run" else RUN,
            SimulatedAccountId("SIMULATED_OTHER") if scope == "account" else ACCOUNT,
            NOW + timedelta(days=1) if scope == "expired" else NOW,
        )


@pytest.mark.parametrize("artifact", [".env", "credentials.json", "code.py", "unlisted.json"])
def test_unlisted_hidden_credentials_and_executable_names_deny(disk_fixture, artifact):
    directory, bundle, policy = disk_fixture
    (directory / artifact).write_text("untrusted")
    with pytest.raises(FixtureDenied):
        read(bundle, policy)


@pytest.mark.parametrize("change", ["missing", "count", "file_bytes", "total_bytes", "exec"])
def test_exact_inventory_file_and_total_limits_are_enforced(disk_fixture, change):
    directory, bundle, policy = disk_fixture
    if change == "missing":
        (directory / "payload.json").unlink()
    elif change == "count":
        policy = replace(policy, max_files=2)
    elif change == "file_bytes":
        policy = replace(policy, max_file_bytes=1)
    elif change == "total_bytes":
        policy = replace(policy, max_total_bytes=1)
    else:
        (directory / "payload.json").chmod(0o755)
    with pytest.raises(FixtureDenied):
        read(bundle, policy)


@pytest.mark.parametrize("change", ["symlink", "ancestor", "hardlink", "fifo", "directory"])
def test_no_follow_nonregular_and_hardlinked_files_deny_without_blocking(disk_fixture, change):
    directory, bundle, policy = disk_fixture
    target = directory / "payload.json"
    if change == "ancestor":
        alias = directory / "alias"
        alias.symlink_to(directory, target_is_directory=True)
        policy = replace(
            policy, relative_directory=policy.relative_directory + "/alias", max_path_depth=4
        )
    else:
        target.unlink()
        if change == "symlink":
            target.symlink_to(directory / "manifest.json")
        elif change == "hardlink":
            os.link(directory / "manifest.json", target)
        elif change == "fifo":
            os.mkfifo(target)
        else:
            target.mkdir()
    with pytest.raises(FixtureDenied):
        read(bundle, policy)


@pytest.mark.parametrize("signature", [b"", b"x" * 128, b"\xff" * 128, b"0" * 128 + b"x"])
def test_invalid_signature_file_shapes_and_encodings_deny(disk_fixture, signature):
    directory, bundle, policy = disk_fixture
    (directory / "manifest.sig").write_bytes(signature)
    with pytest.raises(FixtureDenied):
        read(bundle, policy)


def test_signature_without_trailing_newline_is_supported(disk_fixture):
    directory, bundle, policy = disk_fixture
    (directory / "manifest.sig").write_bytes(bundle[2].hex().encode())
    assert read(bundle, policy).signature == bundle[2]


@pytest.mark.parametrize("operation", ["open", "scandir", "fstat", "read"])
def test_filesystem_faults_are_explicit_denials_not_empty_success(
    disk_fixture, monkeypatch, operation
):
    _, bundle, policy = disk_fixture

    def fail(*args, **kwargs):
        raise OSError("injected fixture I/O fault")

    operations = dict(vars(os))
    operations[operation] = fail
    monkeypatch.setattr(loader, "os", SimpleNamespace(**operations))
    with pytest.raises(FixtureDenied) as failure:
        read(bundle, policy)
    assert failure.value.reason is DenialReason.FILESYSTEM
    assert isinstance(failure.value.__cause__, OSError)


def test_concurrent_file_growth_cannot_bypass_size_limit(disk_fixture, monkeypatch):
    _, bundle, policy = disk_fixture
    original = loader.os.fstat

    def stale_size(fd):
        info = original(fd)
        return SimpleNamespace(st_mode=info.st_mode, st_nlink=info.st_nlink, st_size=0)

    operations = dict(vars(os))
    operations["fstat"] = stale_size
    monkeypatch.setattr(loader, "os", SimpleNamespace(**operations))
    with pytest.raises(FixtureDenied, match="grew"):
        read(bundle, replace(policy, max_file_bytes=1))


@given(st.integers(min_value=0, max_value=30))
def test_signed_path_depth_is_not_advisory(depth):
    record = policy_record("stage_a/" + "/".join("x" for _ in range(depth + 1)))
    record["max_path_depth"] = 3
    if depth <= 1:
        assert load_intake_policy(*signed(policy=record)).max_path_depth == 3
    else:
        with pytest.raises(FixtureDenied):
            load_intake_policy(*signed(policy=record))


def test_disk_payload_or_untrusted_key_cannot_bypass_authentication(disk_fixture):
    directory, bundle, policy = disk_fixture
    with pytest.raises(FixtureDenied):
        read_fixture_directory(policy, b"x" * 32, RUN, ACCOUNT, NOW)
    (directory / "payload.json").write_bytes(bundle[0] + b" ")
    with pytest.raises(FixtureDenied) as failure:
        read(bundle, policy)
    assert failure.value.reason is DenialReason.HASH


def test_even_authentic_bytes_cannot_be_followed_through_a_symlink(disk_fixture):
    directory, bundle, policy = disk_fixture
    with tempfile.TemporaryDirectory(
        prefix="link-target-", dir=ROOT / "fixtures/stage_a"
    ) as folder:
        original = Path(folder) / "genuine.json"
        original.write_bytes(bundle[0])
        (directory / "payload.json").unlink()
        (directory / "payload.json").symlink_to(original)
        with pytest.raises(FixtureDenied):
            read(bundle, policy)
