# Core-5 macro trade test

**Status: `NOT_VERIFIED` — no trade/macro classifications or performance tests were run.**

## Availability and execution status

- Predefined instrument × macro tests: **19**; executed: **0**; statistical recommendations: **0**.
- `reference/history/macro/` is absent/empty. The allowed separate research container/job was not provisioned or attested, so no public downloads were made.
- The verified V2 exports provide 204 trade-result rows: 199 strict WIN/LOSS labels (128 WIN, 71 LOSS) and 5 SCRATCH outcomes. SCRATCH records are not recast as WIN or LOSS.
- Analysis script commit: `0b7d14ae6c9196c195a4c5d994119307b3a39193`.
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

## Fixed test matrix

| Instrument | Macro | Preregistered status | Result |
|---|---|---|---|
| EURUSD | USD strength basket excluding EUR | PRIMARY | `NOT_VERIFIED` |
| EURUSD | VIX risk-off | EXPLORATORY | `NOT_VERIFIED` |
| EURUSD | Brent spot oil | EXPLORATORY | `NOT_VERIFIED` |
| EURUSD | US 2-year yield (DGS2) | EXPLORATORY | `NOT_VERIFIED` |
| EURUSD | Scheduled-event proximity | EXPLORATORY | `NOT_VERIFIED` |
| GBPUSD | USD strength basket excluding GBP | PRIMARY | `NOT_VERIFIED` |
| GBPUSD | VIX risk-off | EXPLORATORY | `NOT_VERIFIED` |
| GBPUSD | Brent spot oil | EXPLORATORY | `NOT_VERIFIED` |
| GBPUSD | US 2-year yield (DGS2) | EXPLORATORY | `NOT_VERIFIED` |
| GBPUSD | Scheduled-event proximity | EXPLORATORY | `NOT_VERIFIED` |
| GOLD | US 10-year real yield (DFII10) | EXPLORATORY | `NOT_VERIFIED` |
| GOLD | USD strength basket | EXPLORATORY | `NOT_VERIFIED` |
| GOLD | VIX risk-off | EXPLORATORY | `NOT_VERIFIED` |
| GOLD | US 2-year yield (DGS2) | EXPLORATORY | `NOT_VERIFIED` |
| SP500 | VIX / VIX3M risk-off | EXPLORATORY | `NOT_VERIFIED` |
| SP500 | High-yield spread (BAMLH0A0HYM2) | EXPLORATORY | `NOT_VERIFIED` |
| DAX | VIX risk-off | EXPLORATORY | `NOT_VERIFIED` |
| DAX | EURUSD 10-day change | EXPLORATORY | `NOT_VERIFIED` |
| DAX | Brent spot oil | EXPLORATORY | `NOT_VERIFIED` |

## Frozen rules and unavailable observations

No rule was changed after reviewing outcomes. If data are later provisioned in the permitted isolated job, apply REV4 exactly: `S` is the sum of ten daily log returns for price/FX/USD/oil series, or latest minus ten observations earlier in percentage points for yields/spreads; `sigma` is the standard deviation of that S over the trailing 250 observations. Fewer than 250 valid observations, missing timestamps, or unavailable as-published FRED/ALFRED vintages means UNKNOWN. USD_UP/DOWN requires S > +0.5 sigma / S < -0.5 sigma; risk-off is VIX/VIX3M > 1 or VIX > 1.25 times its trailing 20-day median. All remaining signs, headwinds, weekly bootstrap, and decision thresholds are those in the controlling REV4 prompt.

- Every trade–macro pair is currently `UNKNOWN`; no WITH/AGAINST/NEUTRAL bucket, win rate, mean/total R, weekly bootstrap CI, removal fraction, or driver-agreement statistic can be calculated.
- Price-series daily close conventions and UTC close timestamps: `UNKNOWN` (no series downloaded).
- FRED observation publication timestamps and ALFRED vintages: `UNKNOWN` (no vintage data supplied/downloaded).
- Official Fed, ECB, BoE, and BLS release dates/times, time zones, and page publication/update dates: `UNKNOWN` (no schedule pages downloaded).
- Macro histories, price histories, release schedules, and their hashes: `NOT_PROVIDED`; no future or unpublished values were substituted.
- These unavailable market/release inputs have no hashes because they were not supplied or downloaded.
- US–German/US–UK 2-year spreads remain `NOT_TESTED_DATA_UNAVAILABLE`; other candidate drivers without a fixed REV4 rule remain `NOT_TESTED`.

There are 19 predefined tests; multiple comparisons would produce chance differences even if all drivers had no effect. These data do not support any gate recommendation. V2's verified closed-trade sample is small, and historical removal of losing trades would only be a partial counterfactual, not a measured future gain. No macro gate is executable V3 policy without explicit owner adoption and forward DEMO validation.
