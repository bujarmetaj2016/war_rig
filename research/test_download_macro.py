import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from research import download_macro as downloader


class DownloadTests(unittest.TestCase):
    key = "test" * 8
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
            self.assertEqual(query["output_type"], ["1"])
            offset = int(query["offset"][0])
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
        ), patch.object(downloader, "build_opener") as opener:
            opener.return_value.open.side_effect = fake_open
            self.assertEqual(downloader.main(["--out", directory]), 0)
            self.assertEqual(opener.return_value.open.call_count, 2 * len(downloader.SERIES))
            out = Path(directory)
            manifest = json.loads((out / downloader.MANIFEST).read_text())
            self.assertEqual([entry["series_id"] for entry in manifest["series"]], list(downloader.SERIES))
            for entry in manifest["series"]:
                self.assertNotIn("api_key", parse_qs(urlsplit(entry["source_url"]).query))
                self.assertEqual(entry["vintage_rows"], 2)
                data = (out / entry["file"]).read_bytes()
                self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
                self.assertIn(b"2024-01-02,2024-01-03,2024-01-03,4.1\n", data)
                self.assertIn(b"2024-01-02,2024-01-04,9999-12-31,4.1\n", data)
            for path in out.iterdir():
                self.assertNotIn(self.key, path.read_text())

    def test_network_errors_do_not_print_or_persist_transport_url(self):
        for fail in (
            lambda url: URLError(url),
            lambda url: HTTPError(url, 403, url, None, io.BytesIO(url.encode())),
        ):
            def fake_open(url, **kwargs):
                raise fail(url)

            with tempfile.TemporaryDirectory() as directory, patch.dict(
                os.environ, {"FRED_API_KEY": self.key}
            ), patch.object(downloader, "build_opener") as opener, contextlib.redirect_stderr(
                io.StringIO()
            ) as err:
                opener.return_value.open.side_effect = fake_open
                self.assertEqual(downloader.main(["--out", directory]), 1)
                self.assertIn("DGS2: FRED request failed", err.getvalue())
                self.assertNotIn(self.key, err.getvalue())
                self.assertNotIn("api_key", err.getvalue())
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_missing_key_does_not_contact_fred(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
            downloader, "build_opener"
        ) as opener, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(downloader.main(["--out", "/out"]), 1)
            opener.assert_not_called()

    def test_recorded_url_pins_observation_bounds(self):
        query = parse_qs(urlsplit(downloader.source_url("DGS2", date(2020, 1, 1), date(2024, 1, 1))).query)
        self.assertEqual(query["observation_start"], ["2020-01-01"])
        self.assertEqual(query["observation_end"], ["2024-01-01"])


if __name__ == "__main__":
    unittest.main()
