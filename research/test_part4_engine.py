import hashlib
import unittest
from datetime import date, datetime, time, timedelta, timezone

from research.part4_engine import (
    ALL_TESTS,
    LEGACY_TESTS,
    MATRIX_DISCREPANCY,
    AlfredProvenance,
    AlfredSeries,
    AlfredVintage,
    OfficialCalendar,
    PriceBar,
    PriceProvenance,
    PriceSeries,
    Reading,
    ScheduleProvenance,
    ScheduledEvent,
    SeriesValue,
    Trade,
    alfred_momentum_reading,
    classify,
    compare,
    event_reading,
    momentum_reading,
    price_momentum_reading,
    risk_off_reading,
    run_all_tests,
    usd_basket_reading,
    weekly_cluster_bootstrap_ci,
)


UTC = timezone.utc
ENTRY = datetime(2026, 6, 10, 12, tzinfo=UTC)
SHA = hashlib.sha256(b"synthetic provenance").hexdigest()


def price_series(name, days, values, *, complete=None, expected_dates=()):
    complete = complete or [True] * len(days)
    bars = tuple(
        PriceBar(datetime.combine(day, time(16), UTC), value, is_complete)
        for day, value, is_complete in zip(days, values, complete)
    )
    provenance = PriceProvenance(
        source="synthetic test source",
        source_url="https://finance.yahoo.com/",
        downloaded_at_utc=datetime(2026, 6, 11, tzinfo=UTC),
        close_convention="synthetic UTC 16:00 close",
        sha256=SHA,
    )
    calendar = tuple(expected_dates) or tuple(days)
    return PriceSeries(name, bars, provenance, calendar)


def valid_calendar_provenance():
    host_and_url = {
        "FOMC": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "ECB": "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html",
        "BOE": "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates",
        "US_CPI": "https://www.bls.gov/schedule/news_release/cpi.htm",
        "US_NFP": "https://www.bls.gov/schedule/news_release/empsit.htm",
    }
    return {
        event_type: ScheduleProvenance(
            event_type,
            url,
            date(2026, 1, 1),
            datetime(2026, 6, 11, tzinfo=UTC),
            SHA,
        )
        for event_type, url in host_and_url.items()
    }


def make_trade(index, bucket, value, *, instrument="EURUSD"):
    entry = datetime(2026, 1, 5, tzinfo=UTC) + timedelta(days=index * 7)
    return Trade(
        trade_id=f"trade-{index}",
        instrument=instrument,
        direction="BUY",
        entry_time_utc=entry,
        outcome="WIN" if value > 0 else "LOSS",
        r_multiple=value,
    )


class Rev4MatrixTests(unittest.TestCase):
    def test_preserves_19_legacy_rows_and_adds_three_required_events(self):
        self.assertEqual(len(LEGACY_TESTS), 19)
        self.assertEqual(len(ALL_TESTS), 22)
        self.assertEqual(
            [spec.instrument for spec in LEGACY_TESTS[-5:]],
            ["SP500", "SP500", "DAX", "DAX", "DAX"],
        )
        self.assertEqual(
            [spec.instrument for spec in ALL_TESTS[-3:]],
            ["GOLD", "SP500", "DAX"],
        )
        self.assertIn("19 tests", MATRIX_DISCREPANCY)
        self.assertIn("22 effective", MATRIX_DISCREPANCY)

    def test_event_classification_uses_event_as_against(self):
        spec = next(row for row in ALL_TESTS if row.test_id == "EURUSD_SCHEDULED_EVENT")
        trade = make_trade(0, "", 1)
        self.assertEqual(classify(spec, trade, Reading("EVENT_WINDOW")).classification, "AGAINST")
        self.assertEqual(classify(spec, trade, Reading("NO_EVENT")).classification, "WITH")


