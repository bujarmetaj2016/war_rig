import csv
import hashlib
import json
import shutil
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from research import download_release_schedules as downloader


FIXTURES = Path(__file__).parent / "fixtures" / "release_schedules"
WORKSPACE = Path(__file__).parent / ".release_schedule_test_output"
SAMPLE_PAGES = {
    "fomc": "fomc.html",
    "ecb": "ecb.html",
    "boe": "boe.html",
    "bls_cpi": "bls_cpi.html",
    "bls_empsit": "bls_empsit.html",
}


class ReleaseScheduleTests(unittest.TestCase):
    def test_mocked_fred_manifest_bounds(self):
        self.assertEqual(
            downloader.read_bounds(FIXTURES / "fred_manifest_mock.json"),
            (date(2024, 1, 1), date(2025, 12, 30)),
        )
        self.assertEqual(
            downloader.read_schedule_bounds(FIXTURES / "fred_manifest_mock.json"),
            downloader.ScheduleBounds(
                date(2024, 1, 1), date(2025, 12, 30),
                date(2025, 12, 31), date(2026, 1, 1),
            ),
        )

    def test_parse_official_page_samples_and_keep_missing_provenance_unknown(self):
        expected = {
            "fomc": ("2024-01-30", "2024-01-08"),
            "ecb": ("2024-01-25", "2024-01-15"),
            "boe": ("2024-03-21", "2024-02-01"),
            "bls_cpi": ("2024-01-11", "2024-01-04"),
            "bls_empsit": ("2024-01-05", None),
        }
        for source in downloader.SOURCES:
            with self.subTest(source=source.key):
                contents = (FIXTURES / SAMPLE_PAGES[source.key]).read_bytes()
                parsed = downloader.parse_page(contents)
                updated = downloader.page_updated_date(" ".join(parsed.page_text))
                events = downloader.extract_events(
                    source,
                    source.url,
                    contents,
                    updated,
                    "2026-11-17T22:00:00+00:00",
                    f"sources/{SAMPLE_PAGES[source.key]}",
                    hashlib.sha256(contents).hexdigest(),
                    date(2024, 1, 1),
                    date(2025, 12, 31),
                )
                self.assertGreaterEqual(len(events), 1)
                self.assertEqual(events[0]["scheduled_date"], expected[source.key][0])
                self.assertEqual(events[0]["page_updated_date"], expected[source.key][1])
                self.assertEqual(events[0]["source_url"], source.url)
                self.assertEqual(
                    events[0]["source_sha256"], hashlib.sha256(contents).hexdigest()
                )
                self.assertIsNone(
                    downloader.schedule_known_by_entry(
                        updated, date(2024, 1, 1)
                    )
                )

    def test_extracts_only_explicit_time_and_zone(self):
        cpi_source = next(source for source in downloader.SOURCES if source.key == "bls_cpi")
        cpi_bytes = (FIXTURES / "bls_cpi.html").read_bytes()
        cpi = downloader.extract_events(
            cpi_source, cpi_source.url, cpi_bytes, None, "downloaded",
            "source.html", "sha", date(2024, 1, 1), date(2025, 12, 31),
        )
        self.assertEqual((cpi[0]["scheduled_time"], cpi[0]["time_zone"]), ("8:30 a.m.", "ET"))
        self.assertEqual((cpi[1]["scheduled_time"], cpi[1]["time_zone"]), (None, None))

        employment_source = next(
            source for source in downloader.SOURCES if source.key == "bls_empsit"
        )
        employment_bytes = (FIXTURES / "bls_empsit.html").read_bytes()
        employment = downloader.extract_events(
            employment_source, employment_source.url, employment_bytes, None, "downloaded",
            "source.html", "sha", date(2024, 1, 1), date(2025, 12, 31),
        )
        self.assertEqual(employment[0]["scheduled_time"], "8:30 a.m.")
        self.assertIsNone(employment[0]["time_zone"])

    def test_schedule_asof_eligibility_requires_prior_dated_page(self):
        self.assertTrue(downloader.schedule_known_by_entry(date(2024, 1, 4), date(2024, 1, 5)))
        self.assertIsNone(downloader.schedule_known_by_entry(date(2024, 1, 5), date(2024, 1, 5)))
        self.assertIsNone(downloader.schedule_known_by_entry(date(2024, 1, 6), date(2024, 1, 5)))
        self.assertIsNone(downloader.schedule_known_by_entry(None, date(2024, 1, 5)))

    def test_archive_discovery_is_year_bounded_and_host_restricted(self):
        page = downloader.parse_page(
            b'<a href="/monetarypolicy/calendar/archive.htm">2025 FOMC calendar</a>'
            b'<a href="https://attacker.example/fomc2025.htm">2025 FOMC</a>'
            b'<a href="/monetarypolicy/fomccalendars2025.pdf">2025 calendar PDF</a>'
        )
        source = next(source for source in downloader.SOURCES if source.key == "fomc")
        links = downloader.archive_links(
            source, page, date(2024, 1, 1), date(2025, 12, 31), source.url
        )
        self.assertEqual(
            links,
            ["https://www.federalreserve.gov/monetarypolicy/calendar/archive.htm"],
        )

    def test_offline_download_writes_hash_pinned_pages_and_bounded_events(self):
        if WORKSPACE.exists():
            self.fail(f"Refusing to overwrite pre-existing test path: {WORKSPACE}")
        WORKSPACE.mkdir()
        out = WORKSPACE / "output"
        manifest_path = FIXTURES / "fred_manifest_mock.json"

        def fake_fetch(_opener, source, _url):
            return (FIXTURES / SAMPLE_PAGES[source.key]).read_bytes()

        with patch.object(downloader, "fetch_page", side_effect=fake_fetch), patch.object(
            downloader, "archive_links", return_value=[]
        ):
            downloader.download(manifest_path, out)

        manifest = json.loads((out / "release_schedule_manifest.json").read_text())
        self.assertEqual(
            manifest["fred_realtime_bounds"],
            {"start": "2024-01-01", "end": "2025-12-30"},
        )
        self.assertEqual(
            manifest["schedule_coverage"],
            {
                "start": "2024-01-01",
                "end": "2026-01-01",
                "latest_trade_date": "2025-12-31",
                "forward_event_horizon_calendar_days": 1,
            },
        )
        self.assertEqual(len(manifest["source_pages"]), 5)
        self.assertEqual(manifest["event_count"], 10)
        for source_record in manifest["source_pages"]:
            contents = (out / source_record["file"]).read_bytes()
            self.assertEqual(source_record["sha256"], hashlib.sha256(contents).hexdigest())
        event_file = out / manifest["events_file"]["file"]
        self.assertEqual(
            manifest["events_file"]["sha256"],
            hashlib.sha256(event_file.read_bytes()).hexdigest(),
        )
        with event_file.open(encoding="utf-8", newline="") as stream:
            events = list(csv.DictReader(stream))
        self.assertEqual(len(events), 10)
        self.assertTrue(all(event["source_sha256"] for event in events))
        self.assertTrue(all(event["source_url"].startswith("https://") for event in events))
        self.assertIn("strictly before the UTC entry date", manifest["eligibility_policy"])
        shutil.rmtree(WORKSPACE)

    def tearDown(self):
        if WORKSPACE.exists():
            shutil.rmtree(WORKSPACE)


if __name__ == "__main__":
    unittest.main()
