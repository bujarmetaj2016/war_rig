# Core-5 macro trade test

**Status: `PARTIAL_TRADE_TEST` — checksum-verified inputs only.**

**Sample limit up front:** EURUSD 101, DAX 44, GBPUSD 19, GOLD 18, SP500 17 strict closed WIN/LOSS outcomes. With 20 required in each comparison bucket, GBPUSD, GOLD and SP500 cannot support gate recommendations; report descriptive results where data permit. EURUSD and DAX are not guaranteed sufficient buckets.

## Availability and execution status

- REV4 comparisons: **22**; fully or partially classified: **8**. The remaining rows have no verified input.
- The verified V2 exports provide 204 trade-result rows: 199 strict WIN/LOSS labels (128 WIN, 71 LOSS) and 5 SCRATCH outcomes. SCRATCH records are not recast as WIN or LOSS.
- Analysis script commit: `63ead5fb721595a4173f815ea2daf0ce4da5a9cc`.
- Trade-results input: `reference/v2_outcomes/trade_results.csv` SHA-256 `ecd3e98ceda9806d86ddf35ac1dba5f50d9e790d7ad7b1223199ea163676bd7c`.
- V2 reference manifest SHA-256 `a06ac2de31fcce5436d9c975ea7b0cf872a050a6b7d475e2e4b2f09fdff1a38b`.
- Verified prediction exports (integrity inputs only; not used for trade counts or tests):
  - `reference/v2_predictions/ml_signal_predictions.csv` SHA-256 `6ad2e22ddd2066e81ef8b06252f8a137e7436992e62ef51a7d96faa1efc2c632`
  - `reference/v2_predictions/ml_signal_v2_feature_snapshots.csv` SHA-256 `ff9598870378378cecea2acfab008bdf80f2393b98936e9febddd376aee08285`
  - `reference/v2_predictions/ml_signal_v2_model_registry.csv` SHA-256 `a1a40f7b000a44d49e6df93a6d226b062a6d799d0120fc5dcfc1e499a01db8c6`
  - `reference/v2_predictions/ml_signal_v2_shadow_predictions.csv` SHA-256 `7e5aacc69107d87993e8b01a21e6a3e85014239ca01bb2e37bd16e5b3e47f5d6`
  - `reference/v2_predictions/ml_signal_v2_training_examples.csv` SHA-256 `ead74bc41b2003629cf0f54ebe9dce7add5028cc5eecd55001d1feaec821e4be`
  - `reference/v2_predictions/ml_signal_v2_training_runs.csv` SHA-256 `5c04e73fd804b482a51628240e93ebb98138dd8bc41c3877cf6affa0c0e12724`
  - `reference/v2_predictions/ml_suppressed_signal_replay_results.csv` SHA-256 `a4868a5424ee9a0108ec7204cc7b1365f70d96a213f325df9b5cc28d0a1822c1`
  - `reference/v2_predictions/operational_missed_signal_audit_results.csv` SHA-256 `fe70fc4f36acfec0c6974eb429f1a02022b2cf596215467bd409f2f9e63b28c6`
  - `reference/v2_predictions/signal_analysis_state_snapshots.csv` SHA-256 `170bb70365a24a9daaa6207e0219e355b9ea019a1de231336c18edbff24e865b`
  - `reference/v2_predictions/signals.csv` SHA-256 `e3dc433c866fffe0f8ba7a2043a78e2a2635c6832b62f3f0ee6cd2c490f4aa3c`
- The five instruments have the following full strict-label counts before any macro availability exclusions:

| Instrument | WIN | LOSS | Strict WIN/LOSS n |
|---|---:|---:|---:|
| EURUSD | 63 | 38 | 101 |
| GBPUSD | 8 | 11 | 19 |
| GOLD | 12 | 6 | 18 |
| SP500 | 12 | 5 | 17 |
| DAX | 33 | 11 | 44 |

The GBPUSD (n=19), GOLD (n=18), and SP500 (n=17) totals are already below the fixed 20-trade bucket threshold before any WITH/AGAINST split. EURUSD and DAX still require at least 20 usable trades in both buckets.

## Fixed test matrix (22 comparisons)