class AlfredAvailabilityTests(unittest.TestCase):
    def make_series(self, vintages):
        return AlfredSeries(
            AlfredProvenance(
                "DGS2",
                ("https://api.stlouisfed.org/fred/series/observations",),
                datetime(2026, 6, 11, tzinfo=UTC),
                SHA,
            ),
            tuple(vintages),
        )

    def test_lookahead_value_published_after_entry_is_never_used(self):
        series = self.make_series(
            [AlfredVintage(date(2026, 6, 8), date(2026, 6, 10), date(2026, 6, 30), 4.0)]
        )
        self.assertEqual(series.snapshot(ENTRY), ())

    def test_earlier_vintage_is_used_instead_of_future_revision(self):
        series = self.make_series(
            [
                AlfredVintage(date(2026, 6, 8), date(2026, 6, 9), date(2026, 6, 9), 3.5),
                AlfredVintage(date(2026, 6, 8), date(2026, 6, 10), date(2026, 6, 30), 4.5),
            ]
        )
        snapshot = series.snapshot(ENTRY)
        self.assertEqual(snapshot[0].value, 3.5)

    def test_entry_day_revision_does_not_invalidate_prior_eligible_vintage(self):
        series = self.make_series(
            [
                AlfredVintage(date(2026, 6, 8), date(2026, 6, 9), date(2026, 6, 9), 3.5),
                AlfredVintage(date(2026, 6, 8), date(2026, 6, 10), date(2026, 6, 30), 4.5),
            ]
        )
        entry = datetime(2026, 6, 10, 8, tzinfo=UTC)
        self.assertEqual(series.snapshot(entry)[0].value, 3.5)

    def test_observation_date_does_not_substitute_for_publication_date(self):
        series = self.make_series(
            [AlfredVintage(date(2026, 6, 1), date(2026, 6, 4), date(2026, 6, 30), 3.1)]
        )
        self.assertEqual(series.snapshot(datetime(2026, 6, 3, 10, tzinfo=UTC)), ())
        self.assertEqual(
            series.snapshot(datetime(2026, 6, 5, 10, tzinfo=UTC))[0].value, 3.1
        )

    def test_csv_loader_requires_hash_and_exact_vintage_schema(self):
        payload = (
            "date,realtime_start,realtime_end,value\n"
            "2026-06-08,2026-06-09,2026-06-30,3.5\n"
        ).encode()
        actual_hash = hashlib.sha256(payload).hexdigest()
        series = AlfredSeries.from_csv_bytes(
                payload,
                expected_sha256=actual_hash,
                series_id="DGS2",
                source_urls=("https://api.stlouisfed.org/fred/series/observations",),
                downloaded_at_utc=datetime(2026, 6, 11, tzinfo=UTC),
            )
        self.assertEqual(series.snapshot(ENTRY)[0].value, 3.5)
        with self.assertRaises(ValueError):
            AlfredSeries.from_csv_bytes(
                payload,
                expected_sha256=SHA,
                series_id="DGS2",
                source_urls=("https://api.stlouisfed.org/fred/series/observations",),
                downloaded_at_utc=datetime(2026, 6, 11, tzinfo=UTC),
            )

    def test_missing_latest_alfred_oil_publication_uses_prior_close(self):
        days = tuple(date(2025, 1, 1) + timedelta(days=index) for index in range(261))
        vintages = tuple(
            AlfredVintage(day, date(2025, 1, 1), date(2026, 12, 31), 80.0 + index * 0.1)
            for index, day in enumerate(days[:-1])
        )
        series = AlfredSeries(
            AlfredProvenance(
                "DCOILBRENTEU",
                ("https://api.stlouisfed.org/fred/series/observations",),
                datetime(2026, 6, 11, tzinfo=UTC),
                SHA,
            ),
            vintages,
            days,
        )
        entry = datetime.combine(days[-1] + timedelta(days=1), time(12), UTC)
        snapshot = series.snapshot(entry)
        self.assertEqual(snapshot[-1].observation_date, days[-2])
        self.assertNotEqual(
            alfred_momentum_reading(series, entry, price_series=True).code, "UNKNOWN"
        )

    def test_missing_mid_history_spot_close_is_not_bridged(self):
        days = tuple(date(2025, 1, 1) + timedelta(days=index) for index in range(261))
        included = days[:-1]
        vintages = tuple(
            AlfredVintage(day, date(2025, 1, 1), date(2026, 12, 31), 80.0 + index * 0.1)
            for index, day in enumerate(included)
            if index != 100
        )
        series = AlfredSeries(
            AlfredProvenance(
                "DCOILBRENTEU",
                ("https://api.stlouisfed.org/fred/series/observations",),
                datetime(2026, 6, 11, tzinfo=UTC),
                SHA,
            ),
            vintages,
            days,
        )
        entry = datetime.combine(days[-1] + timedelta(days=1), time(12), UTC)
        self.assertEqual(
            alfred_momentum_reading(series, entry, price_series=True).code, "UNKNOWN"
        )


