# Core-5 V3 macro profile proposal

**Status: `PROPOSAL_ONLY / OWNER_SELECTION_REQUIRED`.** The verified ALFRED
subset yielded one primary EURUSD candidate and one exploratory EURUSD
candidate; neither is confirmed. The V5
design's macro freshness policies are unselected and deny; this report does
not select or activate them.

Source citations are relative to `reference/v2_snapshot/`; hashes are pinned in
[the findings](CORE5_MACRO_FINDINGS.md) and manifest. `V2_PARITY` is a research
comparison baseline, not permission to enable these gates in V3.

| Instrument | V2_PARITY | Candidate inputs and proposed role | Evidence status / rationale |
|---|---|---|---|
| EURUSD | Directional signal suppressed at climate `<40`; `HALF` at `40 ≤ climate < 60`; `FULL` at `≥60`. `size_mult=0.5` is telemetry, not actual stake (`backtest_ml/live_inference.py:495-508`; `execution/governor.py:286-350,1365-1372`). | USD-strength basket excluding EUR — `COMPUTE_AND_LOG_ONLY`; VIX, US 2-year yield, Brent and event proximity — `LOG_ONLY`; US-German 2-year spread — `LOG_ONLY` pending a point-in-time source. | Primary USD-basket comparison meets the historical rule but is unconfirmed; use the pre-specified forward rule below. |
| GBPUSD | Directional signal suppressed at climate `<40`; `HALF` at `40 ≤ climate < 60`; `FULL` at `≥60`. `size_mult=0.5` is telemetry, not actual stake (same source ranges as EURUSD). | USD-strength basket excluding GBP — `MODEL_FEATURE`; VIX, US 2-year yield, Brent and event proximity — `LOG_ONLY`; US-UK 2-year spread — `LOG_ONLY` pending a point-in-time source. | The primary USD-basket comparison is `INSUFFICIENT_SAMPLE`. |
| GOLD/XAUUSD | Macro model features only for entry; no climate gate (`backtest_ml/live_inference.py:487-493`; `execution/governor.py:618-620,849-867`). | DFII10, independent USD strength and VIX — `MODEL_FEATURE`; event proximity and DGS2 — `LOG_ONLY`. | Non-event comparisons are `INSUFFICIENT_SAMPLE`; `T10YIE` is not tested. |
| SP500/US500 | Directional signal suppressed at climate `<40`; Governor separately denies if VIX z-score is unavailable or `≥2.0` by default (`backtest_ml/live_inference.py:510-521`; `execution/governor.py:618-620,844-882`). | VIX/VIX3M, DGS10 change, and high-yield spread — `MODEL_FEATURE`; event proximity — `LOG_ONLY`. | VIX/VIX3M and high-yield spread are `INSUFFICIENT_SAMPLE`; DGS10 has no fixed Part 4 rule. |
| GER40/DAX | Directional signal suppressed at climate `<40` (`backtest_ml/live_inference.py:510-521`). | VIX, EURUSD and Brent — `MODEL_FEATURE`; Bund yield, prior US500 session and event proximity — `LOG_ONLY` pending data/rules. | VIX, EURUSD and Brent comparisons are `INSUFFICIENT_SAMPLE`. Bund and prior-US500 are not tested. The exporter sign is regime-dependent. |

| Separate candidate change | Evidence and selection status |
|---|---|
| Correct or replace the direction-agnostic EURUSD/GBPUSD climate gate. | Strong USD lowers climate just as much for SELL as BUY (`backtest_ml/macro_confidence.py:157-170`; `backtest_ml/live_inference.py:495-508`). Any replacement requires verified trade evidence and `OWNER_SELECTION_REQUIRED`. |
| Retain, retire or replace the DAX/SP500 climate floors or the independent SP500 panic gate. | The source verifies the V2 baseline, not incremental performance; any change is `OWNER_SELECTION_REQUIRED`. |
| Correct the FX `HALF` telemetry label or introduce actual stake scaling. | V2 did not apply the multiplier; any change is `OWNER_SELECTION_REQUIRED`. A real size change also needs end-to-end validation. |
| Compute and log the EURUSD ex-EUR USD-basket classification in forward DEMO. | `PRIMARY / COMPUTE_AND_LOG_ONLY / OWNER_SELECTION_REQUIRED`. Strongest eligible USD/rates member: WITH n=29, mean +0.390 R; AGAINST n=45, mean −0.099 R. The AGAINST 95% weekly CI [−0.419, +0.342] crosses zero. |
| Keep EURUSD DGS2 as an exploratory observation, not a second USD/rates gate. | `EXPLORATORY / UNCONFIRMED`. The standalone historical rule passed, but the USD basket had the larger WITH-minus-AGAINST mean-R gap; the family rule supersedes DGS2's standalone candidate status. The classifications agreed on 49 of 101 trades. |
| Keep EURUSD Brent spot as a logged exploratory observation. | `EXPLORATORY / UNCONFIRMED`. WITH n=30, mean +0.145 R; AGAINST n=44, mean −0.014 R, total −0.595 R. The AGAINST 95% weekly CI [−0.314, +0.346] crosses zero. GBPUSD and DAX Brent comparisons were `INSUFFICIENT_SAMPLE`. |

## Pre-specified EURUSD forward rule — V2/V3 DEMO

Before DEMO begins, pin the common UTC enrollment start/end, outcome cutoff,
code and data-source versions, and the unchanged V2/V3 policies. No interim
promotion or outcome-dependent extension. At each eligible EURUSD entry,
record side, UTC timestamp, cohort and trade ID, observation dates and vintage
pins, `S`, sigma, and `WITH`/`AGAINST`/`NEUTRAL`/`UNKNOWN`, using the frozen REV4
ex-EUR basket, prior-UTC-day rule and thresholds. Freeze the label before the
outcome; record missing inputs rather than backfilling. The label must not
feed the model, entry logic, routing, stake, or exits in either cohort.

At the pinned cutoff use only strict closed WIN/LOSS results in R. Report
cohorts separately, including matched-entry coverage where available, unknown
and unclosed counts, and the REV4 weekly clustered 95% intervals. Do not pool
cohorts or use differences between platforms as the estimated effect of a
gate. The primary decision uses V3 DEMO: fewer than 20 eligible trades in
either directional bucket is `INSUFFICIENT_SAMPLE`; otherwise require AGAINST
mean R below WITH mean R, AGAINST total R below zero, and the upper bound of
the AGAINST weekly 95% interval below zero before bringing a gate to the owner
for review. V2 DEMO is a separate comparison baseline; disclose disagreement.
Keep `COMPUTE_AND_LOG_ONLY` regardless of the result until the owner explicitly
selects a different policy. A historical or shadow removal estimate is not
realized gate performance.

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
