#!/usr/bin/env python3
"""Download official macro release schedules for an isolated research job.

The program is deliberately standard-library-only. It preserves each source
page and its hash; it does not infer a publication time or reconstruct an
as-of schedule from a page downloaded later.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

MAX_PAGE_BYTES = 12 * 1024 * 1024
MAX_PAGES = 100
USER_AGENT = "WarRigMacroResearch/1.0 (official schedule archive)"
OUTPUT_FIELDS = (
    "event_type",
    "scheduled_date",
    "scheduled_date_text",
    "scheduled_time",
    "time_zone",
    "source_url",
    "page_updated_date",
    "downloaded_at_utc",
    "source_file",
    "source_sha256",
    "schedule_text",
)


@dataclass(frozen=True)
class Source:
    key: str
    event_type: str
    url: str
    host: str
    terms: tuple[str, ...]


@dataclass(frozen=True)
class ScheduleBounds:
    fred_realtime_start: date
    fred_realtime_end: date
    latest_trade_date: date
    schedule_end: date


SOURCES = (
    Source(
        "fomc",
        "Federal Reserve FOMC meeting",
        "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "www.federalreserve.gov",
        ("fomc", "federal open market committee", "meeting"),
    ),
    Source(
        "ecb",
        "ECB monetary policy meeting",
        "https://www.ecb.europa.eu/press/calendars/mgc/html/index.en.html",
        "www.ecb.europa.eu",
        ("monetary policy", "governing council"),
    ),
    Source(
        "boe",
        "Bank of England MPC decision",
        "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates",
        "www.bankofengland.co.uk",
        ("mpc", "monetary policy committee", "policy decision"),
    ),
    Source(
        "bls_cpi",
        "BLS Consumer Price Index release",
        "https://www.bls.gov/schedule/news_release/cpi.htm",
        "www.bls.gov",
        ("consumer price index", "cpi"),
    ),
    Source(
        "bls_empsit",
        "BLS Employment Situation release",
        "https://www.bls.gov/schedule/news_release/empsit.htm",
        "www.bls.gov",
        ("employment situation", "employment situation summary"),
    ),
)

MONTHS = {
    name.lower(): number
    for number, names in enumerate(
        (
            (),
            ("january", "jan"),
            ("february", "feb"),
            ("march", "mar"),
            ("april", "apr"),
            ("may",),
            ("june", "jun"),
            ("july", "jul"),
            ("august", "aug"),
            ("september", "sep", "sept"),
            ("october", "oct"),
            ("november", "nov"),
            ("december", "dec"),
        )
    )
    for name in names
}
MONTH_PATTERN = "|".join(sorted(MONTHS, key=len, reverse=True))
DATE_PATTERNS = (
    re.compile(r"\b(?P<year>20\d{2})[-/](?P<month>\d{1,2})[-/](?P<day>\d{1,2})\b"),
    re.compile(
        rf"\b(?P<month_name>{MONTH_PATTERN})\.?\s+(?P<day>\d{{1,2}})"
        r"(?:\s*(?:-|–|—|to)\s*\d{1,2})?,?\s+(?P<year>20\d{2})\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<day>\d{{1,2}})\s+(?P<month_name>{MONTH_PATTERN})\.?,?\s+"
        r"(?P<year>20\d{2})\b",
        re.IGNORECASE,
    ),
)
UPDATED_PATTERN = re.compile(
    r"\b(?:last\s+updated|updated|published|publication\s+date|date\s+published)"
    r"\s*(?:on|:)?\s*([^\n|;]{0,80})",
    re.IGNORECASE,
)
TIME_PATTERN = re.compile(
    r"\b(?P<time>\d{1,2}:\d{2}(?:\s*[ap]\.?m\.?)?)"
    r"(?:\s*(?P<zone>ET|EDT|EST|CT|CDT|CST|MT|MDT|MST|PT|PDT|PST|"
    r"UTC|GMT|BST|CET|CEST|EET|EEST|Eastern\s+(?:Standard|Daylight)\s+Time|"
    r"Central\s+(?:Standard|Daylight)\s+Time|Eastern\s+Time|Central\s+Time|"
    r"Mountain\s+Time|Pacific\s+Time))?(?![A-Za-z])",
    re.IGNORECASE,
)


class DownloadError(Exception):
    """A safe, user-facing acquisition or validation error."""


class SafeRedirect(HTTPRedirectHandler):
    def __init__(self, allowed_host: str) -> None:
        super().__init__()
        self.allowed_host = allowed_host

    def redirect_request(self, request, response, code, message, headers, new_url):
        parsed = urlsplit(new_url)
        if parsed.scheme != "https" or parsed.hostname != self.allowed_host:
            return None
        return super().redirect_request(request, response, code, message, headers, new_url)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.page_text: list[str] = []
        self._row_depth = 0
        self._row_parts: list[str] = []
        self._in_row = False
        self._anchor_index: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag.lower() == "tr":
            self._row_depth += 1
            if self._row_depth == 1:
                self._in_row = True
                self._row_parts = []
        elif tag.lower() == "a" and attributes.get("href"):
            self.links.append((attributes["href"] or "", ""))
            self._anchor_index = len(self.links) - 1
        if self._in_row:
            for name in ("datetime", "data-date", "title"):
                value = attributes.get(name)
                if value:
                    self._row_parts.append(value)
        if tag.lower() == "meta":
            name = (attributes.get("name") or attributes.get("property") or "").lower()
            content = attributes.get("content") or ""
            if name in {"last-modified", "last_updated", "last-updated"} and content:
                self.page_text.append(f"Last updated: {content}")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a":
            self._anchor_index = None
        if tag.lower() == "tr" and self._row_depth:
            self._row_depth -= 1
            if self._row_depth == 0:
                value = normalize_text(" ".join(self._row_parts))
                if value:
                    self.rows.append(value)
                self._in_row = False

    def handle_data(self, data: str) -> None:
        text = normalize_text(data)
        if not text:
            return
        self.page_text.append(text)
        if self._in_row:
            self._row_parts.append(text)
        if self._anchor_index is not None:
            href, label = self.links[self._anchor_index]
            self.links[self._anchor_index] = (href, normalize_text(f"{label} {text}"))


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def parse_page(contents: bytes) -> PageParser:
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = contents.decode("windows-1252")
    parser = PageParser()
    parser.feed(text)
    parser.close()
    return parser


def read_bounds(path: Path) -> tuple[date, date]:
    coverage = read_schedule_bounds(path)
    return coverage.fred_realtime_start, coverage.fred_realtime_end


def read_schedule_bounds(path: Path) -> ScheduleBounds:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        bounds = manifest["bounds"]["realtime"]
        start = date.fromisoformat(bounds["start"])
        end = date.fromisoformat(bounds["end"])
        latest_trade = date.fromisoformat(manifest["bounds"]["latest_entry"])
        if (
            start.isoformat() != bounds["start"]
            or end.isoformat() != bounds["end"]
            or latest_trade.isoformat() != manifest["bounds"]["latest_entry"]
            or start > end
            or end != latest_trade - timedelta(days=1)
        ):
            raise ValueError
        return ScheduleBounds(
            start, end, latest_trade,
            max(end, latest_trade + timedelta(days=1)),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise DownloadError(
            "Expected a verified FRED manifest with valid realtime and latest_entry dates."
        ) from None


def parse_date(value: str) -> tuple[date, str] | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(value)
        if not match:
            continue
        groups = match.groupdict()
        try:
            month = (
                int(groups["month"])
                if groups.get("month")
                else MONTHS[groups["month_name"].lower().rstrip(".")]
            )
            parsed = date(int(groups["year"]), month, int(groups["day"]))
        except (KeyError, TypeError, ValueError):
            continue
        return parsed, match.group(0)
    return None


def page_updated_date(page_text: str) -> date | None:
    for match in UPDATED_PATTERN.finditer(page_text):
        parsed = parse_date(match.group(1))
        if parsed:
            return parsed[0]
    return None


def parse_time(value: str) -> tuple[str | None, str | None]:
    match = TIME_PATTERN.search(value)
    if not match:
        return None, None
    time_value = normalize_text(match.group("time"))
    zone = normalize_text(match.group("zone") or "") or None
    return time_value, zone


def is_relevant(row: str, source: Source) -> bool:
    lowered = row.lower()
    return any(term in lowered for term in source.terms)


def extract_events(
    source: Source,
    url: str,
    contents: bytes,
    updated_date: date | None,
    downloaded_at: str,
    source_file: str,
    source_sha256: str,
    start: date,
    end: date,
) -> list[dict[str, str | None]]:
    page = parse_page(contents)
    updated = updated_date if updated_date is not None else page_updated_date(
        " ".join(page.page_text)
    )
    events = []
    for row in page.rows:
        if not is_relevant(row, source):
            continue
        parsed = parse_date(row)
        if not parsed:
            continue
        scheduled, date_text = parsed
        if not start <= scheduled <= end:
            continue
        time_value, zone = parse_time(row)
        events.append(
            {
                "event_type": source.event_type,
                "scheduled_date": scheduled.isoformat(),
                "scheduled_date_text": date_text,
                "scheduled_time": time_value,
                "time_zone": zone,
                "source_url": url,
                "page_updated_date": updated.isoformat() if updated else None,
                "downloaded_at_utc": downloaded_at,
                "source_file": source_file,
                "source_sha256": source_sha256,
                "schedule_text": row,
            }
        )
    return events


def schedule_known_by_entry(page_updated: date | None, entry_utc_date: date) -> bool | None:
    """Return unknown unless the page demonstrably predates the UTC entry day."""
    if page_updated is None or page_updated >= entry_utc_date:
        return None
    return True


def archive_links(source: Source, page: PageParser, start: date, end: date, base_url: str) -> list[str]:
    years = set(range(start.year, end.year + 1))
    candidates = set()
    for href, label in page.links:
        absolute = urljoin(base_url, href)
        parsed = urlsplit(absolute)
        if parsed.scheme != "https" or parsed.hostname != source.host:
            continue
        searchable = f"{parsed.path} {parsed.query} {label}".lower()
        if not any(term in searchable for term in ("calendar", "schedule", "meeting", "cpi", "empsit", "mpc")):
            continue
        found_years = {int(value) for value in re.findall(r"20\d{2}", searchable)}
        if parsed.path.lower().endswith((".pdf", ".xlsx", ".docx")):
            continue
        if found_years and found_years.intersection(years) and absolute != base_url:
            candidates.add(absolute)
    return sorted(candidates)


def fetch_page(opener, source: Source, url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with opener.open(request, timeout=45) as response:
            final_url = response.geturl()
            parsed = urlsplit(final_url)
            if parsed.scheme != "https" or parsed.hostname != source.host:
                raise DownloadError("Official source redirected outside its HTTPS host.")
            contents = response.read(MAX_PAGE_BYTES + 1)
    except HTTPError as error:
        error.close()
        raise DownloadError(f"Official schedule request failed (HTTP {error.code}).") from None
    except (URLError, OSError, TimeoutError):
        raise DownloadError("Official schedule request failed or timed out.") from None
    if len(contents) > MAX_PAGE_BYTES:
        raise DownloadError("Official schedule page exceeded the size limit.")
    if not contents:
        raise DownloadError("Official schedule page was empty.")
    return contents


def safe_filename(source_key: str, url: str) -> str:
    parsed = urlsplit(url)
    tail = Path(parsed.path).name or source_key
    tail = re.sub(r"[^A-Za-z0-9._-]+", "_", tail)[:60]
    suffix = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"{source_key}_{tail}_{suffix}.html"


def download(manifest_path: Path, out: Path) -> None:
    coverage = read_schedule_bounds(manifest_path)
    start = coverage.fred_realtime_start
    end = coverage.schedule_end
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise DownloadError("Output directory must be new or empty.")
    out.mkdir(parents=True, exist_ok=True)
    sources_dir = out / "sources"
    sources_dir.mkdir(exist_ok=True)
    events: list[dict[str, str | None]] = []
    page_records = []
    opener_by_host = {
        source.host: build_opener(ProxyHandler({}), SafeRedirect(source.host))
        for source in SOURCES
    }

    for source in SOURCES:
        queue = [source.url]
        seen: set[str] = set()
        while queue:
            url = queue.pop(0)
            if url in seen:
                continue
            if len(page_records) >= MAX_PAGES:
                raise DownloadError("Archive discovery exceeded the page limit.")
            seen.add(url)
            contents = fetch_page(opener_by_host[source.host], source, url)
            downloaded_at = datetime.now(timezone.utc).isoformat()
            source_file = safe_filename(source.key, url)
            digest = hashlib.sha256(contents).hexdigest()
            local_path = sources_dir / source_file
            if local_path.exists():
                raise DownloadError("Source-page filename collision.")
            local_path.write_bytes(contents)
            page = parse_page(contents)
            updated = page_updated_date(" ".join(page.page_text))
            page_records.append(
                {
                    "source_key": source.key,
                    "event_type": source.event_type,
                    "source_url": url,
                    "downloaded_at_utc": downloaded_at,
                    "page_updated_date": updated.isoformat() if updated else None,
                    "file": f"sources/{source_file}",
                    "sha256": digest,
                }
            )
            events.extend(
                extract_events(
                    source, url, contents, updated, downloaded_at,
                    f"sources/{source_file}", digest, start, end,
                )
            )
            queue.extend(
                link for link in archive_links(source, page, start, end, url)
                if link not in seen and link not in queue
            )

    events.sort(key=lambda event: (
        event["event_type"] or "",
        event["scheduled_date"] or "",
        event["source_url"] or "",
    ))
    event_path = out / "release_schedule_events.csv"
    with event_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(events)
    manifest = {
        "fred_realtime_bounds": {
            "start": coverage.fred_realtime_start.isoformat(),
            "end": coverage.fred_realtime_end.isoformat(),
        },
        "schedule_coverage": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "latest_trade_date": coverage.latest_trade_date.isoformat(),
            "forward_event_horizon_calendar_days": 1,
        },
        "bounds_source": str(manifest_path),
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_pages": page_records,
        "event_count": len(events),
        "events_file": {
            "file": event_path.name,
            "sha256": hashlib.sha256(event_path.read_bytes()).hexdigest(),
        },
        "eligibility_policy": (
            "A schedule event is eligible as known at an entry only when its official "
            "page has a publication/last-updated date strictly before the UTC entry date. "
            "Missing metadata or same-day/later metadata is UNKNOWN. A present-day "
            "download timestamp is provenance only and never proves historical availability. "
            "No date, time, time zone, or historical page state is inferred."
        ),
        "coverage_policy": (
            "Acquisition starts at the original FRED realtime start and extends through "
            "the later of the original FRED realtime end or one calendar day after the "
            "latest UTC trade date. The original FRED realtime bounds are retained above."
        ),
    }
    (out / "release_schedule_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, required=True,
        help="FRED download manifest with bounds.realtime.start/end.",
    )
    parser.add_argument("--out", type=Path, required=True, help="New or empty output directory.")
    args = parser.parse_args(argv)
    try:
        download(args.manifest, args.out)
    except DownloadError as error:
        print(error, file=sys.stderr)
        return 1
    except OSError:
        print("Could not write official schedule artifacts.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
