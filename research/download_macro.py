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
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from http.client import HTTPException
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.parse import unquote, urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

API = "https://api.stlouisfed.org/fred/series"
BASE_SERIES = ("DGS2", "DFII10", "BAMLH0A0HYM2", "DCOILBRENTEU")
# Units of the quoted currency per one unit of the base currency.
FX_QUOTES = {
    "DEXUSEU": ("EUR", "USD"),
    "DEXJPUS": ("USD", "JPY"),
    "DEXUSUK": ("GBP", "USD"),
    "DEXCAUS": ("USD", "CAD"),
    "DEXSZUS": ("USD", "CHF"),
    "DEXUSAL": ("AUD", "USD"),
}
VOLATILITY_SERIES = ("VIXCLS", "VXVCLS")
SERIES = BASE_SERIES + VOLATILITY_SERIES + tuple(FX_QUOTES)
FIELDS = ("date", "realtime_start", "realtime_end", "value")
PAGE_SIZE = 10_000
VINTAGE_PAGE_SIZE = 1_000
MAX_VINTAGE_DATES = 1_500
DAY = timedelta(days=1)
OBSERVATION_LOOKBACK_DAYS = 550
TRADE_SHA256 = "ecd3e98ceda9806d86ddf35ac1dba5f50d9e790d7ad7b1223199ea163676bd7c"
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
class Window:
    start: date
    end: date


@dataclass(frozen=True)
class Bounds:
    earliest_entry: date
    latest_entry: date
    realtime: Window
    observation: Window


def trade_bounds(contents: bytes) -> Bounds:
    try:
        reader = csv.DictReader(contents.decode("utf-8-sig").splitlines())
        entries = []
        for row in reader:
            value = row["fill_time"].strip()
            if value.endswith((" UTC", "Z")):
                value = value.removesuffix(" UTC").removesuffix("Z") + "+00:00"
            entry = datetime.fromisoformat(value)
            if entry.utcoffset() is None:
                raise ValueError("Missing timezone")
            entries.append(entry.astimezone(timezone.utc).date())
        first, last = min(entries), max(entries)
        return Bounds(
            first, last, Window(first - DAY, last - DAY),
            Window(first - timedelta(days=OBSERVATION_LOOKBACK_DAYS), last - DAY),
        )
    except (AttributeError, KeyError, ValueError, OverflowError, csv.Error):
        raise DownloadError("Expected nonempty trade_results.csv with timezone-aware fill_time values.") from None


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


def source_url(endpoint: str, series: str, realtime: Window, observation: Window | None = None) -> str:
    params = {
        "series_id": series, "file_type": "json", "sort_order": "asc",
        "realtime_start": realtime.start, "realtime_end": realtime.end,
        "limit": PAGE_SIZE if observation is not None else VINTAGE_PAGE_SIZE,
    }
    if observation is not None:
        params.update(output_type=1, observation_start=observation.start, observation_end=observation.end)
    return f"{API}/{endpoint}?{urlencode(params)}"


def http_error_message(error: HTTPError, key: str) -> str:
    try:
        message = json.loads(error.read(65_536))["error_message"]
        if isinstance(message, str) and message.strip():
            message = re.sub(re.escape(key), "[REDACTED]", unquote(message), flags=re.IGNORECASE)
            message = re.sub(r"(?i)\bapi_key\s*=[^&\s\"'<>]+", "[REDACTED]", message)
            return "".join(char if char.isprintable() else " " for char in message)
    except (HTTPException, OSError, KeyError, TypeError, ValueError):
        pass
    finally:
        error.close()
    return "No FRED error_message was provided."


def fetch_page(opener, url: str, offset: int, key: str, field: str, limit: int) -> tuple[int, list]:
    try:
        query = urlencode({"offset": offset, "api_key": key})
        with opener.open(f"{url}&{query}", timeout=60) as response:
            payload = json.load(response)
    except HTTPError as error:
        raise DownloadError(f"FRED request failed (HTTP {error.code}): {http_error_message(error, key)}") from None
    except (HTTPException, OSError, ValueError):
        raise DownloadError("FRED request failed or returned invalid JSON.") from None

    try:
        count = payload["count"]
        records = payload[field]
        if (
            type(count) is not int
            or count < offset
            or payload["offset"] != offset
            or not isinstance(records, list)
            or len(records) > min(limit, count - offset)
            or (count > offset and not records)
        ):
            raise ValueError("Invalid page")
    except (KeyError, TypeError, ValueError):
        raise DownloadError(f"FRED returned an invalid {field} page.") from None
    return count, records


def paged_records(opener, url: str, key: str, field: str, limit: int):
    offset = 0
    total = None
    while total is None or offset < total:
        count, records = fetch_page(opener, url, offset, key, field, limit)
        if total is not None and count != total:
            raise DownloadError(f"FRED {field} count changed during pagination.")
        total = count
        yield from records
        offset += len(records)


def split_windows(full: Window, dates: list[date], limit: int = MAX_VINTAGE_DATES) -> list[Window]:
    if (full.start > full.end or limit < 1 or dates != sorted(set(dates))
            or any(not full.start <= day <= full.end for day in dates)):
        raise DownloadError("Invalid FRED vintage date list or real-time range.")
    starts = [full.start, *dates[limit::limit]]
    return [Window(start, end) for start, end in zip(starts, [d - DAY for d in starts[1:]] + [full.end])]


