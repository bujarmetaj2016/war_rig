# Core-5 V3 macro profile proposal

**Status: `PROPOSAL_ONLY / OWNER_SELECTION_REQUIRED`.** The verified ALFRED
subset yielded one exploratory candidate, not a confirmed gate. The V5
design's macro freshness policies are unselected and deny; this report does
not select or activate them.

Source citations are relative to `reference/v2_snapshot/`; hashes are pinned in
[the findings](CORE5_MACRO_FINDINGS.md) and manifest. `V2_PARITY` is a research
comparison baseline, not permission to enable these gates in V3.

| Instrument | V2_PARITY | Candidate inputs and proposed role | Evidence status / rationale |
|---|---|---|---|
| EURUSD | Directional signal suppressed at climate `<40`; `HALF` at `40 ≤ climate < 60`; `FULL` at `≥60`. `size_mult=0.5` is telemetry, not actual stake (`backtest_ml/live_inference.py:495-508`; `execution/governor.py:286-350,1365-1372`). | USD-strength basket excluding EUR — `MODEL_FEATURE`; VIX, US 2-year yield, Brent and event proximity — `LOG_ONLY`; US-German 2-year spread — `LOG_ONLY` pending a point-in-time source. | Primary USD-basket test is `NOT_VERIFIED`; DXY contains EUR. |
| GBPUSD | Directional signal suppressed at climate `<40`; `HALF` at `40 ≤ climate < 60`; `FULL` at `≥60`. `size_mult=0.5` is telemetry, not actual stake (same source ranges as EURUSD). | USD-strength basket excluding GBP — `MODEL_FEATURE`; VIX, US 2-year yield, Brent and event proximity — `LOG_ONLY`; US-UK 2-year spread — `LOG_ONLY` pending a point-in-time source. | Primary USD-basket test is `NOT_VERIFIED`; DXY contains GBP. |
| GOLD/XAUUSD | Macro model features only for entry; no climate gate (`backtest_ml/live_inference.py:487-493`; `execution/governor.py:618-620,849-867`). | DFII10, independent USD strength and VIX — `MODEL_FEATURE`; event proximity and DGS2 — `LOG_ONLY`. | Exploratory tests are `NOT_VERIFIED`; `T10YIE` is not tested. |
| SP500/US500 | Directional signal suppressed at climate `<40`; Governor separately denies if VIX z-score is unavailable or `≥2.0` by default (`backtest_ml/live_inference.py:510-521`; `execution/governor.py:618-620,844-882`). | VIX/VIX3M, DGS10 change, and high-yield spread — `MODEL_FEATURE`; event proximity — `LOG_ONLY`. | Tests are `NOT_VERIFIED`; DGS10 has no fixed Part 4 trade-classification rule. |
| GER40/DAX | Directional signal suppressed at climate `<40` (`backtest_ml/live_inference.py:510-521`). | VIX, EURUSD and Brent — `MODEL_FEATURE`; Bund yield, prior US500 session and event proximity — `LOG_ONLY` pending data/rules. | Tests are `NOT_VERIFIED`; Bund and prior-US500 are not tested. The exporter sign is regime-dependent. |

| Separate candidate change | Evidence and selection status |
|---|---|
| Correct or replace the direction-agnostic EURUSD/GBPUSD climate gate. | Strong USD lowers climate just as much for SELL as BUY (`backtest_ml/macro_confidence.py:157-170`; `backtest_ml/live_inference.py:495-508`). Any replacement requires verified trade evidence and `OWNER_SELECTION_REQUIRED`. |
| Retain, retire or replace the DAX/SP500 climate floors or the independent SP500 panic gate. | The source verifies the V2 baseline, not incremental performance; any change is `OWNER_SELECTION_REQUIRED`. |
| Correct the FX `HALF` telemetry label or introduce actual stake scaling. | V2 did not apply the multiplier; any change is `OWNER_SELECTION_REQUIRED`. A real size change also needs end-to-end validation. |
| Evaluate an EURUSD DGS2 `ENTRY_GATE` in forward DEMO. | `EXPLORATORY / OWNER_SELECTION_REQUIRED`. The standalone REV4 rule passes: WITH n=22, mean +0.149 R; AGAINST n=53, mean −0.130 R, total −6.914 R. The AGAINST 95% weekly CI [−0.425, +0.229] crosses zero. The primary USD basket was unavailable, so DGS2 is strongest only among eligible family members tested. See [trade results](CORE5_MACRO_TRADE_TEST.md). |

**No gate is confirmed and no `SIZE_MODIFIER` is proposed.** Every
input above remains a candidate for an owner-selected profile and frozen
forward/DEMO validation. If adopted later, it must use completed observations,
as-published FRED/ALFRED vintages, explicit source close conventions and
per-instrument freshness policies. Unknown or late data must not silently
become a neutral pass. The event window is a calendar/timing observation, not a
directional signal.

V2's climate HALF value did not scale actual FX stake in Governor. V3 must not
inherit that label as a `SIZE_MODIFIER` without an explicit owner decision and
an end-to-end sizing test. Historical removal of losing trades is not an
estimate of future gains; capital use and later signal selection change under
any gate.
