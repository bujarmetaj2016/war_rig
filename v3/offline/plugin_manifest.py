"""EXT-02 closed signed fixture registrations; metadata only, never plug-in discovery/import."""

import hashlib
import json
from dataclasses import dataclass

from v3.offline.data_intake_schema import digest, object_fields
from v3.offline.effective_policy import _strings
from v3.offline.fixture_policy_loader import _identity, _parse, authenticate_fixture
from v3.offline.intent_identity import Digest, Identity

_INTERFACES = {
    "SNAPSHOT_FIXTURE_V1": ("v3.offline.data_intake_schema", "SIGNED_SYNTHETIC_DATA"),
    "COMPLETION_V1": ("v3.offline.calendar_completion", "PURE_COMPLETION"),
    "CALENDAR_V1": ("v3.offline.calendar_completion", "PURE_CALENDAR"),
    "MACRO_INPUT_V1": ("v3.offline.data_intake_schema", "SIGNED_SYNTHETIC_DATA"),
    "FIXTURE_PARAMETERS_V1": ("v3.offline.effective_policy", "FIXTURE_PARAMETERS"),
}


@dataclass(frozen=True)
class BuildArtifact:
    """Actual preflight-pinned source and explicit first-party dependency digests."""

    module: str
    sha256: Digest
    dependencies: tuple[str, ...]


def build_fingerprint(artifacts: tuple[BuildArtifact, ...]) -> Digest:
    """Hash the sorted source/dependency inventory independently of fixture configuration."""
    inventory = sorted((item.module, item.sha256.value, item.dependencies) for item in artifacts)
    if not inventory or len({item[0] for item in inventory}) != len(inventory):
        raise ValueError("Missing or duplicate build source")
    return Digest(hashlib.sha256(json.dumps(inventory, separators=(",", ":")).encode()).hexdigest())


@dataclass(frozen=True)
class PluginRegistration:
    """One exact interface/version/path/hash and restriction-only capability declaration."""

    plugin_id: Identity
    interface_id: str
    version: str
    artifact_sha256: Digest
    source_import_path: str
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class PluginManifest:
    """Authenticated immutable build-bound registry; no dynamic loader or executable capability."""

    entries: tuple[PluginRegistration, ...]
    build_sha256: Digest
    payload_sha256: Digest

    def require(self, plugin_id: str, interface: str, version: str = "1.0.0") -> PluginRegistration:
        """Resolve exactly one registered compatible ID, or deny; no fuzzy lookup/fallback."""
        for entry in self.entries:
            if (
                entry.plugin_id.value == plugin_id
                and entry.interface_id == interface
                and entry.version == version
            ):
                return entry
        raise ValueError("Absent or incompatible registered plug-in")


def load_plugin_manifest(
    payload: bytes,
    manifest: bytes,
    signature: bytes,
    public_key: bytes,
    artifacts: tuple[BuildArtifact, ...],
) -> PluginManifest:
    """Verify signatures, actual build bytes and the closed interface/capability inventory."""
    verified = authenticate_fixture(payload, manifest, signature, public_key)
    record = object_fields(
        _parse(verified.payload, verified.bounds), {"kind", "build_sha256", "entries"}
    )
    build = build_fingerprint(artifacts)
    if (
        record["kind"] != "FIXTURE_PLUGIN_MANIFEST_V1"
        or digest(record["build_sha256"]) != build.value
    ):
        raise ValueError("Wrong manifest domain or permitted build")
    raw_entries = record["entries"]
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError("Explicit nonempty plug-in registry required")
    sources = {item.module: item for item in artifacts}
    entries: list[PluginRegistration] = []
    for raw in raw_entries:
        item = object_fields(
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
        plugin_id, interface = _identity(item["plugin_id"]), _identity(item["interface_id"])
        path, version = _identity(item["source_import_path"]), _identity(item["version"])
        raw_dependencies = item["dependencies"]
        if not isinstance(raw_dependencies, list):
            raise ValueError("Explicit dependency digest list required")
        dependencies = tuple(sorted(digest(value) for value in raw_dependencies))
        if (
            interface not in _INTERFACES
            or _INTERFACES[interface][0] != path
            or set(_strings(item["capabilities"])) != {_INTERFACES[interface][1]}
            or version != "1.0.0"
            or item["schema_version"] != "1.0.0"
            or digest(item["permitted_build_id"]) != build.value
            or path not in sources
            or digest(item["artifact_sha256"]) != sources[path].sha256.value
            or dependencies != tuple(sorted(sources[path].dependencies))
            or any(entry.plugin_id.value == plugin_id for entry in entries)
        ):
            raise ValueError(
                "Unregistered source, dependency, capability, version or duplicate plug-in"
            )
        entries.append(
            PluginRegistration(
                Identity(plugin_id),
                interface,
                version,
                sources[path].sha256,
                path,
                dependencies,
            )
        )
    return PluginManifest(tuple(entries), build, Digest(verified.payload_sha256))
