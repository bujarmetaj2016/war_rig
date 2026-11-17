import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from research import download_macro as downloader
from research.part4_engine import ALL_TESTS
from research.run_part4 import required_fred_series


class DownloadTests(unittest.TestCase):
    def test_series_cover_all_22_rev4_comparisons(self):
        self.assertEqual(len(ALL_TESTS), 22)
        requirements = [required_fred_series(spec) for spec in ALL_TESTS]
        for spec, needed in zip(ALL_TESTS, requirements):
            with self.subTest(test=spec.test_id):
                self.assertEqual(bool(needed), spec.kind != "event")
                self.assertLessEqual(needed, set(downloader.SERIES))
        self.assertEqual(set().union(*requirements), set(downloader.SERIES))
        self.assertEqual(set(downloader.SERIES), {
            "DGS2", "DFII10", "BAMLH0A0HYM2", "DCOILBRENTEU", "VIXCLS", "VXVCLS",
            "DEXUSEU", "DEXJPUS", "DEXUSUK", "DEXCAUS", "DEXSZUS", "DEXUSAL",
        })

    key = "test" * 8
    trades = b"fill_time\n2024-01-05T20:00:00-05:00\n2024-01-04 12:00:00 UTC\n"
    row = {
        "date": "2024-01-02",
        "realtime_start": "2024-01-03",
        "realtime_end": "9999-12-31",
        "value": "4.1",
    }

    def test_prior_day_only_and_expired_vintages(self):
        entry = datetime.fromisoformat("2024-01-05T00:01:00+00:00")
        for start, end, value, expected in (
            ("2024-01-04", "2024-01-04", "4.1", True),
            ("2024-01-05", "9999-12-31", "4.2", False),
            ("2024-01-06", "9999-12-31", "4.3", False),
            ("2024-01-03", "2024-01-03", "4.0", False),
            ("2024-01-04", "9999-12-31", ".", False),
        ):
            with self.subTest(start=start, end=end, value=value):
                vintage = downloader.Vintage.from_record(
                    dict(self.row, realtime_start=start, realtime_end=end, value=value)
                )
                self.assertEqual(vintage.available_at(entry), expected)
        vintage = downloader.Vintage.from_record(dict(self.row, realtime_start="2024-01-05"))
        self.assertFalse(vintage.available_at(datetime.fromisoformat("2024-01-04T19:01:00-05:00")))
        with self.assertRaises(ValueError):
            vintage.available_at(datetime(2024, 1, 5))

    def test_paginated_cli_records_only_sanitized_provenance(self):
        def fake_open(url, **kwargs):
            query = parse_qs(urlsplit(url).query)
            self.assertEqual(query["api_key"], [self.key])
            offset = int(query["offset"][0])
            if urlsplit(url).path.endswith("/vintagedates"):
                self.assertEqual((query["realtime_start"], query["realtime_end"]),
                                 (["2024-01-03"], ["2024-01-05"]))
                return io.StringIO(json.dumps({
                    "offset": offset, "count": 2,
                    "vintage_dates": [("2024-01-03", "2024-01-04")[offset]],
                }))
            self.assertEqual(query["output_type"], ["1"])
            start = ("2024-01-03", "2024-01-04")[offset]
            end = ("2024-01-03", "9999-12-31")[offset]
            return io.StringIO(json.dumps({
                "offset": offset,
                "count": 2,
                "observations": [
                    dict(self.row, realtime_start=start, realtime_end=end, ignored=self.key)
                ],
                "ignored": url,
            }))

        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"FRED_API_KEY": self.key}
        ), patch.object(downloader, "TRADE_SHA256", hashlib.sha256(self.trades).hexdigest()), patch.object(
            downloader, "build_opener"
        ) as opener:
            trades = Path(directory) / "trade_results.csv"
            trades.write_bytes(self.trades)
            opener.return_value.open.side_effect = fake_open
            self.assertEqual(downloader.main(["--out", directory, "--trades", str(trades)]), 0)
            self.assertEqual(opener.return_value.open.call_count, 4 * len(downloader.SERIES))
            out = Path(directory)
            manifest = json.loads((out / downloader.MANIFEST).read_text())
            self.assertEqual(manifest["bounds"]["realtime"], {"start": "2024-01-03", "end": "2024-01-05"})
            self.assertIn("550 calendar days", manifest["derivation"]["observation"])
            self.assertEqual([entry["series_id"] for entry in manifest["series"]], list(downloader.SERIES))
            for entry in manifest["series"]:
                if entry["series_id"] in downloader.FX_QUOTES:
                    base, quote = downloader.FX_QUOTES[entry["series_id"]]
                    self.assertEqual(entry["quote_direction"], {"base": base, "quote": quote})
                for url in [entry["vintage_dates_url"], *entry["observation_urls"]]:
                    self.assertNotIn("api_key", parse_qs(urlsplit(url).query))
                self.assertEqual(entry["vintage_dates"], 2)
                self.assertEqual(entry["vintage_rows"], 1)
                data = (out / entry["file"]).read_bytes()
                self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(data.splitlines()[1:], [b"2024-01-02,2024-01-03,2024-01-05,4.1"])
            for path in out.iterdir():
                self.assertNotIn(self.key, path.read_text())

    def test_network_errors_do_not_print_or_persist_transport_url(self):
        def fred_error(url):
            # Exercise both bare and URL-encoded secrets as well as echoed request URLs.
            encoded_key = "".join(f"%{ord(char):02X}" for char in self.key)
            body = json.dumps({"error_message": f"Too many vintage dates.\n{url} {encoded_key}"})
            return HTTPError(url, 400, url, None, io.BytesIO(body.encode()))

        for fail, expected in (
            (lambda url: URLError(url), "FRED request failed or returned invalid JSON."),
            (fred_error, "HTTP 400): Too many vintage dates."),
            (lambda url: HTTPError(url, 403, url, None, io.BytesIO(url.encode())),
             "No FRED error_message was provided."),
        ):
            def fake_open(url, **kwargs):
                raise fail(url)

            with tempfile.TemporaryDirectory() as directory, patch.dict(
                os.environ, {"FRED_API_KEY": self.key}
            ), patch.object(downloader, "TRADE_SHA256", hashlib.sha256(self.trades).hexdigest()), patch.object(
                downloader, "build_opener"
            ) as opener, contextlib.redirect_stderr(
                io.StringIO()
            ) as err:
                trades = Path(directory) / "trade_results.csv"
                trades.write_bytes(self.trades)
                opener.return_value.open.side_effect = fake_open
                self.assertEqual(downloader.main(["--out", directory, "--trades", str(trades)]), 1)
                self.assertIn("DGS2: FRED request failed", err.getvalue())
                self.assertIn(expected, err.getvalue())
                self.assertNotIn(self.key, err.getvalue())
                self.assertNotIn("api_key=", err.getvalue())
                self.assertNotIn("%74", err.getvalue())
                self.assertEqual(len(err.getvalue().splitlines()), 1)
                self.assertEqual(list(Path(directory).iterdir()), [trades])

    def test_missing_key_does_not_contact_fred(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
            downloader, "build_opener"
        ) as opener, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(downloader.main(["--out", "/out"]), 1)
            opener.assert_not_called()

    def test_recorded_url_pins_observation_bounds(self):
        bounds = downloader.trade_bounds(self.trades)
        query = parse_qs(urlsplit(downloader.source_url(
            "observations", "DGS2", bounds.realtime, bounds.observation
        )).query)
        self.assertEqual(query["observation_start"], ["2022-07-03"])
        self.assertEqual(query["observation_end"], ["2024-01-05"])

    def test_window_calculation_uses_utc_and_margin(self):
        bounds = downloader.trade_bounds(self.trades)
        self.assertEqual(bounds.earliest_entry, date(2024, 1, 4))
        self.assertEqual(bounds.latest_entry, date(2024, 1, 6))
        self.assertEqual(bounds.realtime, downloader.Window(date(2024, 1, 3), date(2024, 1, 5)))
        self.assertEqual(bounds.observation.start, bounds.earliest_entry - timedelta(days=550))
        with self.assertRaises(downloader.DownloadError):
            downloader.trade_bounds(b"fill_time\n2024-01-04 12:00:00\n")

    def test_split_has_at_most_1500_vintage_dates_and_covers_edges(self):
        start = date(2000, 1, 1)
        dates = [start + timedelta(days=2 * n) for n in range(1, 3002)]
        full = downloader.Window(start, dates[-1] + timedelta(days=3))
        windows = downloader.split_windows(full, dates)
        self.assertEqual(windows[0].start, full.start)
        self.assertEqual(windows[-1].end, full.end)
        self.assertEqual([sum(w.start <= d <= w.end for d in dates) for w in windows],
                         [1500, 1500, 1])
        for left, right in zip(windows, windows[1:]):
            self.assertEqual(left.end + timedelta(days=1), right.start)
        self.assertEqual(downloader.split_windows(full, []), [full])

    def test_merge_clips_deduplicates_and_preserves_revision(self):
        days = [date(2024, 1, n) for n in range(1, 7)]
        full = downloader.Window(days[0], days[5])
        left = downloader.Window(days[0], days[2])
        right = downloader.Window(days[3], days[5])
        carry = downloader.Vintage(days[0], days[0], days[4], "4.1")
        revision = downloader.Vintage(days[0], days[5], days[5], "4.2")
        self.assertEqual(downloader.merge_windows(full, [
            (left, [carry, carry]), (right, [carry, revision]),
        ]), [carry, revision])

    def test_merge_rejects_gaps_overlaps_and_incomplete_coverage(self):
        d1, d2, d3, d4 = (date(2024, 1, n) for n in range(1, 5))
        full = downloader.Window(d1, d4)
        carry = downloader.Vintage(d1, d1, d4, "4.1")
        for chunks in (
            [(downloader.Window(d1, d2), [carry])],
            [(downloader.Window(d1, d2), [carry]), (downloader.Window(d4, d4), [carry])],
            [(downloader.Window(d1, d2), [carry]), (downloader.Window(d2, d4), [carry])],
            [(full, [carry, downloader.Vintage(d1, d2, d4, "4.2")])],
            [(full, [downloader.Vintage(d1, d1, d1, "4.1"),
                     downloader.Vintage(d1, d3, d4, "4.2")])],
            [(downloader.Window(d1, d2), [carry]),
             (downloader.Window(d3, d4), [downloader.Vintage(d3, d3, d4, "4.2")])],
            [(full, [downloader.Vintage(d1, d1, d3, "4.1")])],
        ):
            with self.subTest(chunks=chunks), self.assertRaises(downloader.DownloadError):
                downloader.merge_windows(full, chunks)


if __name__ == "__main__":
    unittest.main()
