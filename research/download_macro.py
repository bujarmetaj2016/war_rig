#!/usr/bin/env python3
"""Fetch REV4's FRED/ALFRED series from an isolated research job."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from http.client import HTTPException
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

ENDPOINT = "https://api.stlouisfed.org/fred/series/observations"
SERIES = ("DGS2", "DFII10", "BAMLH0A0HYM2", "DCOILBRENTEU")
FIELDS = ("date", "realtime_start", "realtime_end", "value")
PAGE_SIZE = 10_000
MANIFEST = "fred_download_manifest.json"
NUMBER = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")


class DownloadError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def iso_date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Expected YYYY-MM-DD")
    return parsed


@dataclass(frozen=True)
class Vintage:
    observation_date: date
    start: date
    end: date
    value: str

    @classmethod
    def from_record(cls, record: dict) -> Vintage:
        observation, start, end = (iso_date(record[field]) for field in FIELDS[:3])
        value = record["value"]
        if start > end or (value != "." and not NUMBER.fullmatch(value)):
            raise ValueError("Invalid vintage record")
        return cls(observation, start, end, value)

    def available_at(self, entry: datetime) -> bool:
        """Treat the entry date as UTC and use only earlier vintage dates."""
        if entry.utcoffset() is None:
            raise ValueError("Trade entry time must have a timezone")
        entry_date = entry.astimezone(timezone.utc).date()
        # FRED real-time intervals end inclusively. This is the interval
        # containing the day before entry, without underflow at date.min.
        return (
            self.value != "."
            and self.observation_date < entry_date
            and self.start < entry_date
            and self.end.toordinal() + 1 >= entry_date.toordinal()
        )


def source_url(series: str, start: date, end: date) -> str:
    return f"{ENDPOINT}?" + urlencode(
        {
            "series_id": series,
            "file_type": "json",
            "output_type": 1,  # Observations by real-time period, including revisions.
            "realtime_start": "1776-07-04",
            "realtime_end": "9999-12-31",
            "observation_start": start.isoformat(),
            "observation_end": end.isoformat(),
            "sort_order": "asc",
            "limit": PAGE_SIZE,
        }
    )


def fetch_page(opener, url: str, offset: int, key: str) -> tuple[int, list[Vintage]]:
    # Keep transport URLs and API error bodies out of logs and provenance.
    try:
        query = urlencode({"offset": offset, "api_key": key})
        with opener.open(f"{url}&{query}", timeout=60) as response:
            payload = json.load(response)
    except HTTPError as error:
        error.close()
        raise DownloadError(f"FRED request failed (HTTP {error.code}).") from None
    except (HTTPException, OSError, ValueError):
        raise DownloadError("FRED request failed or returned invalid JSON.") from None

    try:
        count = payload["count"]
        records = payload["observations"]
        if (
            type(count) is not int
            or count <= offset
            or payload["offset"] != offset
            or not isinstance(records, list)
            or not 0 < len(records) <= min(PAGE_SIZE, count - offset)
        ):
            raise ValueError("Invalid page")
        rows = [Vintage.from_record(record) for record in records]
        if any(key in row.value for row in rows):
            raise ValueError("Unexpected observation value")
    except (KeyError, TypeError, ValueError):
        raise DownloadError("FRED returned invalid or empty vintage data.") from None
    return count, rows


def download_series(opener, series: str, start: date, end: date, key: str, stage: Path) -> dict:
    url = source_url(series, start, end)
    path = stage / f"{series}.csv"
    offset = 0
    total = None
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(FIELDS)
        while total is None or offset < total:
            count, rows = fetch_page(opener, url, offset, key)
            if total is not None and count != total:
                raise DownloadError("FRED observation count changed during pagination.")
            total = count
            for row in rows:
                if not start <= row.observation_date <= end:
                    raise DownloadError("FRED returned an observation outside the requested range.")
                writer.writerow((row.observation_date, row.start, row.end, row.value))
            offset += len(rows)

    return {
        "series_id": series,
        "source_url": url,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "vintage_rows": offset,
    }


def download(out: Path, start: date, end: date, key: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    names = [f"{series}.csv" for series in SERIES] + [MANIFEST]
    if any((out / name).exists() or (out / name).is_symlink() for name in names):
        raise DownloadError("FRED output files already exist; use a fresh output directory.")
    opener = build_opener(ProxyHandler({}), NoRedirect())
    with TemporaryDirectory(prefix=".fred-", dir=out) as temp:
        stage = Path(temp)
        artifacts = []
        for series in SERIES:
            try:
                artifacts.append(download_series(opener, series, start, end, key, stage))
            except DownloadError as error:
                raise DownloadError(f"{series}: {error}") from None
        (stage / MANIFEST).write_text(
            json.dumps({"series": artifacts}, indent=2) + "\n", encoding="utf-8"
        )
        for name in names:  # Publish the manifest only after all CSVs are in place.
            (stage / name).rename(out / name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Output directory (e.g. /out).")
    parser.add_argument("--start", type=iso_date, default="1776-07-04", help="First observation date.")
    parser.add_argument("--end", type=iso_date, default="9999-12-31", help="Last observation date.")
    args = parser.parse_args(argv)
    if args.start > args.end:
        parser.error("--start must be on or before --end")
    key = os.environ.get("FRED_API_KEY", "")
    if not re.fullmatch(r"[a-z0-9]{32}", key):
        print("Set FRED_API_KEY to a valid research key in the job environment.", file=sys.stderr)
        return 1
    try:
        download(args.out, args.start, args.end, key)
    except DownloadError as error:
        print(error, file=sys.stderr)
        return 1
    except OSError:
        print("Could not write FRED artifacts to the output directory.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
