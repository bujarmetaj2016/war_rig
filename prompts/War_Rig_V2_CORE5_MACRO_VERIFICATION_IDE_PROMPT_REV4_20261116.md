# WAR RIG — CORE-5 MACRO VERIFICATION (V2 READ-ONLY RESEARCH)

**Status:** `OWNER_DIRECTED_RESEARCH / READ_ONLY_V2 / REV4 / RUNS_IN_PARALLEL_WITH_V3_STAGE_A`
**Purpose:** Establish, per Core-5 instrument, (1) exactly which macro inputs V2 uses and where each one actually acts, (2) which macro inputs each instrument should use, and (3) on V2's real trades, whether trades taken *against* the macro direction performed worse. The output decides V3's per-instrument macro profile.

## 0. Rules

- Read V2 source **only** from the owner-supplied, redacted, hash-pinned `war_rig/reference/v2_snapshot/`, as text. Do not open the active V2 repository, its `.env`, its database, the EC2 host or any cron job, and never import, execute or modify V2 code. Do not touch IG.
- V2 trade history and recorded signals come only from hash-verified exports in `war_rig/reference/v2_outcomes/` and `war_rig/reference/v2_predictions/`. Record each SHA-256. A missing input is recorded as `NOT_VERIFIED`; never reconstruct it.
- Internet access is allowed in this task **only** for downloading public macro and price history (FRED/ALFRED, Yahoo Finance) and the official historical release schedules of the Federal Reserve (federalreserve.gov), ECB (ecb.europa.eu), Bank of England (bankofengland.co.uk) and US BLS (bls.gov) in Part 4. For each schedule, record the scheduled release date and time with its time zone, and the page's own publication or last-updated date where shown. Save every downloaded series to `war_rig/reference/history/macro/` with its SHA-256, source URL/ticker and download time. No other network use. Downloads run in a separate research container or job, never in the V3 network-denied sandbox, with no V2 runtime, credentials or IG access.
- Work on a dedicated branch/worktree of the V3 repository (never a V2 worktree). Write all outputs to `war_rig/evidence/macro/`, plus `evidence/macro/MANIFEST.sha256` listing every output, the script commit and every input data hash. This is the single location the V3 build reads; do not copy outputs elsewhere. Commit the analysis script so every number can be reproduced.
- **Research hypotheses (not policy).** Read `war_rig/reference/hypotheses/Cross-Asset_Macro_Correlation_Dashboard_1.pdf` and `war_rig/reference/hypotheses/Core5_Macro_Driver_Table_20261116.md`, with their SHA-256 recorded. They are inputs to Parts 2 and 3 only. Nothing in them is an approved gate, sign or threshold beyond the rules this prompt fixes.
- Never infer what code does from names or comments. Trace each value from where it is computed to its **last consumer**.
- Label every finding `VERIFIED_FROM_V2_SOURCE` (with file, line range and file SHA-256), `NOT_FOUND`, or `UNCLEAR` (with the reason).

## Part 1 — Inventory of what V2 actually does

For each instrument (EURUSD, GBPUSD, GOLD/XAUUSD, SP500/US500, DAX/GER40), list **every** macro or cross-asset input in its feature module, climate logic, Governor and Manager. One row per input in `CORE5_MACRO_INVENTORY.csv`:

| Column | Content |
|---|---|
| `instrument` | |
| `input_name` | Exact name in code |
| `source` | Yahoo ticker, FRED series ID or other |
| `transform` | Formula and lookback, exactly as coded |
| `timing` | Which bar it is read from; whether it can read a forming (incomplete) bar; publication lag handling |
| `role` | One or more of: `MODEL_FEATURE`, `ENTRY_GATE` (can block an entry), `SIZE_MODIFIER` (changes stake actually sent), `CONFLICT_ARBITRATION`, `DISPLAY_ONLY`, `COMPUTED_UNUSED` |
| `reaches_entry_decision` | YES/NO — does this value change whether Governor enters? |
| `reaches_position_size` | YES/NO — does it change the stake actually sent? |
| `evidence` | file:line range + file SHA-256 |

