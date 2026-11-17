"""Run REV4 offline against checksum-verified research inputs."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections import Counter
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from . import part4_engine as engine
from .download_macro import FX_QUOTES, MANIFEST, VOLATILITY_SERIES
from .verify_alfred import verified_vintages

ALFRED_TESTS = {
    "EURUSD_BRENT_SPOT": "DCOILBRENTEU",
    "EURUSD_DGS2": "DGS2",
    "GBPUSD_BRENT_SPOT": "DCOILBRENTEU",
    "GBPUSD_DGS2": "DGS2",
    "GOLD_DFII10": "DFII10",
    "GOLD_DGS2": "DGS2",
    "SP500_HY_SPREAD": "BAMLH0A0HYM2",
    "DAX_BRENT_SPOT": "DCOILBRENTEU",
}
BRENT_TESTS = {test for test, series in ALFRED_TESTS.items() if series == "DCOILBRENTEU"}
REMAINING_NON_EVENT = {
    spec.test_id for spec in engine.ALL_TESTS
    if spec.kind != "event" and spec.test_id not in ALFRED_TESTS
}
FRED_CLOSES = {
    **{base + quote: series for series, (base, quote) in FX_QUOTES.items()},
    **dict(zip(("VIX", "VIX3M"), VOLATILITY_SERIES)),
}


def required_fred_series(spec: engine.TestSpec) -> set[str]:
    if spec.test_id in ALFRED_TESTS:
        return {ALFRED_TESTS[spec.test_id]}
    if spec.kind == "risk_off":
        return set(VOLATILITY_SERIES)
    if spec.kind == "usd":
        excluded = {"EURUSD": "EUR", "GBPUSD": "GBP"}.get(spec.instrument)
        return {FRED_CLOSES[pair] for currency, pair, _ in engine.USD_QUOTE_PAIRS
                if currency != excluded}
    if spec.test_id == "DAX_EURUSD_10D":
        return {FRED_CLOSES["EURUSD"]}
    if spec.kind == "event":
        return set()
    raise ValueError(f"No FRED input mapping for {spec.test_id}")
PRICE_NAMES = {
    "USDJPY", "GBPUSD", "USDCAD", "USDCHF", "AUDUSD", "EURUSD", "VIX", "VIX3M",
    "BRENT_FRONT_MONTH",
}


def load_prices(history: Path) -> tuple[dict[str, engine.PriceSeries], dict[str, str]]:
    """Load researched close times and session dates; never infer them from Yahoo labels."""
    path = history / "price_manifest.json"
    if not path.is_file():
        return {}, {}
    manifest = path.read_bytes()
    pins = {path.name: hashlib.sha256(manifest).hexdigest()}
    prices = {}
    for item in json.loads(manifest)["series"]:
        name, filename = item["name"], item["file"]
        source = urlsplit(item["source_url"])
        if (name not in PRICE_NAMES or name in prices or filename != f"{name}.csv"
                or source.scheme != "https"
                or source.hostname not in ("finance.yahoo.com", "query1.finance.yahoo.com",
                                           "query2.finance.yahoo.com")):
            raise ValueError("Invalid or duplicate Yahoo Finance price input.")
        raw = (history / filename).read_bytes()
        pins[filename] = hashlib.sha256(raw).hexdigest()
        if pins[filename] != item["sha256"]:
            raise ValueError(f"{filename}: price SHA-256 mismatch.")
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if reader.fieldnames != ["close_time_utc", "close", "complete"]:
            raise ValueError(f"{filename}: invalid price schema.")
        bars = []
        for row in reader:
            if row["complete"] not in ("true", "false"):
                raise ValueError(f"{filename}: explicit completed-bar flag required.")
            bars.append(engine.PriceBar(
                datetime.fromisoformat(row["close_time_utc"].replace("Z", "+00:00")),
                float(row["close"]), row["complete"] == "true",
            ))
        expected = tuple(date.fromisoformat(day) for day in item["expected_dates"])
        if not expected:
            raise ValueError(f"{filename}: expected close dates are required.")
        prices[name] = engine.PriceSeries(name, tuple(bars), engine.PriceProvenance(
            name, item["source_url"], datetime.fromisoformat(item["downloaded_at_utc"]),
            item["close_convention"], pins[filename],
        ), expected)
    return prices, pins


def load_calendar(history: Path) -> tuple[engine.OfficialCalendar | None, dict[str, str]]:
    calendar, pins, _ = verify_schedule_delivery(history / "schedules")
    return calendar, {f"schedules/{name}": digest for name, digest in pins.items()}


def verify_schedule_delivery(
    root: Path,
) -> tuple[engine.OfficialCalendar | None, dict[str, str], dict]:
    """Verify downloaded bytes; require reviewed as-known coverage before use."""
    path = root / "release_schedule_manifest.json"
    if not path.is_file():
        return None, {}, {}
    raw = path.read_bytes()
    manifest = json.loads(raw)
    pins = {path.name: hashlib.sha256(raw).hexdigest()}

    def pinned(item: dict, filename: str) -> bytes:
        if filename != item["file"]:
            raise ValueError("Unexpected schedule artifact path.")
        data = (root / filename).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != item["sha256"]:
            raise ValueError("Schedule artifact SHA-256 mismatch.")
        pins[filename] = digest
        return data

    pages = {}
    for item in manifest["source_pages"]:
        filename = item["file"]
        if filename != f"sources/{Path(filename).name}" or filename in pages:
            raise ValueError("Invalid schedule source-page path.")
        pinned(item, filename)
        pages[filename] = item
    data = pinned(manifest["events_file"], "release_schedule_events.csv")
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    if len(rows) != manifest["event_count"]:
        raise ValueError("Schedule event count mismatch.")
    event_counts = Counter(row["event_type"] for row in rows)
    audit = {
        "manifest_sha256": pins[path.name],
        "downloaded_at_utc": manifest.get("downloaded_at_utc"),
        "schedule_coverage": manifest.get("schedule_coverage"),
        "source_pages": len(pages),
        "event_rows": len(rows),
        "event_rows_by_type": dict(sorted(event_counts.items())),
        "rows_missing_time_zone": sum(not row.get("time_zone") for row in rows),
        "rows_missing_page_update_date": sum(not row.get("page_updated_date") for row in rows),
    }
    review_path = root / "as_known_coverage.json"
    if not review_path.is_file():
        audit["availability_reason"] = "No verified as-known coverage for all five official event types."
        return None, pins, audit
    review_raw = review_path.read_bytes()
    pins[review_path.name] = hashlib.sha256(review_raw).hexdigest()
    review = json.loads(review_raw)
    if review["download_manifest_sha256"] != pins[path.name]:
        raise ValueError("As-known schedule review does not match download manifest.")
    verified_sources = {}
    events = set()
    for event_type in engine.EVENT_TYPES:
        filename = review["complete_official_page_by_event_type"][event_type]
        item = pages[filename]
        if item["source_key"] != {
            "FOMC": "fomc", "ECB": "ecb", "BOE": "boe", "US_CPI": "bls_cpi", "US_NFP": "bls_empsit",
        }[event_type]:
            raise ValueError("Reviewed event type is not supported by its source page.")
        updated = item["page_updated_date"]
        verified_sources[event_type] = engine.ScheduleProvenance(
            event_type, item["source_url"], date.fromisoformat(updated) if updated else None,
            datetime.fromisoformat(item["downloaded_at_utc"]), item["sha256"],
        )
        for row in rows:
            if row["source_file"] != filename:
                continue
            if (row["event_type"] != item["event_type"] or row["source_sha256"] != item["sha256"]
                    or row["source_url"] != item["source_url"]):
                raise ValueError("Event disagrees with its reviewed source.")
            if not row["scheduled_time"] or not row["time_zone"]:
                audit["availability_reason"] = "A reviewed event lacks a time or time zone."
                return None, pins, audit
            events.add((event_type, row["scheduled_date"], row["scheduled_time"], row["time_zone"]))
    start = date.fromisoformat(review["start"])
    end = date.fromisoformat(review["end"])
    coverage = manifest["schedule_coverage"]
    if not (date.fromisoformat(coverage["start"]) <= start <= end
            < date.fromisoformat(coverage["end"])):
        raise ValueError("Reviewed schedule does not cover the 24-hour forward horizon.")
    return engine.OfficialCalendar(
        tuple(engine.ScheduledEvent(kind, date.fromisoformat(day), time.fromisoformat(hour), zone)
              for kind, day, hour, zone in sorted(events)),
        verified_sources, start, end,
    ), pins, audit


def run_event_refresh(
    schedule_root: Path, contents: bytes, prior: dict,
) -> tuple[dict, dict[str, str]]:
    calendar, pins, audit = verify_schedule_delivery(schedule_root)
    if not pins:
        raise ValueError("Missing owner-delivered release schedule manifest.")
    trades = load_trades(contents)
    updated = {}
    for spec in engine.ALL_TESTS:
        if spec.kind != "event":
            continue
        readings = {
            trade.trade_id: (
                engine.event_reading(calendar, trade.entry_time_utc) if calendar is not None
                else engine.Reading.unknown(audit["availability_reason"])
            )
            for trade in trades if trade.instrument == spec.instrument
        }
        row = asdict(engine.run_test(spec.test_id, trades, readings, seed=prior["bootstrap_seed"]))
        row["unknown_reasons"] = dict(sorted(Counter(
            reading.reason or "unspecified" for reading in readings.values()
            if reading.code == "UNKNOWN"
        ).items()))
        if row["unknown_n"] and not any(bucket["n"] for bucket in row["buckets"].values()):
            row["status"] = "UNKNOWN"
        updated[spec.test_id] = row
    return {
        **prior,
        "status": "FINAL_REPORT",
        "latest_run_scope": sorted(updated),
        "schedule_verified_for_classification": calendar is not None,
        "schedule_delivery": audit,
        "matrix": [updated.get(row["test_id"], row) for row in prior["matrix"]],
    }, pins


def load_trades(contents: bytes) -> list[engine.Trade]:
    return [
        engine.Trade(
            row["id"], row["instrument"],
            {"BULLISH": "BUY", "BEARISH": "SELL"}[row["direction"]],
            datetime.fromisoformat(row["fill_time"].removesuffix(" UTC") + "+00:00"),
            row["final_outcome_label"], float(row["exit_r"]),
        )
        for row in csv.DictReader(io.StringIO(contents.decode("utf-8-sig")))
        if row["final_outcome_label"] in ("WIN", "LOSS")
    ]


def brent_futures_reading(
    series: engine.PriceSeries, documented_rolls: set[date], entry: datetime,
) -> engine.Reading:
    try:
        closes = series.completed_before(entry)
        changes = [
            (day, math.log(close / prior))
            for (_, prior), (day, close) in zip(closes, closes[1:])
            if day not in documented_rolls
        ]
        return engine.log_return_momentum_reading(
            changes, entry_date_utc=entry.date() + timedelta(days=1), label=series.name,
        )
    except engine.UnknownData as error:
        return engine.Reading.unknown(str(error))


def analyze(history: Path, trades_path: Path, *, prices=None, calendar=None,
            brent_only_prior: dict | None = None,
            remaining_prior: dict | None = None) -> tuple[dict, dict[str, str]]:
    contents = trades_path.read_bytes()
    raw, pins = verified_vintages(history, contents)
    manifest = json.loads((history / MANIFEST).read_bytes())
    economic = {
        item["series_id"]: engine.AlfredSeries(
            engine.AlfredProvenance(
                item["series_id"], (item["vintage_dates_url"], *item["observation_urls"]),
                datetime.fromisoformat(item["downloaded_at_utc"]), item["sha256"],
            ),
            tuple(engine.AlfredVintage(
                row.observation_date, row.start, row.end,
                None if row.value == "." else float(row.value),
            ) for row in raw[item["series_id"]]),
        )
        for item in manifest["series"]
    }
    trades = load_trades(contents)
    if brent_only_prior is not None:
        if (brent_only_prior["alfred_sources"] != manifest["series"]
                or brent_only_prior["price_sources"]
                or brent_only_prior["schedule_verified_for_classification"]
                or [row["test_id"] for row in brent_only_prior["matrix"]]
                != [spec.test_id for spec in engine.ALL_TESTS]):
            raise ValueError("Brent-only refresh requires the existing ALFRED-only evidence and matching inputs.")
        updated = {}
        for test_id in sorted(BRENT_TESTS):
            spec = engine.TESTS_BY_ID[test_id]
            readings = {
                trade.trade_id: engine.alfred_momentum_reading(
                    economic["DCOILBRENTEU"], trade.entry_time_utc, price_series=True,
                )
                for trade in trades if trade.instrument == spec.instrument
            }
            updated[test_id] = asdict(engine.run_test(test_id, trades, readings, seed=0))
            updated[test_id]["unknown_reasons"] = dict(sorted(Counter(
                reading.reason or "unspecified" for reading in readings.values()
                if reading.code == "UNKNOWN"
            ).items()))
        return {
            **brent_only_prior,
            "latest_run_scope": sorted(BRENT_TESTS),
            "matrix": [updated.get(row["test_id"], row) for row in brent_only_prior["matrix"]],
        }, pins

    prior_rows = {}
    if remaining_prior is not None:
        prior_rows = {row["test_id"]: row for row in remaining_prior["matrix"]}
        prior_sources = {row["series_id"]: row["sha256"] for row in remaining_prior["alfred_sources"]
                         if row["series_id"] in ALFRED_TESTS.values()}
        if (len(REMAINING_NON_EVENT) != 9 or set(prior_rows) != set(engine.TESTS_BY_ID)
                or set(prior_sources) != set(ALFRED_TESTS.values())
                or any(pins.get(f"{name}.csv") != digest for name, digest in prior_sources.items())
                or set(economic) != set(ALFRED_TESTS.values()) | set(FRED_CLOSES.values())
                or remaining_prior["price_sources"] or remaining_prior["schedule_verified_for_classification"]
                or prices is not None or calendar is not None):
            raise ValueError("Nine-comparison refresh requires the verified expanded ALFRED set and matching prior evidence.")
        prices = {}
    if prices is None:
        prices, price_pins = load_prices(history)
        pins.update(price_pins)
    closes = {**prices, **{
        name: engine.AlfredCloseSeries(name, economic[series])
        for name, series in FRED_CLOSES.items() if series in economic
    }}
    roll_dates = None
    price_manifest = history / "price_manifest.json"
    if "BRENT_FRONT_MONTH" in prices and price_manifest.name in pins:
        metadata = json.loads(price_manifest.read_bytes())
        front = next(item for item in metadata["series"] if item["name"] == "BRENT_FRONT_MONTH")
        if front.get("roll_date_documentation") and front.get("roll_dates_complete") is True:
            roll_dates = {date.fromisoformat(day) for day in front["roll_dates"]}
    if calendar is None and remaining_prior is None:
        calendar, schedule_pins = load_calendar(history)
        pins.update(schedule_pins)
    readings = {}
    classified = {}
    for spec in engine.ALL_TESTS:
        # Reclassify the prior rates rows only for same-trade family agreement;
        # do not rerun their statistical comparisons or bootstrap.
        if (remaining_prior is not None and spec.test_id not in REMAINING_NON_EVENT
                and not spec.test_id.endswith(("_DGS2", "_DFII10"))):
            continue
        by_trade = {}
        for trade in trades:
            if trade.instrument != spec.instrument:
                continue
            entry = trade.entry_time_utc
            if spec.test_id in ALFRED_TESTS:
                series = ALFRED_TESTS[spec.test_id]
                reading = engine.alfred_momentum_reading(
                    economic[series], entry, price_series=series == "DCOILBRENTEU",
                )
                if (series == "DCOILBRENTEU" and reading.code == "UNKNOWN"
                        and roll_dates is not None):
                    reading = brent_futures_reading(prices["BRENT_FRONT_MONTH"], roll_dates, entry)
            elif spec.test_id == "DAX_EURUSD_10D" and FRED_CLOSES["EURUSD"] in economic:
                reading = engine.alfred_momentum_reading(
                    economic[FRED_CLOSES["EURUSD"]], entry, price_series=True,
                )
            elif spec.test_id == "DAX_EURUSD_10D" and "EURUSD" in prices:
                reading = engine.price_momentum_reading(prices["EURUSD"], entry)
            elif spec.kind == "risk_off" and "VIX" not in closes:
                reading = engine.Reading.unknown("verified VIX history is missing")
            else:
                reading = engine.evaluate_reading(spec, trade, {
                    "usd_pairs": closes, "vix": closes.get("VIX"), "vix3m": closes.get("VIX3M"),
                    **({"calendar": calendar} if calendar is not None else {}),
                })
            by_trade[trade.trade_id] = reading
        readings[spec.test_id] = by_trade
        classified[spec.test_id] = [
            engine.classify(spec, trade, by_trade[trade.trade_id])
            for trade in trades if trade.instrument == spec.instrument
        ]
    if remaining_prior is None:
        results = engine.run_all_tests(trades, readings, seed=0)
    else:
        results = tuple(
            engine.run_test(spec.test_id, trades, readings[spec.test_id], seed=0)
            if spec.test_id in REMAINING_NON_EVENT else engine.Comparison(
                **{k: v for k, v in prior_rows[spec.test_id].items()
                   if k not in ("buckets", "unknown_reasons")},
                buckets={name: engine.BucketStats(**bucket)
                         for name, bucket in prior_rows[spec.test_id]["buckets"].items()},
            )
            for spec in engine.ALL_TESTS
        )
    family = {}
    for instrument in sorted({trade.instrument for trade in trades}):
        drivers = {
            result.test_id: {row.trade.trade_id: row.classification for row in classified[result.test_id]}
            for result in results
                if result.test_id.startswith(f"{instrument}_")
                and (engine.TESTS_BY_ID[result.test_id].kind == "usd"
                     or result.test_id.endswith(("_DGS2", "_DFII10")))
        }
        family[instrument] = {
            "agreement": [
                {"drivers": [left, right], "n": n, "agree": agree, "fraction": fraction}
                for (left, right), (n, agree, fraction) in engine.overlapping_driver_agreement(drivers).items()
            ],
            "strongest": engine.strongest_family_member([r for r in results if r.test_id in drivers]),
            "dxy": "NOT_TESTED: REV4 does not define a separate DXY classification/sign test",
        }
    dax_risk = {row.trade.trade_id: row.reading.code for row in classified["DAX_VIX_RISK_OFF"]}
    exporter_split = {
        regime: asdict(engine.compare(
            "DAX_EURUSD_10D",
            [row for row in classified["DAX_EURUSD_10D"]
             if dax_risk[row.trade.trade_id] == regime],
            seed=0,
        ))
        for regime in ("RISK_OFF", "NOT_RISK_OFF", "UNKNOWN")
    }
    for comparison in exporter_split.values():
        comparison.pop("gate_recommended")
        comparison.pop("gate_confirmed")
    matrix = []
    for result in results:
        spec = engine.TESTS_BY_ID[result.test_id]
        preserved = remaining_prior is not None and spec.test_id not in REMAINING_NON_EVENT
        data = dict(prior_rows[spec.test_id]) if preserved else asdict(result)
        if spec.kind == "usd" or spec.test_id.endswith(("_DGS2", "_DFII10")):
            strongest, passes = family[spec.instrument]["strongest"]
            data["family"] = "USD_AND_RATES"
            data["gate_recommended"] = result.gate_recommended and passes and strongest == result.test_id
            data["gate_confirmed"] = result.gate_confirmed and data["gate_recommended"]
        if not preserved:
            data["unknown_reasons"] = dict(sorted(Counter(
                row.reading.reason or "unspecified" for row in classified[result.test_id]
                if row.classification == "UNKNOWN"
            ).items()))
        matrix.append(data)
    return {
        "status": "PARTIAL_TRADE_TEST",
        **({"latest_run_scope": sorted(REMAINING_NON_EVENT)} if remaining_prior is not None else {}),
        "alfred_sources": manifest["series"],
        "price_sources": {name: {
            **asdict(series.provenance),
            "downloaded_at_utc": series.provenance.downloaded_at_utc.isoformat(),
        } for name, series in prices.items()},
        "schedule_verified_for_classification": calendar is not None,
        "bootstrap_seed": 0,
        "matrix": matrix,
        "family": family,
        "dax_exporter_descriptive_split": exporter_split,
    }, pins