| Instrument | Macro | Preregistered status | Result |
|---|---|---|---|
| EURUSD | USD strength basket excluding EUR | PRIMARY | `UNKNOWN` |
| EURUSD | VIX risk-off | EXPLORATORY | `UNKNOWN` |
| EURUSD | Brent spot oil | EXPLORATORY | `EVALUATED` |
| EURUSD | US 2-year yield (DGS2) | EXPLORATORY | `EVALUATED` |
| EURUSD | Scheduled-event proximity | EXPLORATORY | `UNKNOWN` |
| GBPUSD | USD strength basket excluding GBP | PRIMARY | `UNKNOWN` |
| GBPUSD | VIX risk-off | EXPLORATORY | `UNKNOWN` |
| GBPUSD | Brent spot oil | EXPLORATORY | `INSUFFICIENT_SAMPLE` |
| GBPUSD | US 2-year yield (DGS2) | EXPLORATORY | `INSUFFICIENT_SAMPLE` |
| GBPUSD | Scheduled-event proximity | EXPLORATORY | `UNKNOWN` |
| GOLD | US 10-year real yield (DFII10) | EXPLORATORY | `INSUFFICIENT_SAMPLE` |
| GOLD | USD strength basket | EXPLORATORY | `UNKNOWN` |
| GOLD | VIX risk-off | EXPLORATORY | `UNKNOWN` |
| GOLD | US 2-year yield (DGS2) | EXPLORATORY | `INSUFFICIENT_SAMPLE` |
| SP500 | VIX / VIX3M risk-off | EXPLORATORY | `UNKNOWN` |
| SP500 | High-yield spread (BAMLH0A0HYM2) | EXPLORATORY | `INSUFFICIENT_SAMPLE` |
| DAX | VIX risk-off | EXPLORATORY | `UNKNOWN` |
| DAX | EURUSD 10-day change | EXPLORATORY | `UNKNOWN` |
| DAX | Brent spot oil | EXPLORATORY | `INSUFFICIENT_SAMPLE` |
| GOLD | Scheduled-event proximity | EXPLORATORY | `UNKNOWN` |
| SP500 | Scheduled-event proximity | EXPLORATORY | `UNKNOWN` |
| DAX | Scheduled-event proximity | EXPLORATORY | `UNKNOWN` |

## Frozen rules and unavailable observations

No rule was changed after reviewing outcomes. If data are later provisioned in the permitted isolated job, apply REV4 exactly: `S` is the sum of ten daily log returns for price/FX/USD/oil series, or latest minus ten observations earlier in percentage points for yields/spreads; `sigma` is the standard deviation of that S over the trailing 250 observations. Fewer than 250 valid observations, missing timestamps, or unavailable as-published FRED/ALFRED vintages means UNKNOWN. Use the vintage in force on the UTC day before entry; a vintage first dated on the entry date is unavailable, and an observation with no eligible earlier vintage is UNKNOWN. USD_UP/DOWN requires S > +0.5 sigma / S < -0.5 sigma; risk-off is VIX/VIX3M > 1 or VIX > 1.25 times its trailing 20-day median. All remaining signs, headwinds, weekly bootstrap, and decision thresholds are those in the controlling REV4 prompt.

- Unverified trade–macro observations are `UNKNOWN` and excluded from statistics.
- Price-series daily close conventions and UTC close timestamps: `UNKNOWN` (no verified price history delivered).
- Verified ALFRED vintages are recorded in the results below. Publication is date-granular; same-day releases are not assumed available.
- Fed, ECB, BoE and BLS schedules: `UNKNOWN` until official as-known coverage is verified.
- No future or unpublished values were substituted.
- US–German/US–UK 2-year spreads remain `NOT_TESTED_DATA_UNAVAILABLE`; other candidate drivers without a fixed REV4 rule remain `NOT_TESTED`.

There are 22 REV4 comparisons, including five event comparisons; with 22 comparisons, some differences can occur by chance even if all drivers had no effect. V2's verified closed-trade sample is small, and historical removal of losing trades would only be a partial counterfactual, not a measured future gain. No macro gate is executable V3 policy without explicit owner adoption and forward DEMO validation.

## Latest run scope

Only the three Brent comparisons were rerun; the other 19 rows retain their previous results or UNKNOWN status.

## Comparisons with verified inputs

Full precision, UTC source timestamps, CSV hashes, URLs, family agreement and DAX descriptive split: [machine-readable results](CORE5_MACRO_TRADE_RESULTS.json).