Answer these explicitly in `CORE5_MACRO_FINDINGS.md`, each with the code path:

1. **EURUSD and GBPUSD:** can V2 open a BUY while USD is strengthening (or a SELL while USD is weakening) when the entry geometry is valid? Show every check between the signal and the order, and state whether any of them looks at USD direction. The owner reports this happens; confirm or refute it from code.
2. Does the climate `HALF`/`size_mult` signal reach Governor's actual position-size formula for EURUSD/GBPUSD, or is it display-only?
3. For each instrument: is any macro input used **only** as a model feature (so it can be outvoted by other features) rather than as a gate?
4. Does any macro series read a forming same-day row (`iloc[-1]` on incomplete data) or mix data dates across instruments?

## Part 2 — Candidate macro profile per instrument (hypotheses to test, not facts)

| Instrument | Candidate macro inputs | Why |
|---|---|---|
| EURUSD | **USD strength excluding EUR** (see Part 4), US–German 2-year yield spread, VIX | DXY is about 58% EUR, so "DXY rising" largely *is* EURUSD falling and is nearly circular. A USD basket without EUR measures USD strength independently. |
| GBPUSD | **USD strength excluding GBP**, US–UK 2-year yield spread, VIX | Same logic; GBP is about 12% of DXY. |
| GOLD | US 10-year real yield (FRED `DFII10`), USD broad strength, VIX | Classic drivers. The real-yield link weakened from 2022 with central-bank buying, so test it on recent data and do not assume it. |
| US500 | VIX level and VIX/VIX3M term structure, US 10-year yield change, high-yield credit spread (FRED `BAMLH0A0HYM2`) | Risk regime and financing conditions. |
| GER40 | VIX (or VSTOXX), EURUSD, Bund 10-year yield, prior US500 session | Global risk, currency translation, rates, US lead. V2 DAX already has 27 point-in-time features including VIX, DXY and FRED yields; reconcile against those. |

### Part 2b — Additional drivers from the owner's driver research

| Driver | Applies to | Treatment in this task |
|---|---|---|
| Oil price (Brent) | GER40, EURUSD, GBPUSD | **Tested** (rule in Part 4). Eurozone and UK are net energy importers; higher energy costs weigh on German industry. |
| US 2-year yield (Fed path proxy) | EURUSD, GBPUSD, GOLD | **Tested** (rule in Part 4). Rising US short rates favour USD and raise gold's opportunity cost. |
| Fed–ECB and Fed–BoE 2-year rate differential | EURUSD, GBPUSD | `NOT_TESTED_DATA_UNAVAILABLE` unless the owner supplies a daily, point-in-time German and UK 2-year yield source. FRED has no daily Bund or gilt 2-year series. |
| High-impact scheduled releases: FOMC, ECB and BoE decisions, US CPI, US NFP | All five | **Tested** as an event-proximity flag (rule in Part 4). This informs V3 calendar exclusions, not a directional gate. Historical dates come only from the official Fed, ECB, BoE and BLS schedules, hash-pinned. |
| 10-year inflation breakeven (FRED `T10YIE`) | GOLD | `NOT_TESTED`. It overlaps the real-yield test already in Part 4. |
| Index heavyweight earnings, fiscal events, budgets, geopolitics, central-bank gold buying, ETF flows | Various | `OUT_OF_SCOPE_NOT_SYSTEMATIC`. No point-in-time daily rule is defined, so it can only be logged, not gated. |

**Overlapping drivers.** The USD basket, US 2-year yield, US real yield and DXY are largely stages of the same Fed repricing, not independent signals. For each instrument, report how often their classifications agree on the same trades. Treat them as **one family**: a recommendation needs the family's strongest member to pass the decision rule; several members agreeing is not extra evidence.

