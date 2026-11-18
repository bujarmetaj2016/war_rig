"""Verify the owner-delivered ALFRED artifacts without contacting FRED."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from .download_macro import (
    API, BASE_SERIES, FIELDS, FX_QUOTES, MANIFEST, SERIES, TRADE_SHA256, DownloadError, Vintage, trade_bounds,
)


def verified_vintages(history: Path, trades: bytes) -> tuple[dict[str, list[Vintage]], dict[str, str]]:
    if hashlib.sha256(trades).hexdigest() != TRADE_SHA256:
        raise DownloadError("Trade export does not match the owner pin.")
    manifest_path = history / MANIFEST
    if not manifest_path.is_file():
        raise DownloadError(f"Missing {MANIFEST}; ALFRED delivery not verified.")
    bounds = trade_bounds(trades)
    pins = {}
    series = {}
    try:
        raw = manifest_path.read_bytes()
        metadata = json.loads(raw)
        pins[MANIFEST] = hashlib.sha256(raw).hexdigest()
        if metadata["trade_results_sha256"] != TRADE_SHA256 or metadata["bounds"] != json.loads(
            json.dumps(asdict(bounds), default=date.isoformat)
        ):
            raise ValueError("Unexpected trade hash or coverage")
        if sorted(item["series_id"] for item in metadata["series"]) not in (
            sorted(BASE_SERIES), sorted(SERIES),
        ):
            raise ValueError("Unexpected series list")
        for item in metadata["series"]:
            name = item["series_id"]
            if name in FX_QUOTES:
                base, quote = FX_QUOTES[name]
                if item["quote_direction"] != {"base": base, "quote": quote}:
                    raise ValueError("Unexpected FX quote direction")
            filename = f"{name}.csv"
            if item["file"] != filename or datetime.fromisoformat(item["downloaded_at_utc"]).utcoffset() is None:
                raise ValueError("Unexpected artifact metadata")
            for url in [item["vintage_dates_url"], *item["observation_urls"]]:
                if not url.startswith(f"{API}/") or any(
                    field.lower() == "api_key" for field, _ in parse_qsl(urlsplit(url).query)
                ):
                    raise ValueError("Unexpected source URL")
            data = (history / filename).read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest != item["sha256"]:
                raise DownloadError(f"{filename}: SHA-256 mismatch.")
            reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
            if tuple(reader.fieldnames or ()) != FIELDS:
                raise ValueError("Unexpected CSV schema")
            rows = [Vintage.from_record(row) for row in reader]
            if not rows or len(rows) != item["vintage_rows"] or any(
                not (bounds.realtime.start <= row.start <= row.end <= bounds.realtime.end)
                or not bounds.observation.start <= row.observation_date <= bounds.observation.end
                for row in rows
            ):
                raise ValueError("Unexpected row count or date range")
            series[name] = rows
            pins[filename] = digest
    except (OSError, KeyError, TypeError, AttributeError, ValueError):
        raise DownloadError("Invalid or incomplete ALFRED artifacts.") from None
    return series, pins


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--trades", type=Path, required=True)
    args = parser.parse_args()
    try:
        _, pins = verified_vintages(args.history, args.trades.read_bytes())
    except (DownloadError, OSError) as error:
        parser.exit(1, f"{error}\n")
    for path, digest in sorted(pins.items()):
        print(f"{digest}  {path}")


if __name__ == "__main__":
    main()