| Test | Bucket | n | Win rate | Mean R | Total R | Weekly 95% CI |
|---|---|---:|---:|---:|---:|---|
| EURUSD_BRENT_SPOT | WITH | 30 | 0.600 | 0.145 | 4.339 | [-0.267, 0.561] |
| EURUSD_BRENT_SPOT | AGAINST | 44 | 0.568 | -0.014 | -0.595 | [-0.314, 0.346] |
| EURUSD_BRENT_SPOT | NEUTRAL | 27 | 0.741 | 0.290 | 7.836 | [0.018, 0.607] |
| EURUSD_DGS2 | WITH | 22 | 0.636 | 0.149 | 3.272 | [-0.218, 0.450] |
| EURUSD_DGS2 | AGAINST | 53 | 0.491 | -0.130 | -6.914 | [-0.425, 0.229] |
| EURUSD_DGS2 | NEUTRAL | 26 | 0.885 | 0.586 | 15.223 | [0.357, 0.799] |
| GBPUSD_BRENT_SPOT | WITH | 8 | 0.500 | -0.069 | -0.548 | [-0.756, 0.689] |
| GBPUSD_BRENT_SPOT | AGAINST | 8 | 0.375 | -0.123 | -0.988 | [-0.792, 0.845] |
| GBPUSD_BRENT_SPOT | NEUTRAL | 3 | 0.333 | -0.383 | -1.148 | [-0.986, -0.081] |
| GBPUSD_DGS2 | WITH | 5 | 0.600 | 0.068 | 0.340 | [-0.625, 0.745] |
| GBPUSD_DGS2 | AGAINST | 4 | 0.250 | -0.380 | -1.519 | [-0.990, 0.837] |
| GBPUSD_DGS2 | NEUTRAL | 10 | 0.400 | -0.151 | -1.505 | [-0.760, 0.441] |
| GOLD_DFII10 | WITH | 5 | 0.400 | -0.199 | -0.997 | [-0.996, 0.983] |
| GOLD_DFII10 | AGAINST | 5 | 1.000 | 0.491 | 2.457 | [0.411, 0.670] |
| GOLD_DFII10 | NEUTRAL | 8 | 0.625 | 0.321 | 2.570 | [-0.555, 0.818] |
| GOLD_DGS2 | WITH | 5 | 0.400 | -0.289 | -1.448 | [-0.989, 0.177] |
| GOLD_DGS2 | AGAINST | 8 | 0.875 | 0.525 | 4.202 | [0.419, 0.617] |
| GOLD_DGS2 | NEUTRAL | 5 | 0.600 | 0.255 | 1.276 | [-1.004, 1.643] |
| SP500_HY_SPREAD | WITH | 4 | 0.750 | 0.272 | 1.088 | [-0.559, 0.792] |
| SP500_HY_SPREAD | AGAINST | 6 | 0.833 | 0.286 | 1.715 | [-0.369, 0.566] |
| SP500_HY_SPREAD | NEUTRAL | 7 | 0.571 | -0.062 | -0.434 | [-0.593, 0.438] |
| DAX_BRENT_SPOT | WITH | 21 | 0.714 | 0.290 | 6.082 | [-0.131, 0.699] |
| DAX_BRENT_SPOT | AGAINST | 16 | 0.750 | 0.305 | 4.883 | [-0.082, 0.631] |
| DAX_BRENT_SPOT | NEUTRAL | 7 | 0.857 | 0.328 | 2.298 | [0.073, 0.702] |

| Test | Unknown n | Removed trade fraction | Removed R fraction | Gate |
|---|---:|---:|---:|---|
| EURUSD_BRENT_SPOT | 0 | 0.436 | -0.051 | exploratory, unconfirmed |
| EURUSD_DGS2 | 0 | 0.525 | -0.597 | exploratory, unconfirmed |
| GBPUSD_BRENT_SPOT | 0 | 0.421 | 0.368 | no |
| GBPUSD_DGS2 | 0 | 0.211 | 0.566 | no |
| GOLD_DFII10 | 0 | 0.278 | 0.610 | no |
| GOLD_DGS2 | 0 | 0.444 | 1.043 | no |
| SP500_HY_SPREAD | 0 | 0.353 | 0.724 | no |
| DAX_BRENT_SPOT | 0 | 0.364 | 0.368 | no |

`exploratory, unconfirmed` means the historical comparison passed among eligible tested family members; it is not confirmed or authorized policy. When the primary USD basket is unavailable, the USD/rates family comparison is incomplete. Brent spot uses numeric ALFRED observations in force on the UTC day before entry; no separate session or futures roll calendar is required.