**Drivers that need surprise data.** The driver dashboard's central-bank surprise and inflation-surprise rows (Fed, ECB and BoE hawkish/dovish surprises; hot US CPI, euro-area HICP and UK CPI) are measured against market expectations. Point-in-time consensus or market-implied expectations are not available in this task, so these rows are `NOT_TESTED_DATA_UNAVAILABLE`. The event-proximity test covers their timing risk, not their direction. The US–German and US–UK real-yield and 2-year spreads are also `NOT_TESTED_DATA_UNAVAILABLE`, for the same reason as the rate differentials. US500 versus DXY is `NOT_TESTED` (regime-dependent, no stable sign).

**Horizon.** The driver dashboard describes medium-term responses over weeks to quarters, while V2 trades last hours to days. The 10-day window is a compromise. A driver that holds over quarters may not hold over a trade's life, which is exactly what this test checks.

**Primary versus exploratory.** The owner's pre-stated hypothesis, the USD-strength basket for EURUSD and GBPUSD, is the **primary** test. Every other instrument × macro test is **exploratory**: report it and apply the same decision rule, but label any recommendation from it `EXPLORATORY` in the proposal.

## Part 3 — Gap table

`CORE5_MACRO_GAP.md`: per instrument, three columns side by side — **in V2 (from Part 1, with role)**, **candidate (Part 2)**, **in V3 design** (from the V5 package's EXT-G0R-14 instrument profiles). Mark each input `PRESENT_AND_ACTING`, `PRESENT_BUT_NOT_ACTING` (e.g. feature only, display only), `MISSING`, or `V3_ONLY`.

## Part 4 — Test on V2's real trades (rules fixed before looking at results)

**Data.** Every closed V2 trade with instrument, direction, entry time (UTC), and outcome in R (strict WIN/LOSS from Transactions, as already established). Market-price series (FX, VIX, VIX3M, indices) use the last daily bar whose close time (UTC, stated per source) is before entry; record each source's daily close convention. Economic and rate series from FRED use the ALFRED vintage published before entry. If there is no evidence that a value was available at entry, that trade–macro pair is `UNKNOWN` and is excluded from every claim.

**Fixed regime rules** (do not change after seeing results):

- **Definitions used by every rule below.** `S` is the 10-day change of a series at the last completed bar before entry:
  - for prices, FX rates, the USD basket and oil: the **sum of the 10 daily log returns** ending at that bar;
  - for yields and spreads (`DGS2`, `DFII10`, HY spread): the **latest value minus the value 10 observations earlier**, in percentage points (never a sum of levels).
  `σ` is the standard deviation of that same `S` series over the **250 observations** ending at that same bar (no later observations). Fewer than 250 valid observations → `UNKNOWN`.
- **USD strength basket:** for each currency in {JPY, GBP, CAD, CHF, AUD, EUR}, **excluding the trade's own counter-currency** (no EUR for EURUSD, no GBP for GBPUSD), take the daily log return of USD priced in that currency: USDJPY, USDCAD and USDCHF as quoted; EURUSD, GBPUSD and AUDUSD inverted. The basket daily return is their equal-weighted mean. `USD_UP` if `S` > +0.5σ; `USD_DOWN` if `S` < −0.5σ; otherwise `NEUTRAL`.
- **Gold:** real yield 10-day change > +0.5 × rolling std = headwind for BUY; < −0.5 × = headwind for SELL; plus the USD rule above (USD up = headwind for gold BUY).
- **US500:** `RISK_OFF` if VIX/VIX3M > 1.0, or VIX > 1.25 × its 20-day median; `RISK_OFF` is a headwind for US500 BUY and a tailwind for SELL. Separately, HY spread `S` > +0.5σ is a headwind for BUY; < −0.5σ is the reverse.
- **GER40:** the same `RISK_OFF` rule, with the same signs as US500. Separately, EURUSD `S` > +0.5σ (stronger euro) is a headwind for GER40 BUY through the exporter channel; < −0.5σ is the reverse. This sign is regime-dependent: in a sharp risk-off move the DAX can fall *with* the euro. Report this test split by `RISK_OFF` versus not; the split is descriptive only and does not create extra decision tests.
- **VIX for FX and Gold:** the same `RISK_OFF` rule is a headwind for EURUSD BUY and GBPUSD BUY (dollar safe-haven demand) and a tailwind for GOLD BUY (gold safe-haven demand), with the reverse for SELLs. All three are exploratory and regime-dependent.
- **Oil (GER40, EURUSD, GBPUSD):** Brent **spot** price, FRED `DCOILBRENTEU` (ALFRED vintage rule applies), so futures contract rolls cannot create false returns. If that series is unavailable for a date, use a front-month futures series only after removing the return on each contract-roll date (roll dates documented); if roll dates cannot be identified, the value is `UNKNOWN`. `S` and `σ` as defined above. Oil `S` > +0.5σ is a headwind for GER40 BUY, EURUSD BUY and GBPUSD BUY, and a tailwind for the matching SELLs; < −0.5σ is the reverse.
- **US 2-year yield (EURUSD, GBPUSD, GOLD):** FRED `DGS2` daily change (ALFRED vintage rule applies). `S` > +0.5σ is a headwind for EURUSD BUY, GBPUSD BUY and GOLD BUY; < −0.5σ is the reverse.
- **Event proximity (all five):** a trade is `EVENT_WINDOW` if its entry is within the 24 hours **before** a scheduled FOMC, ECB or BoE decision, US CPI or US NFP release; otherwise `NO_EVENT`. Use the scheduled release time from the official schedule as it stood before entry. Compare `EVENT_WINDOW` with `NO_EVENT` using the same statistics and decision rule as WITH versus AGAINST, where `EVENT_WINDOW` takes the place of AGAINST.
- Candidate inputs without a rule here (rate differentials, Bund yield, GER40's prior US500 session, breakevens) are `NOT_TESTED`. They are neither accepted nor rejected.

**Classification.** Each trade is `WITH`, `AGAINST` or `NEUTRAL` relative to each macro. Example: an EURUSD BUY while `USD_UP` is `AGAINST`.

**Report** per instrument and per macro: n, win rate, mean R, total R, and a 95% confidence interval of mean R for WITH, AGAINST and NEUTRAL, bootstrapped by calendar week (resampling whole weeks, so trades clustered in time are not treated as independent); plus the fraction of trades and of total R that a gate blocking `AGAINST` trades would have removed.

**Fixed decision rule:**
- If either the WITH or the AGAINST bucket has n < 20, the comparison is `INSUFFICIENT_SAMPLE`. Report it anyway, but make no claim from it.
- Report the total number of instrument × macro tests run, and state that with this many tests some differences will appear by chance.
- A macro is a **recommended V3 entry gate** for that instrument if AGAINST mean R < WITH mean R **and** blocking AGAINST would have raised total R.
- It is **confirmed** only if, in addition, the AGAINST group's 95% CI upper bound is below zero.
- Anything else stays a model feature or a logged observation, not a gate.

State plainly that V2's closed-trade history is small, so these results show direction of evidence, not proof. Removing historically losing trades is a partial counterfactual, not a measured future gain: a gate also changes capital use and which later signals are taken. No macro gate becomes executable in V3 without explicit owner adoption and later forward (DEMO) validation. The V2-versus-V3 demo period remains the decisive test.

## Output

1. `CORE5_MACRO_INVENTORY.csv`
2. `CORE5_MACRO_FINDINGS.md`, answering the four questions in Part 1
3. `CORE5_MACRO_GAP.md`
4. `CORE5_MACRO_TRADE_TEST.md`, with the tables, the regime rules as run, data hashes and the script commit
5. `CORE5_V3_MACRO_PROFILE_PROPOSAL.md`: per instrument, the recommended inputs and the role of each (`ENTRY_GATE`, `SIZE_MODIFIER`, `MODEL_FEATURE`, `LOG_ONLY`), each justified by Parts 1–4. This is a proposal for the owner, not an adopted policy.
