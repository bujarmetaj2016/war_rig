# Agent 1 — Core-5 macro research continuation (17 Nov 2026)

**Authority:** `OWNER_DIRECTED_RESEARCH / READ_ONLY_V2 / REV4`
**Branch:** `research/core5-macro`, starting from commit `105d9794a7e8ce2d15a4466277a32547908e26c5`.

Do not merge into Agent 2's branch, modify V2, access IG, activate any V3 trading policy, or change any fixed REV4 rule (definitions, signs, horizons, thresholds, sample minimums, bootstrap, `UNKNOWN` handling). The FRED/ALFRED downloader is done (section C1); do not redo it.

## A. Correct the source findings and the proposal

1. **V2 parity baseline.** Add a `V2_PARITY` column to `CORE5_V3_MACRO_PROFILE_PROPOSAL.md` and a matching section to `CORE5_MACRO_FINDINGS.md`, listing every existing V2 macro gate with its exact threshold and source citation:
   - EURUSD, GBPUSD: directional signal suppressed when climate < 40; `HALF` for 40 ≤ climate < 60; `FULL` at ≥ 60. `size_mult = 0.5` is telemetry only and does not scale the Governor's actual stake.
   - DAX, SP500: signal suppressed when climate < 40.
   - SP500: separate Governor VIX panic gate, `vix_zscore >= 2.0` by default; unavailable VIX denies entry.
   - GOLD: macro model features only; no climate-derived entry gate.

   `V2_PARITY` is the comparison baseline, not an instruction to enable these gates in V3. Any removal, correction or replacement is a separate, explicit candidate line with its evidence and the status `OWNER_SELECTION_REQUIRED`. Record as a defect that the FX climate is direction-agnostic: a strong USD lowers climate for EURUSD/GBPUSD SELLs as much as for BUYs.
2. **Calculation-lineage table.** Separate every calculation that shares a name, with file, lines and SHA-256:
   - feature-module `dxy_zscore` (5-day DXY return ÷ rolling std, not demeaned);
   - climate `dxy_zscore` (demeaned rolling 20-row z-score);
   - feature-module `vix_zscore` (per instrument) and climate `vix_zscore`, each with its exact window;
   - Governor `MarketSnapshot.vix_zscore` (up to 252 daily closes, may contract to 20).

   For each logged column (`ml_signal_predictions.dxy_zscore`, `ml_signal_predictions.vix_zscore`, `trade_decisions.vix_zscore`), trace the producer and state which definition it holds. If this cannot be established, mark it `UNCLEAR`; do not infer it.
3. **Theme/Sharpe cluster claim.** Cite the exact file:line for the suppression of EURUSD or GBPUSD by the theme/Sharpe cluster filter, or change the claim to `UNCLEAR`.
4. **Sample limits, stated up front** in `CORE5_MACRO_TRADE_TEST.md`: strict closed outcomes are EURUSD 101, DAX 44, GBPUSD 19, GOLD 18, SP500 17. Under REV4's minimum of 20 in **each** of WITH and AGAINST, GBPUSD, GOLD and SP500 cannot produce a gate recommendation; they still get descriptive results where data permit. EURUSD and DAX are not guaranteed sufficient buckets either.

## B. Implement the Part 4 test engine

Implement the classification and comparison engine for all 19 predefined instrument × macro tests, exactly as REV4 defines them: `S` and `σ`, ±0.5σ bands, risk-off rule, USD basket with quote inversions and the traded currency excluded, signs and headwinds, the n ≥ 20 per bucket rule, the weekly clustered bootstrap, the overlapping-driver family rule, the multiple-testing statement, and `UNKNOWN` / `NOT_TESTED` handling.

Availability rule (already used by the downloader): use the ALFRED vintage in force on the UTC day before entry. An observation first published on the entry date is `UNKNOWN`. A same-day revision does not disqualify an eligible earlier vintage.

Before running anything on real outcomes, add synthetic tests that must pass, covering:
- look-ahead (a value published after entry must never be used);
- revised observations (the earlier vintage must be used);
- observation date versus publication date;
- incomplete price bars;
- missing histories;
- fewer than 250 baseline observations → `UNKNOWN`;
- quote inversion in the USD basket;
- duplicate or missing observations;
- mismatched trading calendars;
- bucket-size rule;
- bootstrap determinism with a fixed seed.

Never use historical results to change a threshold or rule.

## C. Data acquisition

1. **FRED/ALFRED:** done (commit `105d979`). The owner runs it in the separate container.
2. **Release schedules:** write a standard-library downloader for the official historical schedules: Federal Reserve FOMC meetings, ECB monetary policy meetings, Bank of England MPC decisions, and BLS CPI and Employment Situation releases. It must cover the real-time range already recorded by the FRED downloader. For each event, record the scheduled date, time and time zone, the source URL, the page's publication or last-updated date where shown, and the download time. Write per-file SHA-256 values. Same isolated-job rules as the FRED downloader: run by the owner in a separate container; no credentials needed. Add offline parser tests using saved sample pages. Until schedules are downloaded and verified, the five event-proximity tests are `UNKNOWN`.

## D. Commit and report

Update every affected evidence file. Make sure rerunning the analysis script cannot overwrite the corrected findings or proposal with older text: either generate them from the script, or make the script leave them alone and fingerprint them. Regenerate `evidence/macro/MANIFEST.sha256`, verify it, and commit.

Report:
- the commit SHA and manifest SHA-256;
- the files changed;
- the status of A1–A4, B (synthetic tests run and passed) and C2;
- which of the 19 tests ran, with results;
- remaining blockers.

Until the owner confirms the downloads ran and you have verified them, report `TRADE_TEST_NOT_VERIFIED`, with zero gate recommendations.
