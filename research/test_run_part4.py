import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from research.part4_engine import ALL_TESTS
from research.run_part4 import load_calendar, load_prices, run_event_refresh


class IntakeTests(unittest.TestCase):
    def test_absent_inputs_are_not_synthesized(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(load_prices(root), ({}, {}))
            self.assertEqual(load_calendar(root), (None, {}))

    def test_price_close_times_and_checksum(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "EURUSD.csv"
            body = b"close_time_utc,close,complete\n2026-05-01T20:00:00Z,1.13,true\n"
            path.write_bytes(body)
            (root / "price_manifest.json").write_text(json.dumps({"series": [{
                "name": "EURUSD", "file": path.name,
                "source_url": "https://finance.yahoo.com/quote/EURUSD%3DX/history/",
                "downloaded_at_utc": "2026-11-18T00:00:00+00:00",
                "close_convention": "Verified fixture close",
                "sha256": hashlib.sha256(body).hexdigest(),
                "expected_dates": ["2026-05-01"],
            }]}))
            prices, pins = load_prices(root)
            self.assertEqual(prices["EURUSD"].bars[0].close_time_utc,
                             datetime(2026, 5, 1, 20, tzinfo=timezone.utc))
            self.assertEqual(pins[path.name], hashlib.sha256(body).hexdigest())
            path.write_bytes(body.replace(b"1.13", b"1.99"))
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                load_prices(root)

    def test_downloaded_schedule_is_not_a_point_in_time_attestation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            schedule = root / "schedules"
            schedule.mkdir()
            events = b"event_type,scheduled_date\n"
            (schedule / "release_schedule_events.csv").write_bytes(events)
            (schedule / "release_schedule_manifest.json").write_text(json.dumps({
                "source_pages": [], "event_count": 0,
                "events_file": {
                    "file": "release_schedule_events.csv",
                    "sha256": hashlib.sha256(events).hexdigest(),
                },
            }))
            calendar, pins = load_calendar(root)
            self.assertIsNone(calendar)
            self.assertIn("schedules/release_schedule_events.csv", pins)

            prior = {"bootstrap_seed": 0, "matrix": [
                {"test_id": spec.test_id, "status": "preserve"} for spec in ALL_TESTS
            ]}
            contents = (
                b"id,instrument,direction,fill_time,final_outcome_label,exit_r\n"
                b"1,EURUSD,BULLISH,2026-05-10 10:00:00 UTC,WIN,1\n"
            )
            result, _ = run_event_refresh(schedule, contents, prior)
            self.assertEqual(len(result["latest_run_scope"]), 5)
            row = next(row for row in result["matrix"] if row["test_id"] == "EURUSD_SCHEDULED_EVENT")
            self.assertEqual((row["status"], row["unknown_n"], row["buckets"]["WITH"]["n"]),
                             ("UNKNOWN", 1, 0))
            self.assertEqual(result["matrix"][0], prior["matrix"][0])
            (schedule / "release_schedule_events.csv").write_bytes(events + b"bad")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                run_event_refresh(schedule, contents, prior)