class PriceAndClassificationTests(unittest.TestCase):
    def test_incomplete_price_bar_is_not_selected(self):
        days = (date(2026, 6, 8), date(2026, 6, 9), date(2026, 6, 10))
        series = price_series(
            "VIX",
            days,
            (20.0, 21.0, 100.0),
            complete=(True, True, False),
            expected_dates=days,
        )
        # Entry after the incomplete bar: it is excluded and the prior
        # completed close is used rather than the forming close.
        rows = series.completed_before(datetime(2026, 6, 11, tzinfo=UTC))
        self.assertEqual(rows[-1], (date(2026, 6, 9), 21.0))
        # Before the incomplete session, the previous completed close is used.
        rows = series.completed_before(datetime(2026, 6, 10, 12, tzinfo=UTC))
        self.assertEqual(rows[-1], (date(2026, 6, 9), 21.0))

    def test_completed_same_day_price_bar_before_entry_is_included(self):
        days = tuple(date(2025, 1, 1) + timedelta(days=index) for index in range(260))
        values = [100.0 + index * 0.1 for index in range(len(days))]
        values[-1] *= 1.1
        series = price_series("EURUSD", days, values)
        entry = datetime.combine(days[-1], time(18), UTC)
        self.assertEqual(series.completed_before(entry)[-1][0], days[-1])
        self.assertNotEqual(price_momentum_reading(series, entry).code, "UNKNOWN")

    def test_missing_histories_and_short_baseline_are_unknown(self):
        short = [
            (date(2025, 1, 1) + timedelta(days=index), 100.0 + index)
            for index in range(259)
        ]
        reading = momentum_reading(
            short,
            entry_date_utc=date(2026, 1, 1),
            price_series=False,
            label="short",
        )
        self.assertEqual(reading.code, "UNKNOWN")
        self.assertEqual(
            momentum_reading(
                [],
                entry_date_utc=date(2026, 1, 1),
                price_series=True,
                label="missing",
            ).code,
            "UNKNOWN",
        )

    def test_fewer_than_250_baseline_s_observations_is_unknown(self):
        points = [
            SeriesValue(date(2025, 1, 1) + timedelta(days=i), 3.0 + (i % 7) * 0.01)
            for i in range(260)
        ]
        # 260 inputs produce 250 S observations; dropping one leaves 249.
        points.pop(-2)
        reading = momentum_reading(
            points,
            entry_date_utc=date(2026, 1, 1),
            price_series=False,
            label="DGS2",
        )
        self.assertEqual(reading.code, "UNKNOWN")
        self.assertIn("250", reading.reason)

    def test_usd_basket_quote_inversion_turns_falling_gbpusd_into_usd_strength(self):
        # 260 price levels provide one anchor and exactly 250 ten-return S
        # observations (259 daily returns, 250 overlapping ten-day windows).
        days = tuple(date(2025, 1, 1) + timedelta(days=index) for index in range(260))
        pairs = {}
        pair_names = ("USDJPY", "GBPUSD", "USDCAD", "USDCHF", "AUDUSD", "EURUSD")
        for pair in pair_names:
            if pair == "GBPUSD":
                values = [1.5 * (0.999**index) for index in range(len(days))]
            else:
                values = [1.0] * len(days)
            pairs[pair] = price_series(pair, days, values)
        reading = usd_basket_reading(
            pairs,
            datetime(2026, 1, 1, tzinfo=UTC),
            instrument="EURUSD",
        )
        self.assertEqual(reading.code, "UP")
        self.assertGreater(reading.s, 0)

    def test_duplicate_and_missing_observations_are_unknown(self):
        duplicate = [
            (date(2025, 1, 1) + timedelta(days=i), 2.0 + i * 0.001)
            for i in range(260)
        ]
        duplicate[5] = duplicate[4]
        self.assertEqual(
            momentum_reading(
                duplicate,
                entry_date_utc=date(2026, 1, 1),
                price_series=False,
                label="duplicate",
            ).code,
            "UNKNOWN",
        )
        days = tuple(date(2025, 1, 1) + timedelta(days=index) for index in range(261))
        values = [1.0 + index * 0.001 for index in range(len(days))]
        expected = days
        # A missing complete bar on an expected session is not silently forward-filled.
        missing_days = days[:140] + days[141:]
        missing_values = values[:140] + values[141:]
        missing_series = price_series(
            "USDJPY",
            missing_days,
            missing_values,
            expected_dates=expected,
        )
        with self.assertRaises(ValueError):
            missing_series.completed_before(ENTRY)

    def test_usd_basket_mismatched_trading_calendars_are_unknown(self):
        days = [date(2025, 1, 1) + timedelta(days=index) for index in range(261)]
        pairs = {}
        for pair in ("USDJPY", "GBPUSD", "USDCAD", "USDCHF", "AUDUSD", "EURUSD"):
            pair_days = days[1:] if pair == "GBPUSD" else days
            pairs[pair] = price_series(pair, pair_days, [1.0] * len(pair_days))
        self.assertEqual(
            usd_basket_reading(
                pairs,
                datetime(2026, 1, 1, tzinfo=UTC),
                instrument="EURUSD",
            ).code,
            "UNKNOWN",
        )

    def test_risk_off_binary_rule(self):
        days = tuple(date(2025, 1, 1) + timedelta(days=index) for index in range(261))
        vix_values = [20.0] * 260 + [26.0]
        vix3m_values = [25.0] * len(days)
        vix = price_series("VIX", days, vix_values)
        vix3m = price_series("VIX3M", days, vix3m_values)
        entry = datetime.combine(days[-1] + timedelta(days=1), time(12), UTC)
        reading = risk_off_reading(vix, vix3m, entry)
        self.assertEqual(reading.code, "RISK_OFF")

    def test_vix_median_trigger_survives_missing_vix3m(self):
        days = tuple(date(2025, 1, 1) + timedelta(days=index) for index in range(261))
        vix = price_series("VIX", days, [20.0] * 260 + [26.0])
        entry = datetime.combine(days[-1] + timedelta(days=1), time(12), UTC)
        self.assertEqual(risk_off_reading(vix, None, entry).code, "RISK_OFF")

    def test_vix_unavailable_ratio_and_untriggered_median_is_unknown(self):
        days = tuple(date(2025, 1, 1) + timedelta(days=index) for index in range(261))
        vix = price_series("VIX", days, [20.0] * len(days))
        entry = datetime.combine(days[-1] + timedelta(days=1), time(12), UTC)
        self.assertEqual(risk_off_reading(vix, None, entry).code, "UNKNOWN")

    def test_vix_risk_rule_requires_250_valid_s_observations(self):
        days = tuple(date(2025, 1, 1) + timedelta(days=index) for index in range(30))
        vix = price_series("VIX", days, [20.0] * len(days))
        vix3m = price_series("VIX3M", days, [15.0] * len(days))
        entry = datetime.combine(days[-1] + timedelta(days=1), time(12), UTC)
        self.assertEqual(risk_off_reading(vix, vix3m, entry).code, "UNKNOWN")


