import csv
import hashlib
import io
import json
import shutil
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from research import download_release_schedules as downloader
from research.reparse_release_schedules import reparse


FIXTURES = Path(__file__).parent / "fixtures" / "release_schedules"
WORKSPACE = Path(__file__).parent / ".release_schedule_test_output"
OWNER = Path(__file__).resolve().parents[1] / "reference/history/macro-schedules-retry"
OWNER_SAMPLES = {
    "fomc": ("fomc_fomccalendars.htm_fe3255ea54.html",
             "3af1a8595bde89728f0f14a34636f9848ea93031994da3bee7b8911d94a5b6a2"),
    "ecb": ("ecb_index.en.html_25ee05e583.html",
            "970599715c97bc5fe95a89f9d9daed724ad64bb96a9d5797ca37b27f2f238ecc"),
    "boe": ("boe_upcoming-mpc-dates_cd798dc790.html",
            "117a44c10955e83593e91161498418459614f37328218216eb205198b9e60449"),
    "05": ("bls_cpi_05_sched_list.htm_67cfe62dbc.html",
           "b2b28325808b60a1d1f10136adbeda4a7db4b7c1cc3a9e5daef353d6d79e8f3d"),
    "06": ("bls_cpi_06_sched_list.htm_572eaac9d4.html",
           "64aa79e6ea4f46f86bc35e49a4f4a1a1aa5b0a5c86375153fdf2d70f511f6b49"),
}


def saved_page(key):
    filename, digest = OWNER_SAMPLES[key]
    return filename, digest, (OWNER / "sources" / filename).read_bytes()


class ReleaseScheduleTests(unittest.TestCase):
    def test_http_error_reports_exact_failed_url_including_redirect_target(self):
        source = next(source for source in downloader.SOURCES if source.key == "ecb")
        for failed in (source.url, source.url + "?calendar=2026"):
            with self.subTest(failed=failed):
                opener = Mock()
                opener.open.side_effect = HTTPError(failed, 404, "Not Found", None, io.BytesIO())
                with self.assertRaises(downloader.DownloadError) as error:
                    downloader.fetch_page(opener, source, source.url)
                self.assertEqual(str(error.exception), f"Official schedule request failed (HTTP 404): {failed}")

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

    def parse_saved(self, key, sample, url=None):
        source = next(source for source in downloader.SOURCES if source.key == key)
        name, digest, body = saved_page(sample)
        self.assertEqual(hashlib.sha256(body).hexdigest(), digest)
        return downloader.extract_events(
            source, url or source.url, body, None, "2026-11-17T23:08:41+00:00",
            f"sources/{name}", digest, date(2026, 5, 6), date(2027, 2, 5),
        )

    def test_saved_bls_releases_exclude_other_rows_and_use_eastern_time(self):
        for key, month, day, updated in (
            ("bls_cpi", "05", "2026-05-12", "2026-05-06"),
            ("bls_cpi", "06", "2026-06-10", "2026-06-10"),
            ("bls_empsit", "05", "2026-05-08", "2026-05-06"),
            ("bls_empsit", "06", "2026-06-05", "2026-06-10"),
        ):
            with self.subTest(key=key, month=month):
                row, = self.parse_saved(
                    key, month, f"https://www.bls.gov/schedule/2026/{month}_sched_list.htm"
                )
                self.assertEqual(row["scheduled_date"], day)
                self.assertEqual(row["scheduled_time"], "08:30:00")
                self.assertEqual(row["time_zone"], "America/New_York")
                self.assertEqual(row["scheduled_at_utc"], f"{day}T12:30:00+00:00")
                self.assertEqual(row["page_updated_date"], updated)

    def test_saved_central_bank_decision_dates_without_inventing_times(self):
        for key, expected, updated in (
            ("fomc", ["2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09", "2027-01-27"],
             "2026-11-12"),
            ("ecb", ["2026-12-17", "2027-02-04"], "2026-11-16"),
            ("boe", ["2026-06-18", "2026-07-30", "2026-09-17", "2026-11-05", "2026-12-17", "2027-02-04"],
             "2026-09-21"),
        ):
            with self.subTest(key=key):
                rows = self.parse_saved(key, key)
                self.assertEqual([row["scheduled_date"] for row in rows], expected)
                self.assertTrue(all(not row["scheduled_at_utc"] and not row["time_zone"] for row in rows))
                self.assertTrue(all(row["page_updated_date"] == updated for row in rows))

    def test_offline_reparse_fingerprints_and_winter_conversion(self):
        payload, manifest = reparse(OWNER)
        provenance = json.loads(manifest)
        self.assertEqual(len(provenance["source_page_sha256"]), 55)
        self.assertEqual(provenance["event_count"], 22)
        self.assertEqual(provenance["reparsed_events_file"]["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertIn(b"2026-11-10T13:30:00+00:00", payload)

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

        monthly = "https://www.bls.gov/schedule/2026/05_sched_list.htm"

        def fake_fetch(_opener, source, url):
            return saved_page("05" if url == monthly or source.key.startswith("bls_") else source.key)[2]

        with patch.object(downloader, "fetch_page", side_effect=fake_fetch), patch.object(
            downloader, "archive_links",
            side_effect=lambda source, _page, _start, _end, url: (
                [monthly] if source.key.startswith("bls_") and url == source.url else []
            ),
        ), patch.object(
            downloader, "read_schedule_bounds", return_value=downloader.ScheduleBounds(
                date(2026, 5, 6), date(2026, 11, 9), date(2026, 11, 10), date(2026, 11, 11),
            ),
        ):
            downloader.download(manifest_path, out)

        manifest = json.loads((out / "release_schedule_manifest.json").read_text())
        self.assertEqual(
            manifest["fred_realtime_bounds"],
            {"start": "2026-05-06", "end": "2026-11-09"},
        )
        self.assertEqual(
            manifest["schedule_coverage"],
            {
                "start": "2026-05-06",
                "end": "2026-11-11",
                "latest_trade_date": "2026-11-10",
                "forward_event_horizon_calendar_days": 1,
            },
        )
        self.assertEqual(len(manifest["source_pages"]), 7)
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
