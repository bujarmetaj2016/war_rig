"""Rebuild schedule evidence offline from the pinned owner delivery."""

import argparse
import csv
import hashlib
import io
import json
from datetime import date
from pathlib import Path

from research.download_release_schedules import OUTPUT_FIELDS, SOURCES, extract_events

OWNER_MANIFEST_SHA256 = "74de937f1cd121b6c056408d28a464428a2ddffa4671fb16d7c407059ddb6b7b"
REPARSED_EVENTS = "RELEASE_SCHEDULE_EVENTS_REPARSED.csv"
REPARSE_MANIFEST = "RELEASE_SCHEDULE_REPARSE.json"


def reparse(root: Path) -> tuple[bytes, bytes]:
    parent = (root / "release_schedule_manifest.json").read_bytes()
    if hashlib.sha256(parent).hexdigest() != OWNER_MANIFEST_SHA256:
        raise ValueError("Owner schedule manifest SHA-256 mismatch.")
    manifest = json.loads(parent)
    original = manifest["events_file"]
    if hashlib.sha256((root / original["file"]).read_bytes()).hexdigest() != original["sha256"]:
        raise ValueError("Original owner schedule CSV SHA-256 mismatch (integrity check only).")

    start = date.fromisoformat(manifest["schedule_coverage"]["start"])
    end = date.fromisoformat(manifest["schedule_coverage"]["end"])
    sources = {source.key: source for source in SOURCES}
    fingerprints, events = {}, {}
    for item in manifest["source_pages"]:
        filename = item["file"]
        contents = (root / filename).read_bytes()
        digest = hashlib.sha256(contents).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"Schedule source page SHA-256 mismatch: {filename}")
        fingerprints[filename] = digest
        for event in extract_events(
            sources[item["source_key"]], item["source_url"], contents, None,
            item["downloaded_at_utc"], filename, digest, start, end,
        ):
            key = (event["event_type"], event["scheduled_date"])
            if key in events:
                raise ValueError(f"Duplicate schedule event: {key}")
            events[key] = event

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(events[key] for key in sorted(events))
    payload = stream.getvalue().encode()
    derivation = {
        "origin": "Offline re-parse of unchanged owner-downloaded official source pages",
        "owner_manifest_sha256": OWNER_MANIFEST_SHA256,
        "owner_downloaded_at_utc": manifest["downloaded_at_utc"],
        "acquisition_bounds_not_as_known_coverage": manifest["schedule_coverage"],
        "source_page_sha256": fingerprints,
        "original_events_file_not_used_for_classification": original,
        "reparsed_events_file": {"file": REPARSED_EVENTS, "sha256": hashlib.sha256(payload).hexdigest()},
        "event_count": len(events),
    }
    return payload, (json.dumps(derivation, indent=2, sort_keys=True) + "\n").encode()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-delivery", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload, manifest = reparse(args.owner_delivery)
    (args.out / REPARSED_EVENTS).write_bytes(payload)
    (args.out / REPARSE_MANIFEST).write_bytes(manifest)


if __name__ == "__main__":
    main()
