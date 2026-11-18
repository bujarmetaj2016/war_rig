"""Pure REV4 Core-5 classification and comparison engine.

The module deliberately performs no I/O except in the explicit ALFRED CSV
loader. It does not fetch data, inspect trade outcomes, or alter fixed rules.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import random
import statistics
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


UTC = timezone.utc
MIN_BUCKET_N = 20
BASELINE_N = 250
BOOTSTRAP_REPLICATES = 2_000
EVENT_TYPES = ("FOMC", "ECB", "BOE", "US_CPI", "US_NFP")
EVENT_HOSTS = {
    "FOMC": "federalreserve.gov",
    "ECB": "ecb.europa.eu",
    "BOE": "bankofengland.co.uk",
    "US_CPI": "bls.gov",
    "US_NFP": "bls.gov",
}


@dataclass(frozen=True)
class TestSpec:
    test_id: str
    instrument: str
    macro: str
    preregistration: str
    kind: str


# REV4's 19-row analyzer matrix, identifiers and order kept intact.
LEGACY_TESTS = (
    TestSpec("EURUSD_USD_BASKET_EX_EUR", "EURUSD", "USD strength basket excluding EUR", "PRIMARY", "usd"),
    TestSpec("EURUSD_VIX_RISK_OFF", "EURUSD", "VIX risk-off", "EXPLORATORY", "risk_off"),
    TestSpec("EURUSD_BRENT_SPOT", "EURUSD", "Brent spot oil", "EXPLORATORY", "up"),
    TestSpec("EURUSD_DGS2", "EURUSD", "US 2-year yield (DGS2)", "EXPLORATORY", "up"),
    TestSpec("EURUSD_SCHEDULED_EVENT", "EURUSD", "Scheduled-event proximity", "EXPLORATORY", "event"),
    TestSpec("GBPUSD_USD_BASKET_EX_GBP", "GBPUSD", "USD strength basket excluding GBP", "PRIMARY", "usd"),
    TestSpec("GBPUSD_VIX_RISK_OFF", "GBPUSD", "VIX risk-off", "EXPLORATORY", "risk_off"),
    TestSpec("GBPUSD_BRENT_SPOT", "GBPUSD", "Brent spot oil", "EXPLORATORY", "up"),
    TestSpec("GBPUSD_DGS2", "GBPUSD", "US 2-year yield (DGS2)", "EXPLORATORY", "up"),
    TestSpec("GBPUSD_SCHEDULED_EVENT", "GBPUSD", "Scheduled-event proximity", "EXPLORATORY", "event"),
    TestSpec("GOLD_DFII10", "GOLD", "US 10-year real yield (DFII10)", "EXPLORATORY", "up"),
    TestSpec("GOLD_USD_BASKET", "GOLD", "USD strength basket", "EXPLORATORY", "usd"),
    TestSpec("GOLD_VIX_RISK_OFF", "GOLD", "VIX risk-off", "EXPLORATORY", "risk_off"),
    TestSpec("GOLD_DGS2", "GOLD", "US 2-year yield (DGS2)", "EXPLORATORY", "up"),
    TestSpec("SP500_VIX_TERM_RISK_OFF", "SP500", "VIX / VIX3M risk-off", "EXPLORATORY", "risk_off"),
    TestSpec("SP500_HY_SPREAD", "SP500", "High-yield spread (BAMLH0A0HYM2)", "EXPLORATORY", "up"),
    TestSpec("DAX_VIX_RISK_OFF", "DAX", "VIX risk-off", "EXPLORATORY", "risk_off"),
    TestSpec("DAX_EURUSD_10D", "DAX", "EURUSD 10-day change", "EXPLORATORY", "up"),
    TestSpec("DAX_BRENT_SPOT", "DAX", "Brent spot oil", "EXPLORATORY", "up"),
)

# REV4 requires event-proximity tests for all five instruments. The source
# matrix accidentally omitted these three rows; append them rather than
# renumbering or reordering any legacy identifiers.
MISSING_REV4_EVENT_TESTS = (
    TestSpec("GOLD_SCHEDULED_EVENT", "GOLD", "Scheduled-event proximity", "EXPLORATORY", "event"),
    TestSpec("SP500_SCHEDULED_EVENT", "SP500", "Scheduled-event proximity", "EXPLORATORY", "event"),
    TestSpec("DAX_SCHEDULED_EVENT", "DAX", "Scheduled-event proximity", "EXPLORATORY", "event"),
)
ALL_TESTS = LEGACY_TESTS + MISSING_REV4_EVENT_TESTS
MATRIX_DISCREPANCY = (
    "The analyzer's legacy matrix has 19 tests but only EURUSD/GBPUSD event rows. "
    "REV4 requires event tests for all five instruments; GOLD, SP500, and DAX "
    "event rows are explicitly appended, yielding 22 effective test definitions."
)
TESTS_BY_ID = {spec.test_id: spec for spec in ALL_TESTS}


def _require_utc(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{label} must be explicitly expressed in UTC")
    return value.astimezone(UTC)


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


@dataclass(frozen=True)
class PriceProvenance:
    source: str
    source_url: str
    downloaded_at_utc: datetime
    close_convention: str
    sha256: str

    def __post_init__(self) -> None:
        _require_utc(self.downloaded_at_utc, "downloaded_at_utc")
        if not self.source or not self.close_convention:
            raise ValueError("price source and daily close convention are required")
        if urlparse(self.source_url).scheme != "https" or not _valid_sha256(self.sha256):
            raise ValueError("price provenance requires an HTTPS URL and SHA-256")


@dataclass(frozen=True)
class PriceBar:
    close_time_utc: datetime
    close: float
    complete: bool = True

    def __post_init__(self) -> None:
        _require_utc(self.close_time_utc, "price close timestamp")
        if not math.isfinite(self.close) or self.close <= 0:
            raise ValueError("price close must be finite and positive")


@dataclass(frozen=True)
class PriceSeries:
    name: str
    bars: tuple[PriceBar, ...]
    provenance: PriceProvenance
    expected_dates: tuple[date, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("price series name is required")
        if tuple(sorted(self.expected_dates)) != self.expected_dates:
            raise ValueError("expected price dates must be sorted")
        if len(set(self.expected_dates)) != len(self.expected_dates):
            raise ValueError("expected price dates must be unique")

    def completed_before(self, entry_time: datetime) -> tuple[tuple[date, float], ...]:
        entry = _require_utc(entry_time, "entry time")
        if not self.expected_dates:
            raise UnknownData(f"{self.name}: verified trading-session calendar is required")
        eligible = [bar for bar in self.bars if bar.close_time_utc < entry]
        stamps = [bar.close_time_utc for bar in eligible]
        if len(stamps) != len(set(stamps)):
            raise UnknownData(f"{self.name}: duplicate price-bar timestamps")
        complete = [bar for bar in eligible if bar.complete]
        if not complete:
            raise UnknownData(f"{self.name}: no completed bar before entry")
        latest_date = max(bar.close_time_utc.date() for bar in complete)
        if self.expected_dates:
            expected = {day for day in self.expected_dates if day <= latest_date}
            actual = {
                bar.close_time_utc.date()
                for bar in complete
                if bar.close_time_utc.date() <= latest_date
            }
            if expected != actual:
                raise UnknownData(f"{self.name}: missing or incomplete expected price bar")
        return tuple(
            (bar.close_time_utc.date(), bar.close)
            for bar in sorted(complete, key=lambda item: item.close_time_utc)
        )


@dataclass(frozen=True)
class AlfredVintage:
    observation_date: date
    realtime_start: date
    realtime_end: date
    value: float | None

    def __post_init__(self) -> None:
        if self.realtime_start > self.realtime_end:
            raise ValueError("invalid ALFRED real-time interval")
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("ALFRED values must be finite or missing")


@dataclass(frozen=True)
class AlfredProvenance:
    series_id: str
    source_urls: tuple[str, ...]
    downloaded_at_utc: datetime
    sha256: str

    def __post_init__(self) -> None:
        _require_utc(self.downloaded_at_utc, "downloaded_at_utc")
        if not self.series_id or not self.source_urls:
            raise ValueError("ALFRED series id and source URLs are required")
        if any(
            urlparse(url).scheme != "https"
            or urlparse(url).hostname != "api.stlouisfed.org"
            or "/fred/" not in urlparse(url).path
            for url in self.source_urls
        ):
            raise ValueError("ALFRED provenance must point to official FRED API URLs")
        if not _valid_sha256(self.sha256):
            raise ValueError("ALFRED provenance requires SHA-256")


@dataclass(frozen=True)
class SeriesValue:
    observation_date: date
    value: float | None


class UnknownData(ValueError):
    """Raised internally when inputs cannot support a point-in-time result."""


@dataclass(frozen=True)
class AlfredSeries:
    provenance: AlfredProvenance
    vintages: tuple[AlfredVintage, ...]
    expected_dates: tuple[date, ...] = ()

    @classmethod
    def from_csv(
        cls,
        path: Path,
        *,
        expected_sha256: str,
        series_id: str,
        source_urls: Sequence[str],
        downloaded_at_utc: datetime,
        expected_dates: Sequence[date] = (),
    ) -> "AlfredSeries":
        """Load the downloader's date/realtime_start/realtime_end/value CSV."""
        return cls.from_csv_bytes(
            path.read_bytes(),
            expected_sha256=expected_sha256,
            series_id=series_id,
            source_urls=source_urls,
            downloaded_at_utc=downloaded_at_utc,
            expected_dates=expected_dates,
        )

    @classmethod
    def from_csv_bytes(
        cls,
        contents: bytes,
        *,
        expected_sha256: str,
        series_id: str,
        source_urls: Sequence[str],
        downloaded_at_utc: datetime,
        expected_dates: Sequence[date] = (),
    ) -> "AlfredSeries":
        """Parse and hash-check synthetic or in-memory ALFRED CSV contents."""
        digest = hashlib.sha256(contents).hexdigest()
        if digest != expected_sha256:
            raise ValueError("ALFRED CSV SHA-256 does not match the pinned manifest")
        records: list[AlfredVintage] = []
        with io.StringIO(contents.decode("utf-8-sig"), newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ["date", "realtime_start", "realtime_end", "value"]:
                raise ValueError("unexpected ALFRED CSV schema")
            for row in reader:
                try:
                    raw = row["value"].strip()
                    records.append(
                        AlfredVintage(
                            date.fromisoformat(row["date"]),
                            date.fromisoformat(row["realtime_start"]),
                            date.fromisoformat(row["realtime_end"]),
                            None if raw in ("", ".") else float(raw),
                        )
                    )
                except (AttributeError, TypeError, ValueError):
                    raise ValueError("invalid ALFRED vintage row") from None
        provenance = AlfredProvenance(
            series_id, tuple(source_urls), downloaded_at_utc, digest
        )
        return cls(provenance, tuple(records), tuple(expected_dates))

    @classmethod
    def from_manifest(
        cls,
        root: Path,
        series_id: str,
        *,
        manifest_name: str = "fred_download_manifest.json",
        expected_dates: Sequence[date] = (),
    ) -> "AlfredSeries":
        """Load one series only when its downloader manifest pins the CSV."""
        manifest = json.loads((root / manifest_name).read_text(encoding="utf-8"))
        row = next(item for item in manifest["series"] if item["series_id"] == series_id)
        path = root / row["file"]
        return cls.from_csv(
            path,
            expected_sha256=row["sha256"],
            series_id=series_id,
            source_urls=(row["vintage_dates_url"], *row["observation_urls"]),
            downloaded_at_utc=datetime.fromisoformat(row["downloaded_at_utc"]),
            expected_dates=expected_dates,
        )

    def snapshot(self, entry_time: datetime) -> tuple[SeriesValue, ...]:
        """Return point-in-time observations using the UTC day before entry."""
        entry_date = _require_utc(entry_time, "entry time").date()
        as_of = entry_date - timedelta(days=1)
        by_observation: dict[date, list[AlfredVintage]] = {}
        for vintage in self.vintages:
            if vintage.observation_date < entry_date:
                by_observation.setdefault(vintage.observation_date, []).append(vintage)
        selected: list[SeriesValue] = []
        for observation_date, revisions in sorted(by_observation.items()):
            active = [
                row for row in revisions
                if row.realtime_start <= as_of <= row.realtime_end
            ]
            if not active:
                continue
            latest_start = max(row.realtime_start for row in active)
            latest = [row for row in active if row.realtime_start == latest_start]
            values = {row.value for row in latest}
            if len(values) != 1:
                raise UnknownData(
                    f"{self.provenance.series_id}: conflicting vintages for {observation_date}"
                )
            selected.append(SeriesValue(observation_date, latest[0].value))
        if self.expected_dates and selected:
            first, last = selected[0].observation_date, selected[-1].observation_date
            expected = {
                day for day in self.expected_dates
                if first <= day <= last and day < entry_date
            }
            observed = {
                row.observation_date
                for row in selected
                if first <= row.observation_date <= last
            }
            missing = any(row.value is None for row in selected)
            if expected != observed or missing:
                raise UnknownData(
                    f"{self.provenance.series_id}: missing expected ALFRED observation"
                )
        return tuple(selected)


@dataclass(frozen=True)
class ScheduleProvenance:
    event_type: str
    source_url: str
    published_or_updated_date: date | None
    downloaded_at_utc: datetime
    sha256: str

    def __post_init__(self) -> None:
        _require_utc(self.downloaded_at_utc, "downloaded_at_utc")
        host = urlparse(self.source_url).hostname or ""
        official_host = EVENT_HOSTS.get(self.event_type, "")
        if self.event_type not in EVENT_HOSTS or not (
            host == official_host or host.endswith("." + official_host)
        ):
            raise ValueError("event calendar provenance is not from its official source")
        if urlparse(self.source_url).scheme != "https" or not _valid_sha256(self.sha256):
            raise ValueError("event provenance requires HTTPS and SHA-256")


@dataclass(frozen=True)
class ScheduledEvent:
    event_type: str
    scheduled_local_date: date
    scheduled_local_time: time
    timezone_name: str

    def scheduled_at_utc(self) -> datetime:
        try:
            zone = ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError:
            raise UnknownData(f"unknown event timezone: {self.timezone_name}") from None
        local = datetime.combine(self.scheduled_local_date, self.scheduled_local_time)
        if local.tzinfo is not None:
            raise UnknownData("event local time must not contain a second timezone")
        return local.replace(tzinfo=zone).astimezone(UTC)


@dataclass(frozen=True)
class OfficialCalendar:
    events: tuple[ScheduledEvent, ...]
    provenance_by_type: Mapping[str, ScheduleProvenance]
    coverage_start: date
    coverage_end: date

    def __post_init__(self) -> None:
        if self.coverage_start > self.coverage_end:
            raise ValueError("invalid event-calendar coverage interval")
        if set(self.provenance_by_type) != set(EVENT_TYPES):
            raise ValueError("all five official event schedules must be represented")
        for event in self.events:
            if event.event_type not in EVENT_HOSTS:
                raise ValueError(f"unsupported event type: {event.event_type}")
            if self.provenance_by_type[event.event_type].event_type != event.event_type:
                raise ValueError("event provenance type mismatch")

    def event_window(self, entry_time: datetime) -> str:
        """Return EVENT_WINDOW, NO_EVENT, or UNKNOWN using as-known schedule data."""
        entry = _require_utc(entry_time, "entry time")
        if not self.coverage_start <= entry.date() <= self.coverage_end:
            raise UnknownData("entry is outside official schedule coverage")
        for event_type in EVENT_TYPES:
            known_on = self.provenance_by_type[event_type].published_or_updated_date
            if known_on is None or known_on >= entry.date():
                raise UnknownData(f"{event_type} schedule was not verified as known before entry")
        for event in self.events:
            scheduled = event.scheduled_at_utc()
            delta = scheduled - entry
            if timedelta(0) < delta <= timedelta(hours=24):
                return "EVENT_WINDOW"
        return "NO_EVENT"


@dataclass(frozen=True)
class Reading:
    code: str
    s: float | None = None
    sigma: float | None = None
    reason: str | None = None

    @classmethod
    def unknown(cls, reason: str) -> "Reading":
        return cls("UNKNOWN", reason=reason)

    @classmethod
    def not_tested(cls, reason: str = "no REV4 rule is defined") -> "Reading":
        return cls("NOT_TESTED", reason=reason)


@dataclass(frozen=True)
class Trade:
    trade_id: str
    instrument: str
    direction: str
    entry_time_utc: datetime
    outcome: str
    r_multiple: float

    def __post_init__(self) -> None:
        _require_utc(self.entry_time_utc, "entry time")
        if self.direction not in ("BUY", "SELL"):
            raise ValueError("trade direction must be BUY or SELL")
        if self.outcome not in ("WIN", "LOSS"):
            raise ValueError("only strict WIN/LOSS outcomes may be tested")
        if not math.isfinite(self.r_multiple):
            raise ValueError("R outcome must be finite")


@dataclass(frozen=True)
class ClassifiedTrade:
    trade: Trade
    classification: str
    reading: Reading


@dataclass(frozen=True)
class BucketStats:
    n: int
    wins: int
    win_rate: float | None
    mean_r: float | None
    total_r: float
    mean_r_ci95: tuple[float, float] | None


@dataclass(frozen=True)
class Comparison:
    test_id: str
    status: str
    buckets: Mapping[str, BucketStats]
    unknown_n: int
    not_tested_n: int
    removed_trade_fraction: float | None
    removed_total_r_fraction: float | None
    gate_recommended: bool
    gate_confirmed: bool
    multiple_testing_statement: str
    family: str | None = None


def _checked_points(
    values: Iterable[SeriesValue | tuple[date, float | None]],
    *,
    label: str,
) -> tuple[SeriesValue, ...]:
    points = tuple(
        item if isinstance(item, SeriesValue) else SeriesValue(item[0], item[1])
        for item in values
    )
    dates = [point.observation_date for point in points]
    if dates != sorted(dates):
        raise UnknownData(f"{label}: observations are not sorted")
    if len(set(dates)) != len(dates):
        raise UnknownData(f"{label}: duplicate observations")
    return points


def momentum_reading(
    values: Iterable[SeriesValue | tuple[date, float | None]],
    *,
    entry_date_utc: date,
    price_series: bool,
    label: str,
    expected_dates: Sequence[date] = (),
    alfred_price: bool = False,
) -> Reading:
    """Compute REV4 S and trailing 250-observation sample standard deviation."""
    try:
        points = _checked_points(values, label=label)
        points = tuple(point for point in points if point.observation_date < entry_date_utc)
        if price_series and not alfred_price:
            if not expected_dates:
                return Reading.unknown(
                    f"{label}: verified trading-session calendar is required"
                )
            if points:
                first, last = points[0].observation_date, points[-1].observation_date
                expected = {
                    day for day in expected_dates if first <= day <= last
                }
                observed = {point.observation_date for point in points}
                if expected != observed or any(point.value is None for point in points):
                    return Reading.unknown(f"{label}: missing expected daily price close")
        valid = tuple(point for point in points if point.value is not None)
        if len(valid) < BASELINE_N + 10:
            return Reading.unknown(
                f"{label}: fewer than 250 valid S observations with 10-observation lookback"
            )
        for point in valid:
            if not math.isfinite(point.value):
                return Reading.unknown(f"{label}: non-finite observation")
            if price_series and point.value <= 0:
                return Reading.unknown(f"{label}: price observations must be positive")
        changes: list[float] = []
        for index in range(10, len(valid)):
            window = valid[index - 10 : index + 1]
            if price_series:
                change = sum(
                    math.log(window[offset + 1].value / window[offset].value)
                    for offset in range(10)
                )
            else:
                change = valid[index].value - valid[index - 10].value
            changes.append(change)
        if len(changes) < BASELINE_N:
            return Reading.unknown(f"{label}: fewer than 250 valid S observations")
        recent = changes[-BASELINE_N:]
        current_s = recent[-1]
        sigma = statistics.stdev(recent)
        if current_s > 0.5 * sigma:
            code = "UP"
        elif current_s < -0.5 * sigma:
            code = "DOWN"
        else:
            code = "NEUTRAL"
        return Reading(code, current_s, sigma)
    except (UnknownData, OverflowError, ZeroDivisionError, ValueError) as error:
        return Reading.unknown(str(error))


def log_return_momentum_reading(
    daily_returns: Iterable[tuple[date, float]],
    *,
    entry_date_utc: date,
    label: str,
) -> Reading:
    """Compute 10-session S directly from daily log returns (no synthetic level)."""
    try:
        points = _checked_points(
            (SeriesValue(day, value) for day, value in daily_returns), label=label
        )
        points = tuple(point for point in points if point.observation_date < entry_date_utc)
        if any(point.value is None or not math.isfinite(point.value) for point in points):
            return Reading.unknown(f"{label}: missing or non-finite daily return")
        # A 10-return S series needs 259 daily returns for 250 observations.
        if len(points) < BASELINE_N + 9:
            return Reading.unknown(f"{label}: fewer than 250 valid S observations")
        changes = [
            sum(point.value for point in points[index - 9 : index + 1])
            for index in range(9, len(points))
        ]
        recent = changes[-BASELINE_N:]
        current_s = recent[-1]
        sigma = statistics.stdev(recent)
        code = (
            "UP" if current_s > 0.5 * sigma
            else "DOWN" if current_s < -0.5 * sigma
            else "NEUTRAL"
        )
        return Reading(code, current_s, sigma)
    except (UnknownData, OverflowError, ValueError) as error:
        return Reading.unknown(str(error))


def price_momentum_reading(
    series: PriceSeries, entry_time_utc: datetime, *, invert_quote: bool = False
) -> Reading:
    try:
        points = series.completed_before(entry_time_utc)
        if invert_quote:
            points = tuple((day, 1.0 / value) for day, value in points)
        return momentum_reading(
            points,
            entry_date_utc=_require_utc(entry_time_utc, "entry time").date()
            + timedelta(days=1),
            price_series=True,
            label=series.name,
            expected_dates=series.expected_dates,
        )
    except UnknownData as error:
        return Reading.unknown(str(error))


def alfred_momentum_reading(
    series: AlfredSeries, entry_time_utc: datetime, *, price_series: bool = False
) -> Reading:
    try:
        points = series.snapshot(entry_time_utc)
        return momentum_reading(
            ((point.observation_date, point.value) for point in points),
            entry_date_utc=_require_utc(entry_time_utc, "entry time").date(),
            price_series=price_series,
            label=series.provenance.series_id,
            expected_dates=series.expected_dates,
            alfred_price=price_series,
        )
    except UnknownData as error:
        return Reading.unknown(str(error))


USD_QUOTE_PAIRS = (
    ("JPY", "USDJPY", False),
    ("GBP", "GBPUSD", True),
    ("CAD", "USDCAD", False),
    ("CHF", "USDCHF", False),
    ("AUD", "AUDUSD", True),
    ("EUR", "EURUSD", True),
)


@dataclass(frozen=True)
class AlfredCloseSeries:
    """Expose previously published numeric ALFRED observations as completed closes."""

    name: str
    series: AlfredSeries

    def completed_before(self, entry_time: datetime) -> tuple[tuple[date, float], ...]:
        closes = tuple(
            (row.observation_date, row.value)
            for row in self.series.snapshot(entry_time) if row.value is not None
        )
        if not closes or any(value <= 0 for _, value in closes):
            raise UnknownData(f"{self.name}: no usable ALFRED close history")
        return closes


def usd_basket_reading(
    series_by_pair: Mapping[str, PriceSeries | AlfredCloseSeries],
    entry_time_utc: datetime,
    *,
    instrument: str,
) -> Reading:
    """Equal-weight the six specified USD legs, excluding EUR/GBP for FX trades."""
    excluded = {"EURUSD": "EUR", "GBPUSD": "GBP"}.get(instrument)
    legs = [leg for leg in USD_QUOTE_PAIRS if leg[0] != excluded]
    try:
        histories = []
        for currency, pair, inverted in legs:
            if pair not in series_by_pair:
                raise UnknownData(f"USD basket missing {pair}")
            series = series_by_pair[pair]
            bars = series.completed_before(entry_time_utc)
            if inverted:
                bars = tuple((day, 1.0 / value) for day, value in bars)
            histories.append((currency, bars))
        calendars = [tuple(day for day, _ in rows) for _, rows in histories]
        if any(calendar != calendars[0] for calendar in calendars[1:]):
            raise UnknownData("USD basket legs have mismatched trading calendars")
        basket_returns: list[tuple[date, float]] = []
        for index, day in enumerate(calendars[0]):
            if index == 0:
                continue
            daily_returns = [
                math.log(rows[index][1] / rows[index - 1][1])
                for _, rows in histories
            ]
            basket_returns.append((day, sum(daily_returns) / len(daily_returns)))
        return log_return_momentum_reading(
            basket_returns,
            entry_date_utc=_require_utc(entry_time_utc, "entry time").date()
            + timedelta(days=1),
            label=f"USD basket excluding {excluded}" if excluded else "USD basket",
        )
    except (UnknownData, OverflowError, ValueError, ZeroDivisionError) as error:
        return Reading.unknown(str(error))


def risk_off_reading(
    vix: PriceSeries | AlfredCloseSeries,
    vix3m: PriceSeries | AlfredCloseSeries | None,
    entry_time_utc: datetime,
) -> Reading:
    """REV4 binary risk-off condition: VIX/VIX3M > 1 OR VIX > 1.25×median20."""
    try:
        # Require the fixed 250-observation baseline even though the regime
        # classification itself uses the 20-day median and term ratio.
        baseline = (
            alfred_momentum_reading(vix.series, entry_time_utc, price_series=True)
            if isinstance(vix, AlfredCloseSeries) else price_momentum_reading(vix, entry_time_utc)
        )
        if baseline.code == "UNKNOWN":
            raise UnknownData(baseline.reason or "insufficient VIX baseline")
        vix_rows = vix.completed_before(entry_time_utc)
        if len(vix_rows) < 20:
            raise UnknownData("VIX has fewer than 20 completed observations")
        vix_date, vix_now = vix_rows[-1]
        term_now = None
        if vix3m is not None:
            try:
                term_rows = vix3m.completed_before(entry_time_utc)
                term_by_date = dict(term_rows)
                term_now = term_by_date.get(vix_date)
            except UnknownData:
                # The median clause is independent under REV4's OR rule.
                term_now = None
        median = statistics.median(value for _, value in vix_rows[-20:])
        median_trigger = vix_now > 1.25 * median
        term_trigger = term_now is not None and term_now > 0 and vix_now / term_now > 1.0
        if median_trigger or term_trigger:
            return Reading("RISK_OFF")
        if term_now is None or term_now <= 0:
            raise UnknownData("VIX/VIX3M ratio unavailable and median rule is not triggered")
        return Reading("NOT_RISK_OFF")
    except (UnknownData, ValueError, ZeroDivisionError) as error:
        return Reading.unknown(str(error))


def event_reading(calendar: OfficialCalendar, entry_time_utc: datetime) -> Reading:
    try:
        return Reading(calendar.event_window(entry_time_utc))
    except UnknownData as error:
        return Reading.unknown(str(error))


def classify(spec: TestSpec, trade: Trade, reading: Reading) -> ClassifiedTrade:
    """Map a fixed macro state and direction to WITH/AGAINST/NEUTRAL."""
    if spec.instrument != trade.instrument:
        raise ValueError(f"{spec.test_id} does not apply to {trade.instrument}")
    if reading.code in ("UNKNOWN", "NOT_TESTED"):
        return ClassifiedTrade(trade, reading.code, reading)
    if spec.kind == "event":
        if reading.code == "EVENT_WINDOW":
            bucket = "AGAINST"
        elif reading.code == "NO_EVENT":
            bucket = "WITH"
        else:
            return ClassifiedTrade(trade, "UNKNOWN", Reading.unknown("invalid event state"))
        return ClassifiedTrade(trade, bucket, reading)
    if reading.code == "NEUTRAL":
        return ClassifiedTrade(trade, "NEUTRAL", reading)

    if spec.kind == "risk_off":
        if reading.code not in ("RISK_OFF", "NOT_RISK_OFF"):
            return ClassifiedTrade(trade, "UNKNOWN", Reading.unknown("invalid risk state"))
        gold_safe_haven = spec.instrument == "GOLD"
        favorable_risk_off = (trade.direction == "BUY") == gold_safe_haven
        favorable = reading.code == "RISK_OFF" if favorable_risk_off else reading.code != "RISK_OFF"
        return ClassifiedTrade(trade, "WITH" if favorable else "AGAINST", reading)

    if spec.kind in ("usd", "up"):
        if reading.code not in ("UP", "DOWN"):
            return ClassifiedTrade(trade, "UNKNOWN", Reading.unknown("invalid directional state"))
        # Stronger USD opposes EURUSD/GBPUSD BUYs and GOLD BUYs; rising
        # yields/spreads/oil/Euro oppose the long side specified by REV4.
        buy_is_headwind = (
            (spec.kind == "usd" and reading.code == "UP")
            or (spec.kind == "up" and reading.code == "UP")
        )
        if spec.kind == "up" and reading.code == "DOWN":
            buy_is_headwind = False
        favorable = (trade.direction == "BUY") != buy_is_headwind
        return ClassifiedTrade(trade, "WITH" if favorable else "AGAINST", reading)
    return ClassifiedTrade(trade, "UNKNOWN", Reading.unknown("unsupported test rule"))


def _percentile(sorted_values: Sequence[float], percentile: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def weekly_cluster_bootstrap_ci(
    trades: Sequence[Trade],
    *,
    seed: int,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> tuple[float, float] | None:
    """Percentile CI for mean R, resampling whole ISO calendar weeks."""
    if not trades:
        return None
    if replicates < 1:
        raise ValueError("bootstrap replicates must be positive")
    weeks: dict[tuple[int, int], list[Trade]] = {}
    for trade in trades:
        entry = _require_utc(trade.entry_time_utc, "entry time")
        iso = entry.date().isocalendar()
        weeks.setdefault((iso.year, iso.week), []).append(trade)
    keys = tuple(sorted(weeks))
    rng = random.Random(seed)
    estimates = []
    for _ in range(replicates):
        sampled: list[Trade] = []
        for _ in keys:
            sampled.extend(weeks[rng.choice(keys)])
        estimates.append(statistics.mean(item.r_multiple for item in sampled))
    estimates.sort()
    return _percentile(estimates, 0.025), _percentile(estimates, 0.975)


def _bucket_stats(trades: Sequence[Trade], *, seed: int) -> BucketStats:
    if not trades:
        return BucketStats(0, 0, None, None, 0.0, None)
    total = sum(trade.r_multiple for trade in trades)
    return BucketStats(
        n=len(trades),
        wins=sum(trade.outcome == "WIN" for trade in trades),
        win_rate=sum(trade.outcome == "WIN" for trade in trades) / len(trades),
        mean_r=statistics.mean(trade.r_multiple for trade in trades),
        total_r=total,
        mean_r_ci95=weekly_cluster_bootstrap_ci(trades, seed=seed),
    )


def compare(
    test_id: str,
    observations: Sequence[ClassifiedTrade],
    *,
    seed: int = 0,
    family: str | None = None,
) -> Comparison:
    if test_id not in TESTS_BY_ID:
        raise ValueError(f"unknown test id: {test_id}")
    spec = TESTS_BY_ID[test_id]
    if any(item.trade.instrument != spec.instrument for item in observations):
        raise ValueError(f"observations do not match {test_id}")
    buckets: dict[str, list[Trade]] = {"WITH": [], "AGAINST": [], "NEUTRAL": []}
    unknown_n = 0
    not_tested_n = 0
    for item in observations:
        if item.classification in buckets:
            buckets[item.classification].append(item.trade)
        elif item.classification == "UNKNOWN":
            unknown_n += 1
        elif item.classification == "NOT_TESTED":
            not_tested_n += 1
        else:
            raise ValueError(f"invalid classification: {item.classification}")
    stats: dict[str, BucketStats] = {}
    for bucket, rows in buckets.items():
        # Stable test/bucket-specific seeds, independent of Python's hash salt.
        digest = hashlib.sha256(f"{seed}:{test_id}:{bucket}".encode()).digest()
        bucket_seed = int.from_bytes(digest[:8], "big")
        stats[bucket] = _bucket_stats(rows, seed=bucket_seed)

    with_stats, against_stats = stats["WITH"], stats["AGAINST"]
    enough = with_stats.n >= MIN_BUCKET_N and against_stats.n >= MIN_BUCKET_N
    removed_trade_fraction = None
    removed_r_fraction = None
    overall_total = sum(
        item.trade.r_multiple
        for item in observations
        if item.classification in ("WITH", "AGAINST", "NEUTRAL")
    )
    if with_stats.n + against_stats.n + stats["NEUTRAL"].n:
        classified_n = with_stats.n + against_stats.n + stats["NEUTRAL"].n
        removed_trade_fraction = against_stats.n / classified_n
    if overall_total != 0:
        removed_r_fraction = against_stats.total_r / overall_total
    recommended = bool(
        enough
        and with_stats.mean_r is not None
        and against_stats.mean_r is not None
        and against_stats.mean_r < with_stats.mean_r
        and overall_total - against_stats.total_r > overall_total
    )
    confirmed = bool(
        recommended
        and against_stats.mean_r_ci95 is not None
        and against_stats.mean_r_ci95[1] < 0
    )
    return Comparison(
        test_id=test_id,
        status="EVALUATED" if enough else "INSUFFICIENT_SAMPLE",
        buckets=stats,
        unknown_n=unknown_n,
        not_tested_n=not_tested_n,
        removed_trade_fraction=removed_trade_fraction,
        removed_total_r_fraction=removed_r_fraction,
        gate_recommended=recommended,
        gate_confirmed=confirmed,
        multiple_testing_statement=(
            f"{len(ALL_TESTS)} instrument × macro tests are defined; with this many "
            "tests some differences will appear by chance."
        ),
        family=family,
    )


OVERLAPPING_DRIVER_FAMILY = (
    "USD strength basket",
    "US 2-year yield",
    "US 10-year real yield",
    "DXY",
)
OVERLAPPING_DRIVER_LABELS = {
    "USD strength basket excluding EUR",
    "USD strength basket excluding GBP",
    "USD strength basket",
    "US 2-year yield (DGS2)",
    "US 10-year real yield (DFII10)",
}


def overlapping_driver_agreement(
    classifications: Mapping[str, Mapping[str, str]],
) -> dict[tuple[str, str], tuple[int, int, float | None]]:
    """Pairwise exact agreement for drivers on the same known trades.

    Returns ``(shared_n, agreements, fraction)`` keyed by sorted driver names.
    """
    result: dict[tuple[str, str], tuple[int, int, float | None]] = {}
    names = sorted(classifications)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            common = [
                trade_id
                for trade_id in set(classifications[left]) & set(classifications[right])
                if classifications[left][trade_id] not in ("UNKNOWN", "NOT_TESTED")
                and classifications[right][trade_id] not in ("UNKNOWN", "NOT_TESTED")
            ]
            agreements = sum(
                classifications[left][trade_id] == classifications[right][trade_id]
                for trade_id in common
            )
            result[(left, right)] = (
                len(common),
                agreements,
                agreements / len(common) if common else None,
            )
    return result


def strongest_family_member(
    comparisons: Sequence[Comparison],
) -> tuple[str | None, bool]:
    """Apply the family rule: only its strongest member can support a gate."""
    eligible = [
        item for item in comparisons
        if item.status == "EVALUATED"
        and item.buckets["WITH"].mean_r is not None
        and item.buckets["AGAINST"].mean_r is not None
    ]
    if not eligible:
        return None, False
    strongest = max(
        eligible,
        key=lambda item: item.buckets["WITH"].mean_r - item.buckets["AGAINST"].mean_r,
    )
    return strongest.test_id, strongest.gate_recommended


def family_decisions(
    comparisons: Sequence[Comparison],
) -> dict[tuple[str, str], tuple[str | None, bool]]:
    """Resolve the strongest eligible Fed-repricing member per instrument."""
    grouped: dict[tuple[str, str], list[Comparison]] = {}
    for item in comparisons:
        spec = TESTS_BY_ID[item.test_id]
        if item.family:
            grouped.setdefault((spec.instrument, item.family), []).append(item)
    return {
        key: strongest_family_member(items)
        for key, items in grouped.items()
    }


def evaluate_reading(
    spec: TestSpec,
    trade: Trade,
    histories: Mapping[str, object],
) -> Reading:
    """Small dispatch API for the implemented raw-history calculators.

    Required keys:
      * ``usd_pairs`` -> pair-name to PriceSeries for ``kind == usd``
      * ``signal`` -> precomputed Reading for the given ``kind == up``
      * ``vix`` / ``vix3m`` -> PriceSeries for ``kind == risk_off``
      * ``calendar`` -> OfficialCalendar for ``kind == event``

    Price/yield-specific signal creation stays explicit at integration time;
    callers use ``price_momentum_reading`` or ``alfred_momentum_reading`` with
    the relevant series and the fixed REV4 semantic flag.
    """
    try:
        if spec.kind == "usd":
            return usd_basket_reading(
                histories["usd_pairs"], trade.entry_time_utc, instrument=trade.instrument
            )
        if spec.kind == "risk_off":
            return risk_off_reading(
                histories["vix"], histories["vix3m"], trade.entry_time_utc
            )
        if spec.kind == "event":
            return event_reading(histories["calendar"], trade.entry_time_utc)
        if spec.kind == "up":
            reading = histories["signal"]
            if not isinstance(reading, Reading):
                return Reading.unknown("signal input must be a Reading")
            return reading
    except (KeyError, TypeError, ValueError) as error:
        return Reading.unknown(f"missing or invalid {spec.macro} input: {error}")
    return Reading.not_tested()


def run_test(
    test_id: str,
    trades: Sequence[Trade],
    readings: Mapping[str, Reading],
    *,
    seed: int = 0,
) -> Comparison:
    """Classify and compare the trades for one preregistered matrix row."""
    spec = TESTS_BY_ID[test_id]
    observations = []
    for trade in trades:
        if trade.instrument != spec.instrument:
            continue
        reading = readings.get(trade.trade_id, Reading.unknown("no macro reading"))
        observations.append(classify(spec, trade, reading))
    family = (
        "FED_REPRICING_OVERLAP"
        if spec.macro in OVERLAPPING_DRIVER_LABELS
        else None
    )
    return compare(test_id, observations, seed=seed, family=family)


def run_all_tests(
    trades: Sequence[Trade],
    readings_by_test: Mapping[str, Mapping[str, Reading]],
    *,
    seed: int = 0,
) -> tuple[Comparison, ...]:
    """Run all 22 effective definitions, preserving the 19-row legacy prefix."""
    comparisons = tuple(
        run_test(spec.test_id, trades, readings_by_test.get(spec.test_id, {}), seed=seed)
        for spec in ALL_TESTS
    )
    decisions = family_decisions(comparisons)
    adjusted = []
    for item in comparisons:
        if item.family is None:
            adjusted.append(item)
            continue
        instrument = TESTS_BY_ID[item.test_id].instrument
        strongest_id, family_recommended = decisions[(instrument, item.family)]
        selected = item.test_id == strongest_id
        adjusted.append(
            replace(
                item,
                gate_recommended=selected and family_recommended,
                gate_confirmed=selected and item.gate_confirmed,
            )
        )
    return tuple(adjusted)
