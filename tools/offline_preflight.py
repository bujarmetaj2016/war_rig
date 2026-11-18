"""Verify pinned inputs and hostile egress failures before importing any V3 code."""

import hashlib
import http.server
import importlib.util
import json
import os
import re
import socket
import stat
import subprocess
import sys
import threading
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PINNED_INPUTS = {
    "evidence/macro/MANIFEST.sha256": (
        "12ebf4559badf11714ff6af71eb1092537230ed699721fc3bda6b95bdb3a17ca"
    ),
    "reference/MANIFEST.sha256": (
        "a06ac2de31fcce5436d9c975ea7b0cf872a050a6b7d475e2e4b2f09fdff1a38b"
    ),
    "requirements-dev.lock": ("6db111bb0a2ed79f9f7d2002d4b44a1cde5e62ce0e53c321be967f4839048b15"),
    "wheelhouse/SHA256SUMS": ("d93c3cc5ebaf4e43d34d85556967c212a8179549407e22cbcd5aef904bbbe850"),
    "evidence/preflight/OWNER_DIRECTED_OFFLINE_START.md": (
        "e601e066ae601df9d6080d5bff187b73a212e987e5c95cf3d2d6aebc57f9662f"
    ),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(name: str, base: Path) -> dict[str, object]:
    path = ROOT / name
    entries = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([0-9a-f]{64}) [ *](.+)", line)
        if match is None:
            raise ValueError(f"Invalid manifest entry in {name}")
        expected, relative = match.groups()
        member = PurePosixPath(relative)
        target = base / member
        if member.is_absolute() or ".." in member.parts:
            raise ValueError(f"Unsafe manifest path in {name}")
        if any(part.is_symlink() for part in [target, *target.parents]):
            raise ValueError(f"Symlink input: {relative}")
        if digest(target) != expected:
            raise ValueError(f"Hash mismatch: {relative}")
        entries.append(relative)
    if len(entries) != len(set(entries)):
        raise ValueError(f"Duplicate manifest entries: {name}")
    if name == "wheelhouse/SHA256SUMS":
        if set(entries) != {p.name for p in base.iterdir() if p.name != "SHA256SUMS"}:
            raise ValueError("Unlisted wheelhouse content")
        if any(not entry.endswith(".whl") for entry in entries):
            raise ValueError("Only pinned binary wheels are permitted")
    return {"path": name, "sha256": digest(path), "verified_entries": len(entries)}


def verify_archive() -> dict[str, object]:
    path = ROOT / ("design/War_Rig_V3_Complete_Offline_Design_V5_MSB_REVIEW_CANDIDATE_20261113.zip")
    if digest(path) != "3d6632a2d662deade05b957ad822edd9af6e8eda8c1d7ebca3f098e122760796":
        raise ValueError("V5 candidate archive identity mismatch")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [entry.filename for entry in infos]
        if len(infos) != 70 or len(set(names)) != 70:
            raise ValueError("Unexpected/duplicate archive members")
        if sum(entry.file_size for entry in infos) > 20_000_000:
            raise ValueError("Archive exceeds bootstrap inspection size bound")
        for entry in infos:
            member = PurePosixPath(entry.filename)
            mode = entry.external_attr >> 16
            if (
                member.is_absolute()
                or ".." in member.parts
                or "\\" in entry.filename
                or stat.S_ISLNK(mode)
                or mode & 0o111
            ):
                raise ValueError("Unsafe/executable archive member")
        raw = archive.read("MANIFEST_SHA256.json")
        manifest = json.loads(raw)
        entries = manifest["entries"]
        expected = [entry["path"] for entry in entries]
        if (
            manifest["members"] != 69
            or len(expected) != 69
            or len(set(expected)) != 69
            or set(names) != set(expected) | {"MANIFEST_SHA256.json"}
        ):
            raise ValueError("Archive manifest membership mismatch")
        for entry in entries:
            content = archive.read(entry["path"])
            if (
                len(content) != entry["size_bytes"]
                or hashlib.sha256(content).hexdigest() != entry["sha256"]
            ):
                raise ValueError("Archive member integrity mismatch")
    return {
        "archive_sha256": digest(path),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "verified_members": 69,
        "extracted": False,
    }


def blocked(name: str, action: Callable[[], object]) -> dict[str, str]:
    try:
        action()
    except OSError as error:
        return {"name": name, "status": "BLOCKED_AS_REQUIRED", "error": str(error)}
    raise RuntimeError(f"Egress unexpectedly succeeded: {name}")


def connect(ip: str) -> None:
    with socket.create_connection((ip, 80), timeout=2):
        pass


class Redirect(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(302)
        self.send_header("Location", "http://169.254.169.254/")
        self.end_headers()

    def log_message(self, *_args: object) -> None:
        pass


def main() -> None:
    interfaces = {
        name: int((Path("/sys/class/net") / name / "flags").read_text().strip(), 16)
        for _, name in socket.if_nameindex()
    }
    active_interfaces = sorted(name for name, flags in interfaces.items() if flags & 1)
    if not Path("/.dockerenv").is_file() or active_interfaces != ["lo"]:
        raise RuntimeError("Run preflight only in the network-none container")
    mounts = Path("/proc/mounts").read_text().splitlines()
    if not any(
        line.split()[1] == "/repo/reference" and "ro" in line.split()[3].split(",")
        for line in mounts
    ):
        raise RuntimeError("Reference inputs must be independently read-only mounted")
    if any(key.startswith(("AWS_", "IG_", "AZURE_", "GOOGLE_")) for key in os.environ):
        raise RuntimeError("Credential/provider environment is forbidden")
    for relative, expected in PINNED_INPUTS.items():
        if digest(ROOT / relative) != expected:
            raise RuntimeError(f"Pinned input identity mismatch: {relative}")
    for name in ("trading_ig", "boto3", "requests", "httpx", "xgboost", "sklearn", "joblib"):
        if importlib.util.find_spec(name) is not None:
            raise RuntimeError(f"Forbidden broker/cloud/model dependency: {name}")
    manifests = [
        verify_manifest("evidence/macro/MANIFEST.sha256", ROOT),
        verify_manifest("reference/MANIFEST.sha256", ROOT),
        verify_manifest("wheelhouse/SHA256SUMS", ROOT / "wheelhouse"),
    ]
    archive = verify_archive()
    probes = [
        blocked("literal_ip_tcp", lambda: connect("1.1.1.1")),
        blocked("dns", lambda: socket.getaddrinfo("example.com", 80)),
        blocked("metadata_tcp", lambda: connect("169.254.169.254")),
    ]
    child = "import urllib.request; urllib.request.urlopen('http://1.1.1.1/',timeout=2)"
    for name, args in (
        ("python_child_http", [sys.executable, "-I", "-c", child]),
        ("shell_child_http", ["/bin/sh", "-c", 'python -I -c "$1"', "probe", child]),
    ):
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=10,
            env={"PATH": "/usr/local/bin:/usr/bin:/bin"},
        )
        if result.returncode == 0 or "Network is unreachable" not in result.stderr:
            raise RuntimeError(f"Hostile probe did not prove network denial: {name}")
        probes.append({"name": name, "status": "BLOCKED_AS_REQUIRED", "stderr": result.stderr})
    with http.server.HTTPServer(("127.0.0.1", 0), Redirect) as server:
        thread = threading.Thread(target=server.handle_request)
        thread.start()
        probes.append(
            blocked(
                "loopback_redirect_to_metadata",
                lambda: urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}", timeout=3),
            )
        )
        thread.join(timeout=5)
        if thread.is_alive():
            raise RuntimeError("Redirect probe did not complete")
    report = {
        "status": "PASS",
        "image": (ROOT / "evidence/preflight/PYTHON_IMAGE.txt").read_text().strip(),
        "python": sys.version,
        "archive": archive,
        "manifests": manifests,
        "requirements_lock_sha256": digest(ROOT / "requirements-dev.lock"),
        "resume_input_identities": "PASS",
        "probes": probes,
        "broker_cloud_model_sdks": "ABSENT",
        "network_interface_flags": interfaces,
        "active_network_interfaces": active_interfaces,
        "reference_mount": "READ_ONLY",
        "v3_runtime_imported_by_preflight": False,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