class CalendarAndComparisonTests(unittest.TestCase):
    def test_event_window_requires_official_as_known_provenance(self):
        provenance = valid_calendar_provenance()
        events = (
            ScheduledEvent(
                "US_CPI",                 date(2026, 6, 11), time(7, 30), "America/New_York"
            ),
        )
        calendar = OfficialCalendar(events, provenance, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(calendar.event_window(ENTRY), "EVENT_WINDOW")
        unknown = dict(provenance)
        unknown["BOE"] = ScheduleProvenance(
            "BOE",
            "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates",
            date(2026, 6, 10),
            datetime(2026, 6, 11, tzinfo=UTC),
            SHA,
        )
        calendar = OfficialCalendar(events, unknown, date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(event_reading(calendar, ENTRY).code, "UNKNOWN")

    def test_bucket_size_rule_and_unknown_not_tested_handling(self):
        spec = LEGACY_TESTS[0]
        observations = []
        for index in range(19):
            trade = make_trade(index, "WITH", 1.0)
            observations.append(classify(spec, trade, Reading("DOWN")))
        for index in range(19, 39):
            trade = make_trade(index, "AGAINST", -1.0)
            observations.append(classify(spec, trade, Reading("UP")))
        unknown = make_trade(39, "", -1.0)
        observations.append(classify(spec, unknown, Reading.unknown("synthetic missing")))
        not_tested = make_trade(40, "", -1.0)
        observations.append(classify(spec, not_tested, Reading.not_tested()))
        result = compare(spec.test_id, observations, seed=7)
        self.assertEqual(result.status, "INSUFFICIENT_SAMPLE")
        self.assertFalse(result.gate_recommended)
        self.assertEqual(result.unknown_n, 1)
        self.assertEqual(result.not_tested_n, 1)
        self.assertEqual(result.buckets["WITH"].n, 19)
        self.assertEqual(result.buckets["AGAINST"].n, 20)

    def test_weekly_bootstrap_is_deterministic(self):
        trades = [
            make_trade(index, "", 1.0 if index % 2 else -0.5)
            for index in range(20)
        ]
        self.assertEqual(
            weekly_cluster_bootstrap_ci(trades, seed=123, replicates=500),
            weekly_cluster_bootstrap_ci(trades, seed=123, replicates=500),
        )

    def test_comparison_recommends_only_when_fixed_rule_passes(self):
        spec = LEGACY_TESTS[0]
        observations = []
        for index in range(20):
            observations.append(
                classify(spec, make_trade(index, "", 1.0), Reading("DOWN"))
            )
        for index in range(20, 40):
            observations.append(
                classify(spec, make_trade(index, "", -1.0), Reading("UP"))
            )
        result = compare(spec.test_id, observations, seed=4)
        self.assertEqual(result.status, "EVALUATED")
        self.assertTrue(result.gate_recommended)
        self.assertTrue(result.gate_confirmed)
        self.assertIn("some differences will appear by chance", result.multiple_testing_statement)

    def test_overlapping_family_only_recommends_its_strongest_member(self):
        trades = [
            make_trade(index, "", 1.0 if index < 30 else -1.0)
            for index in range(60)
        ]
        usd_id = "EURUSD_USD_BASKET_EX_EUR"
        dgs2_id = "EURUSD_DGS2"
        readings = {
            usd_id: {
                trade.trade_id: Reading("DOWN" if index < 30 else "UP")
                for index, trade in enumerate(trades)
            },
            dgs2_id: {
                trade.trade_id: Reading(
                    "DOWN" if index < 20 or 30 <= index < 40 else "UP"
                )
                for index, trade in enumerate(trades)
            },
        }
        results = run_all_tests(trades, readings, seed=3)
        by_id = {result.test_id: result for result in results}
        self.assertTrue(by_id[usd_id].gate_recommended)
        self.assertFalse(by_id[dgs2_id].gate_recommended)
        self.assertEqual(by_id[usd_id].family, "FED_REPRICING_OVERLAP")
        self.assertEqual(by_id[dgs2_id].family, "FED_REPRICING_OVERLAP")


if __name__ == "__main__":
    unittest.main()