def merge_windows(full: Window, chunks: list[tuple[Window, list[Vintage]]]) -> list[Vintage]:
    expected = full.start.toordinal()
    clipped = set()
    for window, rows in chunks:
        if window.start.toordinal() != expected or not window.start <= window.end <= full.end:
            raise DownloadError("Gap or overlap in requested real-time windows.")
        if not rows:
            raise DownloadError("No observations returned for a real-time window.")
        for row in rows:
            start, end = max(window.start, row.start), min(window.end, row.end)
            if start > end:
                raise DownloadError("FRED returned a vintage outside its requested window.")
            clipped.add(Vintage(row.observation_date, start, end, row.value))
        expected = window.end.toordinal() + 1
    if expected != full.end.toordinal() + 1:
        raise DownloadError("Merged real-time windows do not cover the requested range.")

    merged: list[Vintage] = []
    for row in sorted(clipped, key=lambda r: (r.observation_date, r.start, r.end, r.value)):
        previous = merged[-1] if merged else None
        if previous and previous.observation_date == row.observation_date:
            if row.start.toordinal() != previous.end.toordinal() + 1:
                raise DownloadError("Gap or conflicting overlap in observation vintage periods.")
            if row.value == previous.value:
                merged[-1] = Vintage(row.observation_date, previous.start, row.end, row.value)
                continue
        elif previous and previous.end != full.end:
            raise DownloadError("Observation vintage periods end before the requested range is covered.")
        merged.append(row)
    if merged[-1].end != full.end:
        raise DownloadError("Observation vintage periods end before the requested range is covered.")
    return merged


def download_series(opener, series: str, bounds: Bounds, key: str, stage: Path) -> dict:
    vintage_url = source_url("vintagedates", series, bounds.realtime)
    try:
        dates = [iso_date(item) for item in paged_records(
            opener, vintage_url, key, "vintage_dates", VINTAGE_PAGE_SIZE
        )]
    except (TypeError, ValueError):
        raise DownloadError("FRED returned an invalid vintage date.") from None
    sources = []
    chunks = []
    for window in split_windows(bounds.realtime, dates):
        url = source_url("observations", series, window, bounds.observation)
        try:
            rows = [Vintage.from_record(item) for item in paged_records(
                opener, url, key, "observations", PAGE_SIZE
            )]
        except (TypeError, KeyError, ValueError):
            raise DownloadError("FRED returned invalid observation vintage data.") from None
        if any(
            not bounds.observation.start <= row.observation_date <= bounds.observation.end
            or key in row.value for row in rows
        ):
            raise DownloadError("FRED returned an invalid observation range or value.")
        chunks.append((window, rows))
        sources.append(url)
    merged = merge_windows(bounds.realtime, chunks)
    path = stage / f"{series}.csv"
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(FIELDS)
        writer.writerows((row.observation_date, row.start, row.end, row.value) for row in merged)

    return {
        "series_id": series,
        **({"quote_direction": {"base": FX_QUOTES[series][0], "quote": FX_QUOTES[series][1]}}
           if series in FX_QUOTES else {}),
        "vintage_dates_url": vintage_url,
        "observation_urls": sources,
        "vintage_dates": len(dates),
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "vintage_rows": len(merged),
    }


def download(out: Path, trades: Path, key: str) -> None:
    try:
        contents = trades.read_bytes()
    except OSError:
        raise DownloadError("Could not read the pinned trade_results.csv.") from None
    if hashlib.sha256(contents).hexdigest() != TRADE_SHA256:
        raise DownloadError("trade_results.csv SHA-256 does not match the pinned export.")
    bounds = trade_bounds(contents)
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
                artifacts.append(download_series(opener, series, bounds, key, stage))
            except DownloadError as error:
                raise DownloadError(f"{series}: {error}") from None
        provenance = {
            "trade_results_sha256": TRADE_SHA256,
            "bounds": asdict(bounds),
            "derivation": {
                "entries": "Minimum and maximum fill_time UTC dates in the pinned CSV.",
                "realtime": "Inclusive: day before earliest entry through day before latest entry.",
                "observation": (
                    f"Inclusive: {OBSERVATION_LOOKBACK_DAYS} calendar days before earliest entry "
                    "through the real-time end. Allows for 250 valid changes plus 10 observations "
                    "of lookback, weekends, holidays and missing observations. The analysis "
                    "must still check for 250 usable changes."
                ),
            },
            "series": artifacts,
        }
        (stage / MANIFEST).write_text(json.dumps(
            provenance, default=date.isoformat, indent=2
        ) + "\n", encoding="utf-8")
        for name in names:  # Publish the manifest only after all CSVs are in place.
            (stage / name).rename(out / name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Output directory (e.g. /out).")
    parser.add_argument("--trades", type=Path, default=Path("trade_results.csv"),
                        help="Path to the pinned owner-supplied trade_results.csv.")
    args = parser.parse_args(argv)
    key = os.environ.get("FRED_API_KEY", "")
    if not re.fullmatch(r"[a-z0-9]{32}", key):
        print("Set FRED_API_KEY to a valid research key in the job environment.", file=sys.stderr)
        return 1
    try:
        download(args.out, args.trades, key)
    except DownloadError as error:
        print(error, file=sys.stderr)
        return 1
    except OSError:
        print("Could not write FRED artifacts to the output directory.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
