# WAR RIG V3 — ONE COMPLETE OFFLINE DESIGN
## Unified owner review copy | 13 November 2026

**Purpose:** one readable presentation of the complete broker-independent offline V3 technical design, including the approved-for-discussion MS-B dual-source proposal, adaptive trailing, confidence scoring, guardrails, audit, watchdog and deterministic simulator. This review copy reproduces **all 26 numbered design-package members (00–25) verbatim in Part II**; their immutable primary source pins and reference evidence remain in the companion ZIP.

**Status:** `DESIGN_ONLY / CONSOLIDATED_CANDIDATE / NOT_OWNER_ACCEPTED / NOT_FROZEN / NOT_IMPLEMENTATION_AUTHORISED / 48H_NOT_STARTED`.

**Controlling candidate:** `V3-ONE-STAGE-OFFLINE-CORE-CANDIDATE-20261113-V5` (mechanical application of 24 MS-B package edits and AM-10..AM-14 to the V3 package, without modifying any of its 25 pinned source files). The companion ZIP is the byte-carrying candidate; this assembled reading copy is *not* a substitute for its structured CSVs, JSONs, signatures, or independently controlled source contracts.

**Read order:** Part I (scope, architecture, decisions, remaining proof), then Part II (the complete numbered members). Signatures and final evidence fingerprints should refer to the actual frozen package, not to this prose summary.

---

# PART I — Unified technical design and review decision

## A. Intended product, scope and sequence

The proposed master route is **Option R (restricted offline, credential-free) + EXT Option C (full expanded offline functionality with controlled internal implementation slices under one eventual exact-scope G1-R grant)**. This is still a proposed owner selection, not a completed signed choice. The purpose is to implement a complete **broker-neutral simulated trading core**, not merely a test harness with placeholder order states. Initial offline capability covers the entire trade lifecycle: signed data snapshots, instrument definitions, prediction, evidence and confidence classification, eligibility, risk and sizing, simulator execution, partial fills and applied stop proof, adaptive trailing, reconciliation, watchdog evaluation, audit and reporting.

**Strict exclusion boundary:** no IG credentials, SDK, quote feed, real observation, broker order mutation, network egress, operational alert-provider calls, V2 live-code/database reads, live or DEMO trading, model retraining or automatic model promotion. No fixture value or feature flag can create any of those capabilities. Signed fictional risk parameters may support *simulated* trades only. G2 (read-only real broker), G3 (DEMO mutation) and G4 (LIVE) are later separately authorised scopes. V2 continues independently and is not retired by this package.

The baseline covers Gold, GER40, US500, EURUSD and GBPUSD, and includes a configurable instrument-family definition system capable of adding a second synthetic instrument without code changes. An EXT six-instrument paper walkthrough including Brent is **not** broker certification.

## B. Logical processing flow

`Signed snapshots + instrument definition + fixture policy` → `data completeness / calendar / regime validation` → (`SIGNED_TEST_SCORE` **or** `TRAINED_MODEL`) → `SignalScore with source + fingerprint` → `calibrated probability / quality / climate / confidence band` → `strategy eligibility and executable-side geometry` → `portfolio/exposure guardrails` → `one fenced simulated order intent` → `local simulator (market order + partial/full fills)` → `applied initial-stop and protected-quantity read-back` → `safe adaptive trailing` → `reconciliation + realised outcome` → `audit / independent watchdog evaluation / read-only dashboard / comparison`.

Every transition carries stable intent/prediction identities, input/policy fingerprints, UTC evidence and explicit `UNKNOWN` states. **No score implies permission**: a signal must separately pass side-specific model evidence, data quality, cost-adjusted edge, instrument, sizing, portfolio, risk, audit, stop-protection and lifecycle gates.

## C. Thirteen complete functional components (design scope)

1. **Market data and calendars (`SourceSnapshotLoader`)** — signed immutable rows, completed bars, publication timing, no forming-bar or stale-data reuse.
2. **Prediction registry and inference (`ModelArtifactRegistry`, `model_intake.py`)** — signed fixed test scores and controlled trained-model reading under one `SignalScore`; no refit, no executable model deserialisation.
3. **Confidence, climate and selection (`EffectivePolicyResolver`, pure strategy evaluator)** — raw score, calibrated side/regime probability, evidence flags, context and a decision band; explicit no-entry outcomes.
4. **Strategy and TP/SL geometry (`AnchorQuoteValidator`, `EntryEligibilityEngine`)** — instrument role/direction, executable bid/ask versus model reference, horizon, grid and protective side validity.
5. **Sizing and portfolio risk (`ExposureRiskLedger`)** — synthetic account economics, conservative pending/UNKNOWN exposure, portfolio theme conflicts, breakers, cap before minimum stake.
6. **Broker-neutral execution (`CoreOfflineExecutionEngine`)** — one logged attempt per intent, simulated MARKET entry, atomic multi-axis lifecycle and no implicit retries.
7. **Deterministic broker simulator (`OfflineBrokerSimulator`)** — delayed ACK, rejection, UNKNOWN, partial fill/close, applied-stop proof, wrong account, stale or conflicting snapshots.
8. **Adaptive position manager (`PositionProtectionMonitor`, ATC-01)** — V2 parity reference, mandatory safety divergences, grade BE/ATR trail, single pure evaluator, tighten-only simulator modifications.
9. **Confirmation and reconciliation (`ConfirmationReconciler`)** — authoritative evidence per claim, preserve ambiguity, no timeout→REJECTED or missing-row→CLOSED, transaction wallet with proven outcomes.
10. **Ledger, controls and watchdog (`IntentLedger`, `StopBreakerControls`, `IndependentWatchdog & AlertProof`)** — single writer, seven typed axes, persistent entry-only local Stop, separate circuit breakers, missed-cycle and audit-chain detection.
11. **Audit and dashboard (`AuditCustody & Dashboard`)** — tamper-evident event journals, source/stop/attempt proof, typed alerts, read-only health and financial projections with verified provenance.
12. **Offline comparison (`ComparisonEvaluator`)** — pre-registered V2-versus-V3 cohorts from one immutable quarantined pinned V2 snapshot only; no online V2 production query, no unsupported performance inference.
13. **Isolation and build policy** — deny-all outbound controls, reproducible lockfiles and mirrors, secret/quarantine tests, static import denials and future common adapter conformance.

The exact 18-module scope mapping and the traceability of original eight units, EXT units and named additions appear in numbered members 02 and 17. The original eight-unit G1-R scope is insufficient for this functional design; members 04 and 23 propose the required exact source amendments. **Do not assume those amendments are already adopted.**

## D. Predictions — controlled dual-source MS-B (`NO_REFIT`)

**Source A, `SIGNED_TEST_SCORE`** is deterministic, fingerprinted fixture scoring used to validate the pipeline, execution geometry, risk accounting, trailing and audits. Its outputs are always `PIPELINE_VALIDATION_ONLY` and visibly stamped `NOT_PERFORMANCE_EVIDENCE` and `NOT_A_MODEL_PREDICTION`.

**Source B, `TRAINED_MODEL`** takes an owner-registered artifact through a single narrowly allowed read/evaluate module, `v3/offline/model_intake.py`. Allowed data-only formats: XGBoost native JSON with restricted tree/objective support, JSON scaler, JSON calibration, JSON ordered feature schema and signed manifest. Unsafe deserialisation formats (pickle/joblib/etc.) and fit/train imports are prohibited inside the offline artifact. Existing eligible owner-produced pickle/joblib candidates would need separately authorised conversion in an isolated environment, end-to-end parity evidence (raw row through feature order, missing values, scaling, trees, calibration, final probability), a justified registered tolerance, signed registration and all 11 G-1..G-11 serving gates. A missing or invalid model yields `NO_AUTHORITATIVE_PREDICTION`, **not** a fallback to test scores, older models or just-in-time refit.

Each `SignalScore` records `source_kind`, registered source manifest hash, feature row and snapshot lineage, evidence class, direction, raw score, calibrated probability, policy/run hashes and stable `prediction_id`; all simulated orders/positions/outcomes/audit events retain the link. Each run declares the source for each instrument and cannot switch it mid-run. Trained-model reports carry `OFFLINE_SIMULATED_MODEL_BEHAVIOUR` and the explicit caveat `not verified forward or live trading performance`. Source A and B figures are **never pooled**.

**Core-5 model status:** no registered frozen Core-5 artifact was identified on the one inspected EC2 host in the specified locations; S3 and other hosts were not verified. All five remain `UNAVAILABLE` **for authorised trained-model serving**. This is not proof that no model exists globally. A new fit-and-freeze is a separate proposed authorisation, MS-F; model cadence remains `OC-D04-04 = DEFER`. No fitting, calibration fitting, model promotion or LIVE activation is authorised here. Open inventory and manifest checks do not create authority.

## E. Trading confidence, climate and strategy eligibility

The ATC-01/D04 confidence design separates **L1** raw score, **L2** calibrated instrument/side/regime probability (with lower bound and sample count), **L3** completeness/freshness/drift evidence, **L4** separately labelled macro climate, and **L5** decision band/grade. Only L2 may be called a probability. The continuation score used by adaptive management is **not** entry confidence. Climate is not silently multiplied into calibrated probability; a retained contextual effect requires evidence. V2 reference grades and baseline parameters are documented for comparison, not assumed to be statistically calibrated.

The proposed eligibility test requires the calibrated probability **lower bound** above the traded, cost-adjusted break-even plus owner-specified margin; complete features, valid calibration, no disqualifying drift and independently valid risk/strategy permits. For common units: `break_even = (SL + round_trip_cost)/(TP + SL)` if the same round-trip cost is charged in both outcomes. That probability gates the *barrier label*, not proven realised profit under trailing; realised net-R-by-band under the actual policy must be evaluated separately. Missing short-side labels/calibration make shorts ineligible. Confidence can select only a base stake tier; final stake is lowered or denied by money, exposure, theme, climate, margin and broker-minimum constraints. Confidence never widens TP or SL, loosens a stop, bypasses risk or increases stake on missing evidence.

Core roles: **Gold** trend + pullback, **GER40** trend plus open/session filters, **US500** trend with separately evidenced direction policy, **EURUSD** mean reversion with occasional trend, **GBPUSD** rejection-style mean reversion. Market-only initial simulated entries do **not** silently convert a GBPUSD limit-entry requirement; use explicit rejection/fixture incompatibility tests. Default without a valid signed fixture is `NO_NEW_ENTRY` for every market.

## F. Entry protection, risk guardrails and trade lifecycle

Entry requires signed valid data, policy, permitted instrument/side, fixture market quote and sound protective geometry and capability. `ACCEPTED` is only an acknowledgement, not a fill. After each partial/full fill, reserve **gross worst-case exposure** and set the position `OPEN_CONFIRMED` only on fill proof, while protection remains `PROTECTION_UNVERIFIED` until independent simulator read-back verifies account, position, filled quantity, applied stop, grid, correct side, min distance, and policy/version. No trailing before this proof.

A missing, rejected, widened or unverifiable stop freezes routine trailing, retains reservations, opens an incident and triggers a watchdog-alert simulation. UNKNOWN send/ACK/close remains UNKNOWN until specific authoritative evidence. Do not blindly retry the same intent, release reserves because a row is absent, pretend a close was successful, or use unapproved automatic IG rescue. A local authenticated and audited **Stop** persists across restart and blocks only new entries; it never controls IG and cannot defeat automatic safety gates. Breakers remain distinct and require separate controlled reset evidence.

The broker-neutral simulator supplies a market-entry interface, account-scoped read-back and stop modification interface, deterministic event ordering and injected failures. Offline scope has **zero IG transport**. A later IG adapter must pass the shared contract plus additional platform-specific certification, but is outside this authority.

State lineage uses seven typed axes: `broker_operation`, `working_order`, `position`, `protection`, `realised_result`, `intent_lifecycle`, `attempt_send_eligibility`. Stage D03's 42-edge candidate model, 38 guarded edges and 84 denied state-pairs remain source-pinned design proposals. Cross-axis updates require one atomic fenced transaction; partial commit is forbidden.

## G. Adaptive trailing and break-even

The mandatory **V2_PARITY_V1 reference** is computed on fixed V2 inputs; its executable offline result includes four named safety divergences (actual-fill + verified initial-stop R; reject stale/unknown data; verified stop read-back authority; at most one send per intent), not silent V2 behaviour cloning. V2's observed reference behaviour includes initial HOLD when unrealised R ≤0.5, confidence/continuation-score tier fractions at R ≥1, grade-dependent break-even and ATR parameters (FX override), and a max of two times spread versus broker minimum distance. Values in the V2 source are parity references, **not new owner-selected adaptation parameters**.

Every tick uses one pure function of the immutable position, last verified applied stop, fresh market data and bound policy version, producing `HOLD(reason)` or `PROPOSE(tighter_stop, reason, digest)`. Simulation-only authority checks audit persistence, fence, modified quantity, market crossing and distance limits, stop grid, minimum interval/move, latest position version and no breaker/mutation latch. A modification gets a new stable intent, is attempted once, then requires independent applied-stop read-back before being called `VERIFIED`. Ambiguous, stale, mismatched or failed proof leaves last VERIFIED state intact and freezes trailing with an incident. The policy bound at entry cannot silently rewrite a running position.

The four ATC improvement candidates C1–C4 remain **compute-only comparisons** until individually preregistered, tested and chosen. The ATC owner directions J1–J4 are not automatically selected by inclusion. **Offline permission is `SIMULATOR_ONLY_TIGHTEN`;** `LIVE_TIGHTEN_ONLY` is excluded.

## H. Independent watchdog, audit and alert proof

The offline core includes pure watchdog evaluation on **signed synthetic event traces**: an expected-cycle roster, completed-cycle witness, audit-chain/checkpoint gap verifier, clock and stale-input checks, incident classification and synthetic alert proof states. The watchdog must not self-attest its own failure; the real separated watchdog runtime, independent outside witness, genuine delivery channels and canaries remain later G3 work. Architectural *separation* is specified; operational independence is not claimed as already demonstrated.

Audit/event records have typed envelope, source/evidence pointers, actor/position/account scope, event sequence, hashes and per-stream append-only writers. Candidate families cover decision, eligibility, intent/ledger, broker evidence, protection, reconciliation, registry, health, control, alert, clock, incident and integrity. `ALERT_PROVIDER_ACCEPTED` is **not** delivery, and delivery is not human acknowledgement or incident resolution. Alerts track generated → send attempted → provider accepted/failed → independently evidenced delivered → authenticated acknowledged; backup escalation has its own proof. The watchdog's six D1–D3/E1–E3 clocks use specific source events and keep unknown/unstated deadlines explicit; **operational numeric intervals and several endpoint alternatives remain owner-UNSET**.

An audit pre-commit failure denies an automatic simulated mutation, but cannot reverse an actual already-observed fill. A compromised single hash chain is not proof of external custody; external witnessed/custody copies and independent reviewer signatures are governance/evidence obligations, not automatic capabilities. Dashboard output is **read-only**, with manager/watchdog health, candidate and event lineage, data freshness, simulated position/protection states and transaction wallet/reconciled outcomes, visibly separated by evidence class.

## I. Test and evidence requirements

**Design tests are not execution results.** The package carries Stage D03's 187 specified synthetic cases, 42-edge/84-denial design material, the core `TC-*` family matrix, ten `TC-INIT-01..10` initial-protection oracles and `MSB-01..19` model/dual-source cases. The MS-B edit checker has been independently re-run locally on this candidate: **71 structural/replay checks PASS**. This does not prove software execution, model conversion parity, robustness, broker compatibility, watchdog failure-domain independence or human acceptance.

Before an exact G1-R grant is eligible, the source package requires real signed deny-egress controls, hostile isolation tests, source/model provenance, quarantine and secret scan, build graph, dependency pinning, mirror/lockfile hashes, review independence evidence and custody; each proof must bind the exact candidate bytes. No test failure concerning protective stop truth, UNKNOWN exposure, duplicate send, atomic ledger, stale policy, secret/IG ingress, audit integrity or source provenance can be waived by fixture confidence.

## J. Decision ledger and documented residuals

The source package explicitly carries **61 unresolved owner decision rows** (43 original master, 14 Stage D and 4 ATC), as well as **13 source freeze findings** and **21 repairs**, each requiring explicit controlled disposition; their files 05, 06, 07 and 18 are reproduced below. `DEFAULT_DISABLED`, `OPEN` or `DEFER` is not a hidden owner YES. Real money values, real IG contracts, actual model artifacts and calibration tolerances, watchdog fail-domain and alert channels, numeric safety deadlines, protective-response policy, approved model cadence and permissions remain unresolved or later-gated as described in member 15.

**Four evidence-precision wording corrections applied in the V5 package:**

1. Member 24, section 13: Signal ML V2 model sets are `CREATED_UNREGISTERED`; their `promoted_for_live` status is `NOT_VERIFIED_BY_R2` pending manifest inspection. No model becomes serving-eligible.
2. Member 15: No registered or eligible Core-5 frozen artifact was identified in the inspected locations; other hosts and S3 were not checked. Absence is not claimed universally.
3. Member 00: The copies of the V2 inference code reviewed by R2 fit a transient model on each run. The actual EC2 live-folder code hash is still `PENDING_OWNER_CHECK`.
4. Member 21: The Core-5 absence statement is limited to the single inspected host; the V2 inference behaviour statement is limited to the reviewed copies, with the six other files recorded separately.

These are bounded factual corrections, not a redesign or permission to fit, serve or promote models. R2's revised checker records 114/114 design-package review checks and 71/71 V5 replay checks; the V5 package has separately been replayed locally with 71/71 PASS. Neither constitutes executed V3 unit/integration tests. All 25 pinned primary sources remain unchanged.

## K. Controlled presentation, 48-hour interval and grant

**Path 1** is the current working route, preserving the pinned 27 October 2026 rules (a) and (b): group all final proposal members, independent review/approval evidence, exact scope and environment, controlled amendments, disposition registers, custody evidence and the two **unsigned** owner forms into **one indivisible final presentation group**. Compute/check the SHA-256 of every member and the group root. Record the **last actual** trusted presentation timestamp in UTC. Only that final, complete, immutable, owner-presented group may begin **one continuous 48-elapsed-hour interval**. Any member text/scope/hash change resets the entire group's interval; no partial time credit.

**After** 48 hours and verified human/quorum/K1/H13/witness/custody compliance, hold one owner sitting with **two separate exact-fingerprint signatures**: G0-R design acceptance followed by G1-R scoped offline implementation authority. A single sitting does not combine the grants. The clock itself grants nothing. External IG, DEMO, LIVE and V2 retirement remain separately controlled later.

**Present status:** candidate assembled and checked, but the 61-row dispositions, independent-review route (`19`), evidence packet (`09`), controlled exact-source amendments (`23`) and relevant owner choices are not signed. Accordingly **THIS IS NOT THE FINAL EVIDENCE-BOUND PRESENTATION; NOT AN ACCEPTED DESIGN FREEZE; NO `WAIT_START`; NO G1-R GRANT.** The owner may review this fingerprinted candidate and decide whether any corrections are necessary. A fully finalised version is then sealed once and presented under Path 1.

---

# PART II — Verbatim numbered package members

The following 26 numbered source-package files are reproduced with their original content. CSV and JSON sections are fenced for unambiguous source reproduction. The package ZIP retains each in its native filename and includes the 25 unchanged pinned sources, the evidence/checker tools, and `MANIFEST_SHA256.json`. The text below is a *reading copy*; source bytes live in the ZIP.


---

## PACKAGE MEMBER 00_READ_ME_FIRST.md

# War Rig V3 — one consolidated offline-core design acceptance / G1-R grant candidate

**Artifact ID:** `V3-ONE-STAGE-OFFLINE-CORE-CANDIDATE-20261113-V5`  
**Status:** `DESIGN_ONLY / PROPOSAL_FOR_SINGLE_OWNER_SITTING / NO_OWNER_SELECTION / NOT_INDEPENDENTLY_VERIFIED / NOT_FROZEN / NO_48H_CLOCK / NO_G1_AUTHORITY`.

## Meaning

One **consolidated owner stage** contains (a) independently verified final offline trading design, (b) one 48-hour evidence-bound group interval, (c) **two separate, exact-hash records signed in the same owner sitting**—G0-R design acceptance and G1-R implementation grant—and (d) implementation **only after** the G1-R record is actually signed. Do not treat the stage as an automatic grant. No IG integration, credentials, login, deals or V2 runtime modification is in scope.

**Scope selection candidate:** Master Option R + EXT-G0R-14 §1.1 Option C—**complete broker-neutral offline trading**, implemented in controlled slices under one final authority, with fixture-policy simulated dealing. This is a *candidate*; a proposal cannot sign itself. The original master §3.1A eight-unit G1R slice is expressly insufficient for full offline trading and requires controlled scope amendment. All 16 original design modules are mapped in `02_...csv`, with two named additional offline modules. The IG-facing mutation gateway stays excluded.

**ATC-01:** Confidence-grade/trade sizing/breakeven/adaptive trailing are core requirements, not deferred out of the offline simulator. ATC-01 revision 2 provides four candidate improvements and four owner decisions J1–J4, none selected. The offline manager can simulate stop modifications in a *simulation-only* mode. No real broker writes.

## Contents and sequence

- `01_...md` — full 13-component core baseline; `02_...csv` — 18-module mapping.
- `03_...md` — broker-neutral simulator/interface contract; `04_...md` — controlled source reconciliation schedule.
- `05_...csv` — all 61 owner rows: 14 Stage D + 4 ATC + 43 master; every row OPEN/NOT_SELECTED.
- `06_...csv`, `07_...csv` — 13 freeze findings and 21 repairs, preserved OPEN for controlled disposition.
- `08_...md` — test contract and offline failure injection; `09_...csv` — G1-R evidence inventory (actual results not claimed).
- `10_...md` — governance table/group timing; `11_...md` — independent review record, **unsigned**.
- `12_...md` — G0-R acceptance form, **unsigned**; `13_...md` — G1-R grant form, **unsigned**.
- `14_...json` — grouped cooling-off status: **NOT_STARTED**.
- `15_...md` — blockers/remaining work; `16_...json` — source-chain/provenance.
- `17_...csv` — crosswalk of the eight original units and `EXT-01` to `EXT-13` to the 18 modules and 13 components; `18_...csv` — disposition class of each of the 43 master rows, the 13 findings and the 21 repairs.
- `19_...md` — Group 1 independence applicability and the owner's three routes (none selected); `20_...md` — explanatory table of the source-amendment proposals (not adopted); `21_...md` — merged review finding disposition; `22_...md` — primary-evidence hashes; `23_...csv` — the **exact old and new text of the fourteen controlled source amendments (AM-01..AM-14), the controlling form** (not adopted until the owner signs G0-R); `24_...md` — MS-B dual-source prediction contract with 19 tests (proposed, not selected); `25_...csv` — evidence on the model files that exist today.
- `SOURCE_PINS_UNMODIFIED/` — fingerprinted copies of source proposals/reviews, never amended in place.
- `MANIFEST_SHA256.json` — SHA256 for every member other than the manifest; the containing ZIP hash is reported separately.

## Readiness is not permission

This is a **substantive consolidated candidate**, not a claim that all safety, reviewer, custody or G1-R environmental evidence is complete. Do **not** present it as the *last/final evidence-bound group* or start the 48-hour interval until all items in `15_READINESS_BLOCKERS_AND_UNSET_VALUES.md` are satisfied, all decisions explicitly disposed, all final proposal bytes and evidence locked, independently checked, and the final-group hashes presented together. A revision changes the group's fingerprint and, if a group clock has started, restarts the entire indivisible group under the reported 27-Oct rule.

**Historical evidence caution:** The local historical cooling-off `PENDING_V1` file is *not* the subsequently approved 48-hour decision; it is not included as a controlling source. The approved decision is attached byte for byte as `SOURCE_PINS_UNMODIFIED/A39_GROUP1_COOLING_OFF_OWNER_DECISION_V2.json` (SHA-256 `d3f39baa27d8a8c91050d19dea32d83883b73eb1ddb80cf4d89dcfbee534143b`, re-computed from its bytes by R2 on 13 Nov 2026). Owner reply, verbatim: "Cooling-off duration: 48 hours. I accept rules (a) and (b) as written." Rule (a): one interval covers proposals presented together once the full group, every final proposal, its evidence and each SHA-256 are fixed, and it starts after the last final evidence-bound presentation. Rule (b): a change to proposal text, evidence-bound scope or SHA-256 restarts the clock, and for an indivisible group it restarts the whole group clock.

**Precedence over the pinned Group 1 addendum:** `SOURCE_PINS_UNMODIFIED/GROUP1_V2_ADDENDUM_UNCHANGED.json` was written before the owner's decision and still records `cooling_off_duration: UNSET`. The owner's 27 Oct decision (`d3f39baa…`, 48 hours) supersedes that statement for duration only; no other statement in the addendum changes.

**V3-GOV-48-01:** retained as an unadopted alternative; not incorporated or treated as an effective replacement. No other stage is invented by this candidate. G2/G3/G4 external broker/use gates stay separately controlled in future when needed; they are outside this one offline implementation grant.

## Consolidated review correction round (13 Nov 2026)

R2 B1–B7/C1 edits, source pins and 27 October decision are incorporated. A second documentary review identified F01–F07; this revision adds explicit initial-stop protection contract and test oracles, fixes inconsistent offline modules, supplies the Stage D03 primary spec and 187 detailed unexecuted cases, and corrects clock metadata. See `21_MERGED_REVIEW_FINDING_DISPOSITION.md`. All such corrections are **design-only and nonbinding**; no human independent review, build, test execution, cooling-off or owner signature is claimed.

**Important boundary:** the model *interface, confidence pipeline and simulated signals* are in offline G1 candidate scope, while prediction sources are governed by the proposed MS-B dual-source contract (`24_...md`, `25_...csv`): signed test scores validate the pipeline, owner-registered non-executable trained models may be read once registered, no model is fitted or promoted, and at presentation all five Core-5 trained models are recorded UNAVAILABLE for offline serving, because no registered frozen Core-5 artifact was identified in the inspected locations and the V2 inference code that R2 holds trains afresh on each run (this is not proof that no model exists elsewhere). This is not a claim of a fully integrated trained-model trading runtime.

New review files: `17_EXT_AND_ORIGINAL_UNIT_CROSSWALK.csv`, `18_REGISTER_DISPOSITION_CLASSES.csv`, `19_GROUP1_INDEPENDENCE_APPLICABILITY_OWNER_ROUTE_NOT_SELECTED.md`, `20_CONTROLLED_SOURCE_SUPERSESSION_PROPOSAL_NOT_ADOPTED.md`, `21_MERGED_REVIEW_FINDING_DISPOSITION.md`, `22_PRIMARY_EVIDENCE_MOUNT_AND_CONTENT_SHA256.md`, `23_CONTROLLED_AMENDMENT_EXACT_TEXT.csv`, `24_MSB_CONTROLLED_DUAL_SOURCE_PREDICTIONS_CONTRACT.md`, `25_MODEL_ARTIFACT_EVIDENCE_EC2_20261113.csv`; primary bytes under `SOURCE_PINS_UNMODIFIED/STAGE_D03_REVIEW_BYTES/`.


---

## PACKAGE MEMBER 01_COMPLETE_OFFLINE_CORE_DESIGN_13_COMPONENTS.md

# Complete V3 broker-independent offline trading core — acceptance candidate

**Proposed route:** Master §0 Option R + EXT §1.1 Option C. **Implementation:** full offline capability, staged internally but under one exact G1-R grant after one group 48h interval. This does *not* accept or amend the source contracts by itself.

## Scope invariant

The system accepts a signed, explicitly **SIMULATED/FIXTURE** money-and-strategy policy and can create, fill, monitor, trail, reconcile, close and audit synthetic positions for all five market families (Gold, GER40, US500, EURUSD, GBPUSD). It can replay immutable historical events and run deterministic simulated sessions. **All money, stops, clock values and confidence limits used for simulation are test fixtures, not a trading-account policy.** Real IG account/market certification, credentials, external trading, and V2 production access are absent. Genuine broker-facing capability is never unlocked by a fixture config flag.

## Thirteen integrated components

| # | Component | Existing or new module owner | What it does | Input → output contract | Fail-closed/default invariant | UNSET and later gate | Test family |
|---|---|---|---|---|---|---|---|
| 01 | Market data and calendars | SourceSnapshotLoader | Immutable historical/synthetic source manifests; completed bars; timezone/calendar and macro publication checks | snapshot_digest, feed_id, bars, publication_time -> FreshSnapshot/REJECT | No stale/forming-bar reuse; no zero imputation; unknown session blocks new signal | Fixture freshness thresholds signed for offline use; actual live feeds at later gate | TC-DATA-* |
| 02 | Model registry and inference | ModelArtifactRegistry (two sources behind one `SignalScore` contract, MS-B: signed test scores and, through `v3/offline/model_intake.py`, owner-registered non-executable trained models) | Pin model/data/feature and calibration hashes; return a `SignalScore` either from a signed, hash-registered test-score set (`SIGNED_TEST_SCORE`, pipeline validation only) or from an owner-registered trained model that passes the MS-B gates (`TRAINED_MODEL`); every score carries its source and fingerprint; no pickle or joblib, no fitting, no promotion, no fallback from one source to the other | model_manifest + input_snapshot -> SignalScore/NOT_PROVEN | Model missing/stale/unhashed -> no eligible entry; no fitting or promotion | Real artifact registration is separate and later; all five Core-5 trained models are UNAVAILABLE at presentation; fit-and-freeze (MS-F), training cadence and promotion are separately authorised later gates (OC-D04-04) | TC-MODEL-*, MSB-01..MSB-19 |
| 03 | Confidence, climate and selection | EffectivePolicyResolver + EXT-04 strategy_evaluator (CandidatePublisher stays excluded) | Separate raw model score, calibrated side-specific probability, quality, climate and band; theme resolution | score + calibration + context + signed_fixture_policy -> Candidate/NO_NEW_ENTRY | No mislabeled probability; lower-bound edge gate candidate; uncertain shorts ineligible; monetary caps never overridden | ATC J1/J3/J4 decisions OPEN; calibration sample thresholds fixture; later G3 proof | TC-CONF-* |
| 04 | Strategy and TP/SL geometry | AnchorQuoteValidator + EntryEligibilityEngine | Core 5 per-instrument role and direction; V2 reference trace; simulated executable bid/ask anchor; horizon/TP/SL | candidate + side quote + certified_sim_caps -> ProposedGeometry/DENY | No price substitution from daily close; side/stop/grid check, same model label geometry until validated change | GBPUSD limit strategy not silently market-converted; US500 direction unresolved for IG; offline fixture scenarios explicit | TC-STRAT-* |
| 05 | Sizing and portfolio risk | ExposureRiskLedger | Fixture money-per-point, equity, margin, gross reservations, risk tier, theme conflicts, circuit breakers | geometry + cap/equity snapshot + pending exposure -> StakePermit/DENY | No minimum-stake round-up; no unknown-netting release; breaker latches independent; no unproven monetary assumptions | Real financial limits OD-05 UNSET; signed fixture money values allowed for simulated trades | TC-RISK-* |
| 06 | Broker-neutral order/position engine | CoreOfflineExecutionEngine | Simulated MARKET entry, one-attempt journal, partial fill/close, state-machine rules, cancellation and outcome typing | intent + permit + adapter -> ATTEMPTED/ACCEPTED/REJECTED/UNKNOWN | Never double-send; wire attempt <=1 per intent; UNKNOWN reserves gross exposure; cross-axis commit atomic | Live IG working entry and mutation gateway excluded; offline adapter permitted | TC-ENGINE-* |
| 07 | Deterministic broker simulator | OfflineBrokerSimulator | Virtual quote/account/position capability record; delayed/failed ACK, rejects, partial fills, incomplete snapshot and read-back | submit/modify/cancel/read + fault_fixture -> broker_response/evidence | Simulator side effects only; deterministic injection; failure replay trace and no network transport | Fixture spreads/min stops/stakes must be signed and labeled non-IG | TC-SIM-* |
| 08 | Adaptive protection and position manager | PositionProtectionMonitor + ATC-01 evaluator | V2_PARITY reference and V3 safety divergences; grade-based BE and ATR trail; C1–C4 shadow comparisons; simulated stop writes | verified_sim_stop + market + policy_version -> HOLD/PROPOSE -> SIMULATOR_ONLY_MODIFY -> verify | Tighten-only; failed read, missing R, ambiguous send or audit-failure => freeze/alert; never treat requested stop as applied | ATC J1/J2 and exact policy parameters owner OPEN; fixture values simulate every path | TC-ATC-* |
| 09 | Confirmation and reconciliation | ConfirmationReconciler | Broker-neutral correlation, account/position binding, UNKNOWN-to-proof transitions, late fills, partial close and transaction wallet | sim position/event/snapshot -> verified applied state + provenance | No timeout->REJECTED; no unproved closed/absent position; no silently dropped P&L | Real IG read-back semantics at G2/G3 only | TC-RECON-* |
| 10 | Ledger, controls and watchdog | IntentLedger & SingleWriter + StopBreakerControls + IndependentWatchdog & AlertProof | Seven typed axes, CAS fence, local entry-only Stop, separate breakers, completed-cycle witness, typed alert receipt | typed events + observer cycles -> ledger commits + incidents | Atomic group journal, no unaudited mutation; stop persists; no false alert delivered/ack; no automatic breaker reset | Six operational D/E clock numbers UNSET; fixture times for test only | TC-STATE-* |
| 11 | Audit, custody and dashboard | AuditCustody & Dashboard | Append-only decision/attempt/applied stop history; signed fixture provenance; read-only health and P&L projection | journal + verified state -> audit trail/dashboard | Disk failure blocks automated simulation mutation as test oracle; dashboard cannot become a mutation endpoint | Actual custody and human signers before owner sitting; operational alert routes later | TC-AUDIT-* |
| 12 | Comparison and offline backtesting | ComparisonEvaluator | Preregistered V2 replay controls, fixed cohorts/cost normalization, simulated trade outcomes, confidence band economics | immutable V2 snapshot + simulated V3 outputs -> read-only evaluation | Missing/unknown outcomes retained; no lookahead, no use of V2 runtime database, no performance claim without executed evidence | V2 log/data intake requires quarantined scanned, independently pinned source | TC-COMP-* |
| 13 | Isolation, build governance and cross-adapter conformance | EffectivePolicyResolver + OfflineBrokerSimulator + audit | Deny-all outbound environment, immutable config, fixture-policy signature, one conformance suite for simulator and future IG adapter | build/environment signature + test manifests -> build permit/deny | No IG SDK/keys/routes/real transport; no V2 code/import; network isolation independent of scanner; no host writes | Signed deny-egress, lockfile, mirror and hostile proof required before actual G1 authorization | TC-ISOLATION-* |

## Explicit initial-protection lifecycle (broker-neutral)

The `CoreOfflineExecutionEngine`, `OfflineBrokerSimulator`, `PositionProtectionMonitor`, `ConfirmationReconciler` and `ExposureRiskLedger` implement the *same* protected-fill contract in `03_BROKER_NEUTRAL_EXECUTION_AND_SIMULATOR_CONTRACT.md`: deny an unprotectable entry; reserve gross potential exposure on every partial or full fill; remain position `OPEN_CONFIRMED` with protection `PROTECTION_UNVERIFIED` until independent simulator read-back confirms account, position, applied stop and protected quantity; only then permit routine adaptive trailing. Missing, rejected, ambiguous or stale protection remains `PROTECTION_UNVERIFIED` (or `PROTECTION_DRIFT` when a defect is proven) with frozen trailing, preserved reservations and an alert. No IG auto-repair or hidden rescue authority. Exercise TC-INIT-01..10 on both eventual adapter implementations before claiming parity. All cases are NOT_RUN.

## V2 functionality parity and approved divergence model

`V2_PARITY_V1` produces a **reference** answer from pinned V2 inputs; the offline **executable** answer is that algorithm subject to ATC-01 rev2's DV-1 through DV-4: broker-confirmed initial stop for R; no trading when required data stale/missing; read-back is authoritative and freezes unverified protection; one wire attempt per intent. This is a planned design comparison, **not a demonstrated V2 parity result**. For synthetic sessions, a simulated actual fill and initial applied stop are authoritative; for later IG sessions the certified IG read-back is authoritative. Higher V2 grades affect stake and, outside FX, baseline BE/trail parameters; retain that mapping in parity, rather than rewriting history. Four C1–C4 improvement candidates are compute-only until individually tested and selected.

**Do not silently enable:** shorts without short labels/calibration; limit-working GBPUSD entries in MARKET-only entry policy; US500 direction without explicit policy; automatic emergency repair/flatten; a G2/G3 broker adapter; model refit/promotions; real monetary risk values. They remain available for offline failure simulations as deliberately isolated fixture cases, not production permissions.

## State contracts

Maintain Stage D03's proposed 42-edge candidate graph, 38 guarded edges, 84 denied pairs, three ledger event families and the seven ledger axes exactly as the pinned Stage D integrated specification section 3 defines them: `broker_operation`, `working_order`, `position`, `protection`, `realised_result` (the five Annex G axes) plus `intent_lifecycle` and `attempt_send_eligibility` (the two axes master V1.8 section 3.3 proposes). Alert, clock, manual-Stop, automatic-breaker and reset-authorisation records are control and watchdog records (master section 3.3, WDA-08); they are not among these seven ledger axes. Exact edge IDs remain governed by the pinned Stage D03 members `01_EDGE_CONTRACTS_35_DRAFT.json` and `02_NEGATIVE_GRAPH_COMPLEMENT_59_SOURCE_PRESERVED.json`; this memo does not activate them. D03 N12 remains: cross-axis operation groups must commit atomically or be denied, with explicit correlation and half-commit negative tests. No event type is approved merely because it appears here.

## Instrument definition layer (EXT-G0R-14 section 3; part of this baseline)

War Rig V3 is configurable by instrument, not hard-wired to five markets. This baseline includes the pinned EXT-G0R-14 section 3 model unchanged: a stable **instrument-family definition** whose typed fields each sit in tier T1, T2 or T3; separate **dated listings** with per-field evidence; an acyclic **input-evidence index**; and a **registration manifest** under which every plug-in is declared by signed hash. A new instrument is added by a new definition plus fixture data only, with zero source changes and zero plug-in-manifest changes (`V3EXT-006`, the first build milestone). Modules: `EXT-01 instrument_definition.py`, `EXT-02 plugin_manifest.py`, `EXT-13 contract_listing_registry.py`, mapped in `17_EXT_AND_ORIGINAL_UNIT_CROSSWALK.csv`; the layer sits under components 01, 03, 04 and 13 and is not a fourteenth component. Fail-closed: a missing or wrongly typed field, a T3 value that tries to override a T2 or T1 check, an uncertified or stale listing, or a missing mandatory check denies new entry (`V3EXT-002`, `-007`, `-010`). A second synthetic instrument is the `V3EXT-006` proof; the EXT Annex A six-instrument walkthrough (core five plus Brent) remains paper evidence and certifies no IG economics.

## All five instruments, offline only

| Instrument | Strategy continuity requirement | Default without signed fixture |
|---|---|---|
| Gold | V2 trend + pullback, confidence grade, adaptive protection parity, volatility variants C1–C4 | NO_NEW_ENTRY |
| GER40 | Trend, market-open filters and grade-derived BE/trailing baseline | NO_NEW_ENTRY |
| US500 | Trend, model direction label proof and grade-derived management | NO_NEW_ENTRY |
| EURUSD | Mean reversion with occasional trend; FX BE/ATR baseline; USD theme | NO_NEW_ENTRY |
| GBPUSD | Rejection mean reversion; limit-entry mismatch must be explicitly simulated but not converted into MARKET automatically | NO_NEW_ENTRY |

## Scope closure criterion

A final owner acceptance must approve this complete **functional architecture** and its explicit simulator boundary, not merely the historical eight-unit scaffold. Parameter tuning can remain fixture-only, but a missing fail-safe behaviour, unbounded broker uncertainty or an unjustified hidden module exclusion cannot. This complete baseline is a candidate awaiting independent verification and recorded owner decision.


---

## PACKAGE MEMBER 02_SCOPE_C_COMPLETE_18_MODULE_SCHEDULE.csv

```csv

module,previous_g1r_disposition,proposed_scope_C_disposition,implementation_gate,simulation_boundary,source_test_anchor,remaining_broker_dependency,owner_selection
SourceSnapshotLoader,`SCHEMA-ONLY` via `v3/offline/calendar_completion.py`,FULL_OFFLINE_IMPLEMENTATION_CANDIDATE,G1R_OFFLINE_FIXTURE,Complete offline implementation using signed synthetic/historical snapshots; no IG dependency,`G1R-06-A` forming bar rejected; `G1R-06-B` DST/late-calendar invalidation,Actual feed loader EXCLUDED,NOT_SELECTED
ModelArtifactRegistry,"`EXCLUDED`; effective-policy **manifest/hash field only**, not a model loader, registry/mock or runtime",OFFLINE_DUAL_SOURCE_PREDICTIONS_NO_REFIT,G1R_OFFLINE_FIXTURE,"Two sources behind one SignalScore contract: signed test scores (SIGNED_TEST_SCORE) and owner-registered non-executable trained models through `v3/offline/model_intake.py` (TRAINED_MODEL); no fitting, no promotion, no pickle or joblib; no IG dependency","`G1R-08-M` narrowed to one module (AM-10, AM-11); MSB-01..MSB-19; manifest-field validation belongs to `G1R-01-A`","Real model registration, any fit-and-freeze (MS-F) and promotion are separate later gates; all five Core-5 trained models UNAVAILABLE at presentation; OC-D04-04 stays DEFER",NOT_SELECTED
EffectivePolicyResolver,`IN` via `v3/offline/effective_policy.py`,FULL_OFFLINE_IMPLEMENTATION_CANDIDATE,G1R_OFFLINE_FIXTURE,Complete offline implementation using signed synthetic/historical snapshots; no IG dependency,`G1R-01-A` duplicate/unknown config DENY; `G1R-01-B` disabled monetary policy cannot enable dealing,Final risk and model policies OFF,NOT_SELECTED
CandidatePublisher,`EXCLUDED`,EXCLUDED_RESERVED_EXT07_NO_PUBLISHER_OR_STORE,G1R_OFFLINE_FIXTURE,Not built: candidate records are carried by intent identity plus ledger plus audit events and emitted by the pure strategy evaluator EXT-04; no IG dependency,`G1R-08-C` reject candidate publication service import,NONE_IN_OFFLINE_MODE; EXT-07 stays excluded and reserved,NOT_SELECTED
AnchorQuoteValidator,`EXCLUDED`,OFFLINE_PURE_VALIDATOR_OVER_FIXTURE_QUOTES,G1R_OFFLINE_FIXTURE,Pure bid/ask validator over signed fixture quotes only; no feed or broker-quote or anchor-module import; no IG dependency,`G1R-08-Q` reject broker quote/anchor module import,Optional anchor decision OPEN,NOT_SELECTED
AccountBoundBrokerObserver,`SCHEMA-ONLY` via `v3/offline/synthetic_observer.py`,OFFLINE_SIMULATED_OBSERVER_ONLY,G2_FOR_IG,Account-identity and evidence contracts exercised against simulated account; no live IG read proxy,`G1R-07-A` mock identity mismatch; `G1R-07-B` no credential/network capability,Actual G2 observer not included,NOT_SELECTED
EntryEligibilityEngine,`EXCLUDED` (deny outcome type only in `effective_policy.py`),FULL_OFFLINE_IMPLEMENTATION_CANDIDATE,G1R_OFFLINE_FIXTURE,"FULL offline rule evaluation and eligibility under signed fixture confidence, data and risk; not merely a mocked deny type","`G1R-01-C` missing policy data remains deny; no send permit; TC-STRAT, TC-CONF and TC-INIT-01 negative cases",FULL fixture-driven offline entry decision engine within G1-R scope; actual IG quote/policy proof remains at G2/G3,NOT_SELECTED
IntentLedger & SingleWriter,"`IN` via `v3/offline/intent_identity.py` + `v3/offline/state_ledger.py` (**mock journal**, no broker writer)",FULL_OFFLINE_IMPLEMENTATION_CANDIDATE,G1R_OFFLINE_FIXTURE,Complete offline implementation using signed synthetic/historical snapshots; no IG dependency,`G1R-02-A` duplicate key; `G1R-03-A` CAS/race; `G1R-03-B` UNKNOWN replay,Broker single-writer/send excluded,NOT_SELECTED
BrokerMutationGateway,`EXCLUDED` from **G1-R and G2 artifacts**,NOT_IN_OFFLINE_BUILD,G3,IG-only live broker mutation gateway excluded; simulation uses independent offline adapter with no imported real transport,`G1R-08-W` static/import/raw-network deny test,First eligible only for separately granted G3,NOT_SELECTED
ConfirmationReconciler,`EXCLUDED` (synthetic result states in `state_ledger.py`),FULL_OFFLINE_IMPLEMENTATION_CANDIDATE,G1R_OFFLINE_FIXTURE,"FULL offline event/position reconciliation including UNKNOWN, delayed read-back, partial fills/closes; no real broker API",`G1R-03-C` duplicate/conflict code stays UNKNOWN; `G1R-07-C` mock conflicting confirmations; TC-RECON/TC-INIT-04..09,REAL IG reconciliation later only; simulator implementation part of this one G1-R grant,NOT_SELECTED
PositionProtectionMonitor,`EXCLUDED` (protection states mocked in `state_ledger.py`),FULL_OFFLINE_IMPLEMENTATION_CANDIDATE,G1R_OFFLINE_FIXTURE,"FULL simulated initial protection validation, grade-based BE and adaptive trailing, applied stop read-back and loss-of-stop incidents",`G1R-03-D` degraded evidence never VERIFIED; ATC-X01..23 and TC-INIT-03..10,Real IG A/B/C and broker-specific protective action at G3 only; offline TC-ATC and TC-INIT included now,NOT_SELECTED
ExposureRiskLedger,`EXCLUDED` (unknown reservation fields only),FULL_OFFLINE_IMPLEMENTATION_CANDIDATE,G1R_OFFLINE_FIXTURE,FULL deterministic fixture-risk accounting and simulated portfolio exposure; never actual broker account value,`G1R-01-D` no R/capital => denied capability; `G1R-03-E` UNKNOWN reservation retained; TC-RISK and TC-INIT-03/04,"FULL simulated exposure, capital, stake, margins, gross UNKNOWN reservations and breaker ledger in G1-R; real-account monetary certification later only",NOT_SELECTED
StopBreakerControls,`IN` via `v3/offline/control_latches.py`,FULL_OFFLINE_IMPLEMENTATION_CANDIDATE,G1R_OFFLINE_FIXTURE,Complete offline implementation using signed synthetic/historical snapshots; no IG dependency,`G1R-05-A` restart Stop latched; `G1R-05-B` Resume cannot reset breaker,Breaker limits and local Resume OPEN,NOT_SELECTED
IndependentWatchdog & AlertProof,`SCHEMA-ONLY` alert events in `v3/offline/audit_events.py`; watchdog runtime `EXCLUDED`,FULL_OFFLINE_IMPLEMENTATION_CANDIDATE,G1R_OFFLINE_FIXTURE,Complete offline implementation using signed synthetic/historical snapshots; no IG dependency,`G1R-04-B` ack chronology/evidence; no provider calls,Independent watchdog and real canary G3,NOT_SELECTED
AuditCustody & Dashboard,`SCHEMA-ONLY` audit ledger via `v3/offline/audit_events.py`; dashboard and external custody `EXCLUDED`,FULL_OFFLINE_IMPLEMENTATION_CANDIDATE,G1R_OFFLINE_FIXTURE,Complete offline implementation using signed synthetic/historical snapshots; no IG dependency,`G1R-04-A` actor/account correlation; `G1R-04-C` tamper/outage,External custody/audit restore G3,NOT_SELECTED
ComparisonEvaluator,`EXCLUDED`,FULL_OFFLINE_IMPLEMENTATION_CANDIDATE,G1R_OFFLINE_FIXTURE,Complete offline implementation using signed synthetic/historical snapshots; no IG dependency,`G1R-08-X` no V2 DB/live cohort access,FULL synthetic comparison and pinned historical fixture evaluation at G1; production V2 results and actual cross-broker trial require separate authorisation,NOT_SELECTED
CoreOfflineExecutionEngine,NOT_PRESENT_IN_16_MODULE_TABLE,NEW_BROKER_INDEPENDENT_OFFLINE_MODULE,G1R_OFFLINE_FIXTURE,Single fenced market-entry and position-management coordinator,NEW_CONTRACT_TEST_REQUIRED,NONE_IN_OFFLINE_MODE; IG conformance later,NOT_SELECTED
OfflineBrokerSimulator,NOT_PRESENT_IN_16_MODULE_TABLE,NEW_BROKER_INDEPENDENT_OFFLINE_MODULE,G1R_OFFLINE_FIXTURE,Deterministic broker simulator with delayed/ambiguous/partial/adverse outcomes and read-back,NEW_CONTRACT_TEST_REQUIRED,NONE_IN_OFFLINE_MODE; IG conformance later,NOT_SELECTED

```


---

## PACKAGE MEMBER 03_BROKER_NEUTRAL_EXECUTION_AND_SIMULATOR_CONTRACT.md

# Broker-neutral execution and simulator contract (proposed core normative interface)

## No-IG offline boundary

The offline simulator implements a broker-neutral protocol that **does not link, import, load, call, authenticate or route to IG**. There are two distinct runtime implementations in the overall product roadmap: `OfflineBrokerSimulator` at G1-R; any actual `IGAdapter` only after separate future G2/G3 authorisation. Exactly one conformance suite is defined against the shared protocol; the simulator runs it during offline implementation, the later adapter is required to run the applicable same cases plus independently approved IG probes.

### Typed interface sketch (shape only, NOT deployed code)

```
capabilities(account_scope, instrument) -> CapabilityRecord | NOT_PROVEN
quote(account_scope, instrument, as_of) -> QuoteSnapshot | UNKNOWN
submit_market(intent_id, attempt_id, policy_hash, side, stake, initial_protection_spec, guard_hash) -> ACCEPTED(ref) | REJECTED(reason) | UNKNOWN(transport_or_broker_evidence)
read_order(account_scope, source_intent_id, broker_ref?) -> snapshot | UNKNOWN
read_position(account_scope, position_id) -> filled_quantity, avg_fill, applied_stop, applied_target, verified_timestamp | UNKNOWN
modify_stop(modify_intent_id, attempt_id, position_id, new_stop, policy_hash, fence) -> ACCEPTED(ref) | REJECTED(reason) | UNKNOWN
cancel_or_close(intent_id, position_id, qty, fence) -> ACCEPTED | REJECTED | UNKNOWN
read_events(correlation_scope) -> immutable broker events + provenance | UNKNOWN
```

- `CapabilityRecord` must declare tick/price grid, money-per-point, currency conversion, minimum size, stop distance, supported order types, modification feasibility, protection semantics, and reliability/evidence status. **Fixture values are explicitly synthetic and signed**; unverified IG values must never be represented as certified.
- Direction-sensitive quote price and spread are explicit. Model/reference price and executable-side price remain separate; no stale-close fallback.
- `ACCEPTED` means the adapter accepted/recorded a request, **not** proof of fill, applied stop, realised P&L or closed position. `UNKNOWN` is a first-class nonterminal result. Read-back has a separate independent failure path.
- All requests bind to explicit account and product scope, position identity, a durable pre-commit intent, immutable policy version and writer fence; an operation has **at most one wire attempt per intent**. Idempotency keys identify a local intent; they do not imply a broker duplicate-suppression guarantee. No retries of the same intent.
- Reconciliation is authoritative only on evidence sufficient for that specific claim, not on a timeout, an error code or a missing item in a partial snapshot. UNKNOWN reserves gross potential exposure. Distinguish PARTIALLY_FILLED, PARTIALLY_CLOSED, COMPLETE, CANCELLED_PRE_FILL, UNKNOWN and explicit NOT_SENT proof.
- A stop modification checks the **latest verified applied** stop and its instrument grid. Only tighter stops allowed. The simulator can perform modifications under `SIMULATOR_ONLY_TIGHTEN`, and must permit fault injection returning `UNKNOWN`, `REJECTED`, stale, external widening and broker-applied mismatches. The real IG `LIVE_TIGHTEN_ONLY` mode is not part of G1-R.
- Each broker-neutral result creates typed requested/committed/denied ledger events with **atomic transaction group** correlation spanning intent, attempt, position, protection, capital reservation and audit. If audit cannot be written, no automated simulated mutation proceeds; the failure must be observable.

## Initial fill-to-protection transaction and risk reservation (normative offline test contract; PROPOSED)

**Pre-entry admission.** A signed fixture policy supplies a protective stop/target specification and the capability record declares whether the simulated broker can attach protection to each fill. `initial_protection_spec` carries stop type, stop/target prices, direction, version, and synthetic price-grid/size constraints. If protection cannot be attached or positively verified by the allowed simulator policy, **deny new entry**. Any two-step attachment alternative remains `UNSELECTED` and is not implicitly authorised. A returned `ACCEPTED` is not a fill and not verified protection.

**Full or partial fill.** On every authoritative fill event (including a partial fill), record actual filled quantity, price, synthetic account/product identity, position version and **gross worst-case exposure reserved** in a single fenced ledger transaction. Set the position axis to `OPEN_CONFIRMED` (`D03-SRC-015`, fill proven) and the protection axis to `PROTECTION_UNVERIFIED` (`D03-SRC-020`); do not set `PROTECTION_VERIFIED` merely because the order was accepted, protection was requested, or a fill was seen. Any remaining unfilled quantity stays independently reserved according to the maximum possible pending exposure. The simulator must bind each new partial quantity to effective protection; after every quantity change, re-verify the entire filled size and applied protective stop. No trailing evaluates until verified.

**Stop read-back.** An independent, account-bound `read_position` must confirm `filled_quantity`, `applied_stop`, price-grid correctness, protective side and min stop distance, policy/version compatibility, and correct ownership. A verified match moves protection from `PROTECTION_UNVERIFIED` to `PROTECTION_VERIFIED` (`D03-SRC-028`) and releases only the justified protection uncertainty, **not** the position's capital/risk reservation. An applied stop different from requested outside an *approved* tolerance (UNSET means exact match only), missing stop, failed read or stale/partial evidence remains `PROTECTION_UNVERIFIED` (or becomes `PROTECTION_DRIFT` when a defect is proven, `D03-SRC-023`), freezes trailing for the position, blocks additional simulated entry under its fail-closed fixture policy, preserves gross risk reservations, writes an incident and requests an independently evidenced watchdog alert. An applied stop worse than the last verified stop is never silently promoted.

**Rejected, ambiguous, missing initial protection.** If the entry is rejected with authoritative proof of no fill, leave `NOT_FILLED` and release a reservation only after that proof. If an entry result is `UNKNOWN`, retain maximum pending exposure; a timeout or partial snapshot does not prove absence. If protection is rejected, missing, or its modification outcome is ambiguous, **no blind retry, no automatic IG/real close or repair**. Offline simulator may exercise a separately labelled *fixture-only protective-response test*, but that is a negative scenario, not a default remediation permission. A real broker account's protective-response A/B/C remains owner-open at G3.

**Crash, concurrent close, and audit failure.** A crash between fill and first verified stop must recover with position `BROKER_OUTCOME_UNKNOWN` (if the fill itself is not proven) or position `OPEN_CONFIRMED` with protection `PROTECTION_UNVERIFIED`, full reservations and no trailing until authoritative read-back. A close/fill/partial-fill race uses the one-writer, atomic cross-axis commit and a fresh account/position read; conflicting evidence freezes mutation. If audit pre-commit fails, deny the mutation; if the fill has already occurred externally, preserve exposure, mark protection unverified and alert—**never invent an order rollback**.

**Invariant:** the simulator never presents an active position as safely protected without independent applied-stop and quantity evidence, and never treats a requested protective change as applied. These are contract *specifications* and fixture tests; no implementation or broker capability is claimed.

## Modes that cannot be confused

| Mode | What it does | Broker write import permitted |
|---|---|---|
| `OFF` | Records no trading proposals | None |
| `COMPUTE_AND_LOG_ONLY` | Calculates stop or simulated trade decisions and logs only | None |
| `SIMULATOR_ONLY_TIGHTEN` | Sends one broker-neutral modification to a strictly local offline simulator and verifies its applied stop | Offline simulator only, no networking |
| `LIVE_TIGHTEN_ONLY` | **Future G3 candidate**, separately verified IG mutation authority and stop read-back | **DENIED/ABSENT in offline artifacts** |

## Safety vs routine management

An authorised **offline simulated** tighten is part of normal position management, not emergency repair. An unprotected or unknown simulated position triggers an incident/alert, preserves exposure and follows an explicit fixture-controlled protective-response scenario; this does not grant a real-IG emergency-close capability. Local Stop blocks new simulated entries but does not stop observing/managing established simulated positions; the separate mutation-safety latch can freeze automated trailing. An external manual real IG close remains outside offline scope.

## Required simulator fault schedule (minimal contract)

- Reject order without filling; reject stop update after the request is recorded; return UNKNOWN despite applying a stop; drop acknowledgment after partial fill; duplicate and reorder confirmation events.
- Simulate a bad position snapshot, delayed read-back, stale quote, wrong account, invalid instrument grid, too-tight/wide stop, widened external stop and absent stop.
- Simulate partial fills/partial closes; close/fill races; manager crash between intent commit and send; journal disk-full; duplicate tick; stale model artifact; daylight-saving/market closed window.
- Simulate direct-IP/DNS/outbound transport attempts and require zero external network egress. No fixture may be allowed to carry an actual IG secret.

**Contract-change rule:** the future IG adapter must satisfy these exact shared behaviour classes and any additional separately approved IG constraints. Any necessary strategy-domain rewrite is a design regression that requires disclosure and controlled review; do not promise perfect platform interchangeability before G2/G3 proof.


---

## PACKAGE MEMBER 04_CONTROLLED_SCOPE_SOURCE_AMENDMENT_SCHEDULE.md

# One controlled source-reconciliation schedule — PROPOSED, NOT APPLIED

**Source precedence:** the pinned Master V1.8, EXT-G0R-14, WDA-08, D03 and OD14-03 are retained byte-identically under `SOURCE_PINS_UNMODIFIED`. The clauses below are **amendment proposals**; signing this schedule alone does not mutate their source files. The exact old and new text of each amendment is in `23_CONTROLLED_AMENDMENT_EXACT_TEXT.csv` (AM-01..AM-14; each old text is quoted verbatim from the pinned file, where it occurs exactly once). That file is the controlling form of each amendment; this schedule and `20_...` explain what each one is for, and where they differ from file 23, file 23 controls. Every actual adopted controlled document must be separately fingerprinted and included in the final group.

| Controlled location | Current restricted wording / issue | Required full-offline-scope C alignment | Negative assertion | Disposition |
|---|---|---|---|---|
| EXT-G0R-14 §1.1 | Option C not yet owner selected; credential-free scope partly schema-only | Owner chooses R+C for complete broker-neutral offline trading baseline, built in stages under one G1-R authority; actual external broker gated | No real adapter in offline build | PROPOSED/OPEN |
| EXT section 1.2 invariant 1 | Bans real market-data network acquisition and order/stop/close operations in G1-R, which read literally also bans simulated ones | Ban only real-broker order/stop/close operations; simulated order, stop and close operations inside the OfflineBrokerSimulator are test-only with no real transport, credential or network path (AM-01) | No real transport, credential or socket in any build; V3EXT-024, V3EXT-025, TC-ISOLATION | PROPOSED/OPEN |
| Master V1.8 §0 | Scope R/F/DEFER unresolved | Record exact R+C scope and fixture-policy trading allowance without granting real dealing | Signed synthetic fixture cannot enable IG | PROPOSED/OPEN |
| Master V1.8 §3.1A | 16 modules; 9 EXCLUDED and several schema-only, plus absent offline engine/simulator | Replace previous G1-R module schedule with 18-row mapping: 16 original, new CoreOfflineExecutionEngine + OfflineBrokerSimulator, all broker-neutral behaviours included; IG gateway excluded; original units 01-08 and `EXT-01` to `EXT-13` are mapped one by one in `17_EXT_AND_ORIGINAL_UNIT_CROSSWALK.csv` | No hidden disabled core execution module | PROPOSED/OPEN |
| Stage D OD-01 / OD14-03 E1 | States TP/SL confidence trailing are not part of offline freeze | Core includes **functional offline simulator trading**, confidence/TP/SL/breakeven/adaptive trailing; only external IG writes excluded | Simulated modification accepted under fixture-only permit | PROPOSED/OPEN |
| Stage D OD-06 / OD14-03 E3–E6 | Disables all protective broker actions | Explicitly distinguish simulated protective stop tightening from prohibited IG repair/close/cancel. A/B/C real broker response remains OPEN | No unapproved real broker write | PROPOSED/OPEN |
| EXT V3EXT-070 | Prohibits any stop-modification import when adaptive field unselected | Prohibit IG/real transport imports; allow local simulated modify under signed fixture/mode with deterministic negative tests | `LIVE_TIGHTEN_ONLY` denied, simulator path exercised | PROPOSED/OPEN |
| EXT section 5.3 `G1R-08-M` | Rejects model/runtime registry import | Keep rejection of any fit, training, promotion, live activation and executable deserialisation, and of any registry or loader import outside `v3/offline/model_intake.py`. That module may read only the allow-listed non-executable formats of file 24, only for owner-registered artifacts that pass the MS-B gates; the pure strategy (the signed test-score source) keeps no loader (AM-10, AM-11) | MSB-04, MSB-05, MSB-09, MSB-15; `V3EXT-021` unchanged | PROPOSED/OPEN |
| EXT `V3EXT-025` | No V2 bytes in G1-R | One exception: an owner-registered converted model artifact, which is data admitted only through the model-intake route, never an archive member, V2 code or a V2 DB read (AM-12); `V3EXT-027` and `G1R-08-X` unchanged | MSB-05; V3EXT-025, V3EXT-027 | PROPOSED/OPEN |
| Master V1.8 section 3.1 ModelArtifactRegistry row | Says EXCLUDED from G1-R runtime and mocks and anticipates a later scope grant | Replace with controlled dual-source predictions under MS-B (AM-13); the module schedule row is in file 02 | MSB-01, MSB-12 | PROPOSED/OPEN |
| EXT section 1.2 invariant 1 (tail) | Bans model fitting or model activation in G1-R | Keep the ban on fitting and on promotion or activation for live use; state that offline serving of an owner-registered artifact under MS-B is neither (AM-14) | MSB-09; `V3EXT-015` | PROPOSED/OPEN |
| EXT section 5.3 `G1R-08-C` | Rejects candidate publication service import | No change. `EXT-07` and `CandidatePublisher` stay excluded; candidate records are carried by intent identity, ledger and audit events and emitted by the pure strategy evaluator `EXT-04` | Existing negative oracle stays; `V3EXT-022` | UNCHANGED |
| EXT section 5.3 `G1R-08-Q` | Rejects broker quote/anchor module import | Keep rejection of any broker quote, feed or anchor module. Permit only a pure bid/ask validator over signed fixture quotes | Negative test: no quote-adapter or anchor-module import; `V3EXT-023` | PROPOSED/OPEN |
| ATC-01 rev2 T11 and §5 | OFF, COMPUTE_ONLY, LIVE_TIGHTEN_ONLY; compute-only has no broker-write import | Add `SIMULATOR_ONLY_TIGHTEN` mode with simulator-only call graph, preserving real write denial; keep `LIVE_TIGHTEN_ONLY` unavailable | Simulator allowed, IG denied by code and egress | PROPOSED/OPEN |
| EXT Annex G, WDA §3.1 | Five Annex G axes in EXT/WDA vs the seven axes in the pinned Stage D specification (the five plus master section 3.3's `intent_lifecycle` and `attempt_send_eligibility`) and seven new candidate edges `D03-MST-036` to `D03-MST-042` | Controlled adoption/alignment of 42 candidate edges, 84 denied pairs and three events; add atomic group commit proof | No half-commit or event activation before acceptance | PROPOSED/OPEN |
| D03 risk/ATC stop policies | Some protective/monetary semantics rely on unselected real policy | Signed finite fixture policies drive fully simulated trade tests; real risk values, stop type and G3 authority remain unselected | Fixture value cannot promote into live policy | PROPOSED/OPEN |
| G1-R deny-egress and source intake | Eight-unit first-slice quarantine/build packet | Re-scope to 18-module complete offline build, no IG SDK, zero copied V2 code, sealed/quarantined evidence and no outbound networking | Negative egress/import/archive traversal proof required | PROPOSED/OPEN |
| V3-GOV-48-01 | Proposed unadopted G1-only timing amendment | **Do not adopt** for Path 1 if source-verified standing rules (a),(b) permit grouped wait; retain historical proposal as unadopted | Timing exception not silently assumed | PROPOSED/OPEN |

**Order of operations:** prepare and reconcile these amendments once; obtain independent review of the final consolidated baseline and governance; explicitly dispose owner items; freeze the exact immutable proposal/evidence group; apply its valid 48h interval; then obtain separately signed G0-R and G1-R records in one owner sitting. Any change to group members after presentation restarts its interval under R2's reported rule (b).


---

## PACKAGE MEMBER 05_CONSOLIDATED_61_ROW_OWNER_DECISION_REGISTER_NOT_SELECTED.csv

```csv

decision_id,kind,topic,historic_author_recommendation,consolidated_scope_C_candidate,source,explicit_owner_choice,binding_disposition,review_required
OD-01,STAGE_D_OWNER_DECISION,G0-R route and exact expanded/offline scope,PROVISIONAL_PREFER_R_PLUS_C_SCOPE_SCHEDULE,PROPOSE_R_PLUS_C_FULL_OFFLINE_TRADING; all 16 broker-neutral modules + execution engine + simulator; IG gateway absent,"Master V1.8 §10; EXT-G0R-14 §§1,5; V3-BA-04 A-01/A-02; Stage D03 OD-01",NOT_SELECTED,OPEN,YES
OD-02,STAGE_D_OWNER_DECISION,OC-D03-05: subminimum stakes,PROVISIONAL_PREFER_DENY_NO_STAKE_UPLIFT,No. Deny that new entry rather than increase stake and therefore breach risk sizing. A minimum stake is not permission to increase risk.,Master OC-D03-05; EXT risk-math / broker-budget evidence; Stage D03 OD-02,NOT_SELECTED,OPEN,YES
OD-03,STAGE_D_OWNER_DECISION,GBPUSD rejection strategy / MARKET-only incompatibility,PROVISIONAL_PREFER_DISABLE_GBPUSD_G3_PENDING_COMPATIBILITY,"Keep the strategy defined as research, but do not enable its present limit-entry form at G3. No silent conversion to MARKET.","WG-00; EXT-G0R-14 PAPER-04/PAPER-11, V3EXT-068; BB-04 BF-1; Stage D03 OD-03",NOT_SELECTED,OPEN,YES
OD-04,STAGE_D_OWNER_DECISION,US500 directional policy,PROVISIONAL_PREFER_US500_DIRECTION_DISABLED_PENDING_POLICY,Do not infer LONG_ONLY or allow either side from an old trading strategy. Keep any executable directional eligibility disabled until you select and evidence the policy.,Master DirectionEligibilityPolicy; Stage D03 OD-04,NOT_SELECTED,OPEN,YES
OD-05,STAGE_D_OWNER_DECISION,Stop type / monetary risk maximum / margin/size/FX,PROVISIONAL_PREFER_ALL_REAL_RISK_VALUES_UNSET,"Define typed fields and validation rules in the offline design but leave every real dealing parameter unset. Unknown means deny, not default.",Master §10 C-04/C-05; EXT §2.2; Stage D03 OD-05,NOT_SELECTED,OPEN,YES
OD-06,STAGE_D_OWNER_DECISION,Unprotected position protective response A/B/C and closed market,PROVISIONAL_PREFER_NO_V3_PROTECTIVE_MUTATION_OFFLINE_ONLY__G3_POLICY_DEFER,PROPOSE_OFFLINE_SIMULATED_PROTECTION_TRAILING_AND_STOP_MODIFICATION; IG automated repair/close/cancel still unapproved,"Master OC-D03-08, §10 C-01/C-04; WDA-08 §7; Stage D03 OD-06; R2 final review",NOT_SELECTED,OPEN,YES
OD-07,STAGE_D_OWNER_DECISION,"Ledger evidence conflict U/X, late fills, stale snapshots",PROVISIONAL_PREFER_CONSERVATIVE_UNKNOWN__DEFER_FULL_E4_POLICY,"UNKNOWN remains unresolved; retain gross reservations; do not blindly resend, infer close, net offset or release capital without sufficient proof. This does NOT establish the complete E-4 conflict policy.",Master §3.3; EXT §4.2; Stage D03 OD-07; R2 final review,NOT_SELECTED,OPEN,YES
OD-08,STAGE_D_OWNER_DECISION,Seven PARTIAL B-row contract/exclusion decision,PROVISIONAL_PREFER_TYPE_ONLY_WITH_EXPLICIT_PER_ROW_EXCLUSION,COMPLETE_OFFLINE_TYPES_AND_SIMULATED_BEHAVIOUR; per-row source treatment to be reviewed; not implicit G3 authority,V3-DC-04 Batch B item 5; EXT Annex B; BB-03 seven PARTIAL row mapping; Stage D03 OD-08,NOT_SELECTED,OPEN,YES
OD-09,STAGE_D_OWNER_DECISION,"WDA-08 §10 decisions 1, 3, 9",PROVISIONAL_PREFER_INDEPENDENT_FAILURE_DOMAIN__NO_LATE_BACKDATE__WDA_CANONICAL_CANDIDATE,"Propose a verified separate failure domain (WDA decision 1), require genuinely completed and timely supervision evidence and never back-credit late cycles (decision 3), and propose WDA-08 as the technical home with EXT pointing to an exact hash (decision 9).","WDA-08 §10 decisions 1,3,9; EXT §4.5; Stage D03 OD-09",NOT_SELECTED,OPEN,YES
OD-10,STAGE_D_OWNER_DECISION,Clock alternatives D1..E3 and operational timing,PROVISIONAL_PREFER_EXPLICIT_G0R_OFFLINE_EXCLUSION_FOR_UNSELECTED_CLOCK_MEANINGS,"Preserve typed D1/D2/D3/E1/E2/E3 schemas and negative tests, but make specific unresolved A/B/bracket/closed-market alternatives documented exclusions from restricted offline runtime. No numerical timer operates.",EXT-G0R-14 §4.5; WDA-08 §7; BB-05 choice 12; Stage D03 OD-10,NOT_SELECTED,OPEN,YES
OD-11,STAGE_D_OWNER_DECISION,"Stop Resume, watchguard breaker reset authority",PROVISIONAL_PREFER_NO_AUTOMATIC_RESUME_OR_CLEAR,"Keep local authenticated, persistent Stop as entry-only. Continue monitoring existing positions. No watchdog or restart may reset a breaker; future resume/reset must have its own authenticated and auditable permission and independent prerequisites.","Master C-09; WDA-08 decisions 4, admission; BB-05 choice 8; Stage D03 OD-11",NOT_SELECTED,OPEN,YES
OD-12,STAGE_D_OWNER_DECISION,Review/witness/custody and design-freeze hash control,PROVISIONAL_PREFER_R1_CANDIDATE_ONLY__SEPARATE_APPOINTMENT_CUSTODY_HASH,"Keep original R1 as a candidate reviewer, conditional on documented independence, scope, conflicts and appointment. Separately settle witness/custody and owner-fingerprint approval; the three decisions are NOT one automatic approval.",V3-BA-04 A-06; EXT §7/§8; master K1/H13 and R-01/R-10; WDA-08 §20; Stage D03 OD-12,NOT_SELECTED,OPEN,YES
OD-13,STAGE_D_OWNER_DECISION,Cooling-off placement: one grouped 48h interval then G0-R and G1-R signed in one sitting (Path 1),PROVISIONAL_PREFER_G1_ONLY__SUBJECT_TO_CONTROLLED_GOV48_ADOPTION,PROPOSE_SINGLE_48H_GROUPED_INTERVAL_BEFORE_SEPARATE_G0R_AND_G1R_SIGNATURES_IN_ONE_SITTING; primary proof attached: 27 Oct decision d3f39baa… rules (a) and (b) byte-verified by R2 on 13 Nov 2026,12 Nov owner provisional G1-only response; V3-GOV-48-01 REV3; Stage D03 OD-13,NOT_SELECTED,OPEN,YES
OD-14,STAGE_D_OWNER_DECISION,Stage D ledger and three event type registration,PROVISIONAL_PREFER_REGISTER_ONLY_AFTER_CONTROLLED_ALIGNMENT_AND_INDEPENDENT_CHECK,PROPOSE_CONTROLLED_42_EDGE_LEDGER_ALIGNMENT; no registry activation without review and exact owner record,"Master §3.3; EXT Annex G; WDA §3.1; Stage D03 files 01–04,11–12; R2 final N12",NOT_SELECTED,OPEN,YES
ATC-J1,ATC01_OWNER_DECISION,Adopt this design as the proposed direction for trailing and confidence.,ATC_01_REV2_AUTHOR_DIRECTION_ONLY,"V2's rule becomes the floor. Improvements are tested against it and promoted only on evidence you approve. Alternative: Different direction, or defer.",ATC-01 revision 2 §7,NOT_SELECTED,OPEN,YES
ATC-J2,ATC01_OWNER_DECISION,Allow a controlled split of DEMO trades between V2's rule and a candidate.,ATC_01_REV2_AUTHOR_DIRECTION_ONLY,"Some demo trades use a new rule and others use V2's, assigned by a fixed rule decided in advance. It is the only way to test a rule that gives *more room* than V2's. The shares are yours to set. Alternative: Compute-only plus historical replay: slower evidence, no new rule on the account.",ATC-01 revision 2 §7,NOT_SELECTED,OPEN,YES
ATC-J3,ATC01_OWNER_DECISION,"Eligibility uses the **lower bound** of the calibrated probability against the cost-adjusted break-even (a gate on the label; realised profit under trailing is checked separately, U1).",ATC_01_REV2_AUTHOR_DIRECTION_ONLY,"Stricter than V2. A trade is taken only if we are confident the edge is real, not just that the best guess looks fine. Fewer trades. Alternative: Use the point estimate: closer to V2, more trades, more of them uncertain.",ATC-01 revision 2 §7,NOT_SELECTED,OPEN,YES
ATC-J4,ATC01_OWNER_DECISION,Shorts are ineligible until a short-side label and calibration exist.,ATC_01_REV2_AUTHOR_DIRECTION_ONLY,"This is already D04-03's rule. V2 traded shorts as the complement of a long-side label. It cuts V2 activity until the evidence exists. Alternative: Not a free alternative. Allowing V2-style shorts in DEMO, labelled ""uncalibrated"" and at the lowest stake tier, contradicts U1, ATC-C04 and D04-03, and one selection here cannot activate it. It would be a separate proposed policy exception needing a controlled amendment, DEMO-only limits, stated risk evidence and negative tests. Until then, a short without short-side evidence is ineligible.",ATC-01 revision 2 §7,NOT_SELECTED,OPEN,YES
OC-D02-01,MASTER_BINDING_ITEM,Freeze account-unknown => no mutation; Candidate A stays nonbinding; broker proof at G2.,CARRY_PRIOR_A_AS_NONBINDING_ONLY,CLASS C_CARRY_PRIOR_DECISION: Earlier proposal or owner evidence carried unchanged as candidate; binding status needs proof.,Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D02-02,MASTER_BINDING_ITEM,Freeze manual-IG-only operation boundary and local Stop interface; detailed actor rights stay disabled.,CARRY_PRIOR_SOLE_OPERATOR_IG_ONLY_LOCAL_STOP,CLASS C_CARRY_PRIOR_DECISION: Earlier proposal or owner evidence carried unchanged as candidate; binding status needs proof.,Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D02-03,MASTER_BINDING_ITEM,Freeze no account-switch path and forbid PUT /session; startup selection/proof at G2.,D02_03_NO_RUNTIME_SWITCH_STARTUP_METHOD_DEFERRED,CLASS C_CARRY_PRIOR_DECISION: Earlier proposal or owner evidence carried unchanged as candidate; binding status needs proof.,Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D03-06,MASTER_BINDING_ITEM,Freeze positive V3-owned intent/account linkage and UNKNOWN outcome; broker-close actions disabled.,"D03_IDENTITY_A_SAME_DIRECTION, D03_NO_AUTOMATED_ORPHAN_FLATTEN_DEMO, D03_BROKER_EVIDENCE_CONTRACT_FOR_REVIEW",CLASS C_CARRY_PRIOR_DECISION: Earlier proposal or owner evidence carried unchanged as candidate; binding status needs proof.,Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D06-05,MASTER_BINDING_ITEM,Human IG intervention conditional on proven independent alerting; no manager-down mutation path.,"D06_IDENTITY_A_SAME_DIRECTION, D06_IG_SIDE_HUMAN_INTERVENTION_DEMO",CLASS C_CARRY_PRIOR_DECISION: Earlier proposal or owner evidence carried unchanged as candidate; binding status needs proof.,Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D06-10,MASTER_BINDING_ITEM,Freeze role/authority manifest with emergency responder disabled; independent K1/H13 signing remains open.,D06_FULL_ROLE_AND_EVIDENCE_MATRIX_FOR_REVIEW,CLASS C_CARRY_PRIOR_DECISION: Earlier proposal or owner evidence carried unchanged as candidate; binding status needs proof.,Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D02-04,MASTER_BINDING_ITEM,"Actual key ownership, rate allowance, product/account mismatch require separately authorised IG proof.",PREFER DEFER_BROKER_BUDGET_PRODUCT_MISMATCH_PENDING_EVIDENCE,"CLASS K_KEEP_OFF_UNTIL_LATER_GATE: Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",Corrected Master V1.8 §0.1; prior tag G2,NOT_SELECTED,OPEN,YES
OC-D03-02,MASTER_BINDING_ITEM,Freeze executable bid/ask geometry interface and post-fill recalculation; numeric limits disabled.,PREFER PROPOSE_EXECUTABLE_SIDE_PRICE_AND_GEOMETRY_CONTRACT,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D03-03,MASTER_BINDING_ITEM,"Stop grid, tick, point value and minimum-stop evidence belongs to exact instrument/account.",PREFER PROPOSE_FIVE_INSTRUMENT_GRID_CERTIFICATION_DEFER_VALUES,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag G2,NOT_SELECTED,OPEN,YES
OC-D03-04,MASTER_BINDING_ITEM,R denominator not selected; risk reporting/admission using R must be disabled.,DEFER,"CLASS K_KEEP_OFF_UNTIL_LATER_GATE: Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D03-07,MASTER_BINDING_ITEM,"Confirm channels, partial fills and protection semantics require actual IG evidence.",PREFER DEFER_IG_TECHNICAL_SEMANTICS_PENDING_PROOF,"CLASS K_KEEP_OFF_UNTIL_LATER_GATE: Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",Corrected Master V1.8 §0.1; prior tag G2,NOT_SELECTED,OPEN,YES
OC-D04-02,MASTER_BINDING_ITEM,Freeze reference-to-executable price validation with deny on unproven basis; bounds disabled.,PREFER PROPOSE_SOURCE_TO_IG_BASIS_FAIL_CLOSED,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D05-02,MASTER_BINDING_ITEM,"Freeze typed, account-bound capital/currency interface; no fallback balance; actual values G2.",PREFER PROPOSE_CERTIFIED_ACCOUNT_CAPITAL_ONLY,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D06-08,MASTER_BINDING_ITEM,Freeze credential custody/no-login pre-G2/no shared tokens or streams; actual topology G2.,PREFER PROPOSE_V3_SESSION_CREDENTIAL_AND_BUDGET_ISOLATION,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D03-01,MASTER_BINDING_ITEM,Freeze intent identity separate from model attribution and broker attempt; dedup fields reviewed.,PREFER PROPOSE_IMMUTABLE_INTENT_AND_REISSUE_IDENTITY,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D03-08,MASTER_BINDING_ITEM,Protection A/B/C and B→A remain unselected; all broker remedial actions unreachable.,DEFER,"CLASS K_KEEP_OFF_UNTIL_LATER_GATE: Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D04-06,MASTER_BINDING_ITEM,Freeze stable source-event identity across model/policy version changes.,PREFER PROPOSE_CROSS_VERSION_SIGNAL_IDENTITY_CONTRACT,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D04-07,MASTER_BINDING_ITEM,Anchor yes/no and tolerance open; interface may be a disabled optional pre-send check.,PREFER PROPOSE_ANCHOR_AND_REQUOTE_FOR_REVIEW,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D05-05,MASTER_BINDING_ITEM,Freeze UNKNOWN exposure and conservative reservations with broker-evidenced release.,PREFER PROPOSE_UNKNOWN_OUTCOME_CONSERVATIVE_RESERVATION,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D05-08,MASTER_BINDING_ITEM,Freeze market-only order allowlist and structurally prohibit all V3 working entries.,PREFER PROPOSE_MARKET_ONLY_ENTRY_LIFECYCLE_AND_SESSION_EVIDENCE,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D06-04,MASTER_BINDING_ITEM,D1–D3/E1–E3 unset; no dealing or protection deadline claim.,DEFER,"CLASS K_KEEP_OFF_UNTIL_LATER_GATE: Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D03-05,MASTER_BINDING_ITEM,Freeze no automatic minimum stake uplift; numeric risk approvals deferred.,PREFER PROPOSE_NO_AUTOMATIC_MIN_SIZE_UPLIFT,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D05-01,MASTER_BINDING_ITEM,Account breaker type incl NONE still owner-open; all unselected policies disabled.,PREFER PROPOSE_POSITIVE_ACCOUNT_BREAKER_DESIGN,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D05-03,MASTER_BINDING_ITEM,"Risk fractions, capital caps, margin, drawdown and theme limits unset; no entry.",DEFER,"CLASS K_KEEP_OFF_UNTIL_LATER_GATE: Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D05-04,MASTER_BINDING_ITEM,Freeze outcome-attribution types and UNKNOWN manual closes; count thresholds later.,PREFER PROPOSE_ATTRIBUTABLE_MANUAL_IG_CLOSE_LOSSES_COUNT,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D05-06,MASTER_BINDING_ITEM,Freeze three separate durable latches and limited Resume; local Resume remains open.,PREFER PROPOSE_MANUAL_PAUSE_SEPARATE_FROM_BREAKER_RESET,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D05-07,MASTER_BINDING_ITEM,Freeze admission-versus-open-position-supervision separation; mutation not implied.,PREFER PROPOSE_ENTRY_BREAKER_DENY_WITH_PROTECTION_CONTINUITY,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D05-09,MASTER_BINDING_ITEM,Freeze gross reservations and no unproven netting; exposure limits disabled.,PREFER PROPOSE_GROSS_RESERVATIONS_AND_NO_UNPROVEN_NETTING,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D04-01,MASTER_BINDING_ITEM,"Per-instrument direction, TP/SL/horizon and short-side design not selected.",PREFER PROPOSE_EXPLICIT_PER_INSTRUMENT_DIRECTION_AND_GEOMETRY,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D04-03,MASTER_BINDING_ITEM,Freeze completed-bar/session eligibility and missing-data denial; age values later.,PREFER PROPOSE_FAIL_CLOSED_MISSING_OR_LATE_INPUTS,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D04-04,MASTER_BINDING_ITEM,Frozen A versus retained-refit B unselected; fitting and promotion disabled.,DEFER,"CLASS K_KEEP_OFF_UNTIL_LATER_GATE: Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D04-05,MASTER_BINDING_ITEM,Grade/climate/theme choices and score-based risk disabled until separately decided.,PREFER PROPOSE_SAVED_GRADE_CLIMATE_RULES_WITHOUT_AUTOMATIC_RISK_SCALING,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D04-08,MASTER_BINDING_ITEM,"Freeze source-run, model, reason, timestamp and expired/UNKNOWN event schema.",PREFER PROPOSE_SAVED_REASON_AND_SOURCE_RUN_PROVENANCE,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D06-06,MASTER_BINDING_ITEM,Freeze IANA/calendar/expected-stale state shape; numerical schedules disabled.,PREFER DEFER_PUBLICATION_AND_EXPECTED_STALE_SCHEDULE_VALUES,"CLASS K_KEEP_OFF_UNTIL_LATER_GATE: Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D06-01,MASTER_BINDING_ITEM,Freeze watchdog event and independent witness contract; actual witness later.,PREFER PROPOSE_INDEPENDENT_WATCHDOG_WITH_VERIFIED_FAILURE_DOMAIN,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D06-02,MASTER_BINDING_ITEM,All supervision thresholds and PASS/FAIL/UNKNOWN policy branch remain unselected.,DEFER,"CLASS K_KEEP_OFF_UNTIL_LATER_GATE: Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D06-03,MASTER_BINDING_ITEM,"Real alert route, recipient, independent delivery and deadlines unproven; no dealing.",PREFER PROPOSE_INDEPENDENT_PRIMARY_BACKUP_ALERT_PROOF,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D06-07,MASTER_BINDING_ITEM,Freeze audit event/identity/correlation schema; retention/custody later.,PREFER PROPOSE_AUDIT_RETENTION_AND_EXTERNAL_CUSTODY_CONTRACT,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D04-09,MASTER_BINDING_ITEM,Actual counterfactual data runs and broker price collection unapproved; method later.,PREFER PROPOSE_READ_ONLY_COUNTERFACTUAL_EVIDENCE_PROTOCOL,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D05-10,MASTER_BINDING_ITEM,Freeze acceptance/zero-new-entry semantics and control-to-negative-test identifiers; proof G3.,PREFER PROPOSE_CERTIFICATION_AND_ZERO_TRADE_FAIL_CLOSED_ACCEPTANCE,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag DW,NOT_SELECTED,OPEN,YES
OC-D06-09,MASTER_BINDING_ITEM,"Preregistered trial details, dates and outcome criteria unset; no trial.",PREFER PROPOSE_PREREGISTERED_V2_V3_COMPARISON,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag OFF,NOT_SELECTED,OPEN,YES
OC-D06-11,MASTER_BINDING_ITEM,Owner must choose strict G0 or separately named restricted G0-R scope; none selected.,PREFER PROPOSE_SEPARATE_G0_G1_G2_G3_GATES,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag OD,NOT_SELECTED,OPEN,YES
OC-D06-12,MASTER_BINDING_ITEM,"LIVE, account/product scope expansion and V2 retirement are future separate grants.",PREFER PROPOSE_G4_LIVE_AND_V2_RETIREMENT_SEPARATE,"CLASS D_DESIGN_ADOPTED_FOR_OFFLINE_CORE: Proposed rule for G1 simulator implementation and testing, not yet built or proved; IG proof later.",Corrected Master V1.8 §0.1; prior tag G4,NOT_SELECTED,OPEN,YES

```


---

## PACKAGE MEMBER 06_ORIGINAL_13_FREEZE_FINDINGS_OPEN.csv

```csv

finding_id,old_restricted_tag,prior_treatment,proposed_scope_C_treatment,formal_disposition,review_evidence
D03-FREEZE-01,DW,Specify independent ∅→NOT_SENT and ∅→UNRESOLVED monetary initiation edges.,INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED
D03-FREEZE-02,DW,Specify versioned partial-fill/partial-close/stop-update self-transitions and races.,INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED
D03-FREEZE-03,DW,End active protection surveillance on broker-proven close; retain incident evidence.,INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED
D03-FREEZE-04,DW,"Require V3-owned intent, account and deal evidence for ∅→OPEN_CONFIRMED.",INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED
D03-FREEZE-05,DW,Exclude V3 resting entry orders with unreachable-state proof; foreign-order residue G2/G3.,INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED
D03-FREEZE-06,DW,Version and map REQUESTED/NOT_SENT/OPEN_CONFIRMED/CANCELLED_PRE_FILL and protection taxonomy.,INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED
D04-FREEZE-01,OFF,Only triggered if model Option B is later selected; promotion authority open.,INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED
D04-FREEZE-02,DW,"Inference loads retained hashed artifacts, no silent refit; fitting disabled for G1-R.",INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED
D06-FREEZE-01,DW,Choose a proposed canonical deny enum with explicit 3-way legacy mapping; formal clarification pending.,INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED
D06-FREEZE-02,DW,Include supervision proof in admission shape; no working-entry action; foreign-order residue conditional.,INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED
D06-FREEZE-03,DOC,"Source attribution correction for V2 token paths/dry-run lock; map to isolation, not calendar.",INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED
D06-NOTE-01,DOC,Split and pin individual negative oracles; code tests follow by implemented slice.,INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED
D06-NOTE-02,DW,Declare emergency responder role DEFAULT_DISABLED/NO_BROKER_AUTHORITY in manifest.,INTEGRATE_IN_COMPLETE_OFFLINE_CORE_OR_MARK_IG_ONLY_WITH_EXPLICIT_NEGATIVE_TEST,OPEN,NOT_YET_INDEPENDENTLY_CERTIFIED

```


---

## PACKAGE MEMBER 07_ORIGINAL_21_REPAIRS_OPEN.csv

```csv

repair_id,old_restricted_tag,prior_treatment,proposed_scope_C_treatment,formal_disposition,verification
R-01,DW,Validate curated source-to-direction subject map; reject numeric pairing.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-02,DOC,Correct OC-D04-06 source links; no runtime code dependency.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-03,DOC,Add D06 noninterference source link to comparison.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-04,DOC,Restore full D01 failure-injection list in test-plan trace; execute after G1.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-05,DOC,Restore full D05 stress-oracle list in test-plan trace; execute after G1.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-06,DW,Freeze pre-wire NOT_SENT proof rule; silence is not order absence.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-07,DOC,Correct Draft3 attribution heading.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-08,DOC,Correct D02-01 record V1 filename; preserve hash.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-09,DW,Freeze D1–D3/E1–E3 schema and the full test-source citation; values OFF.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-10,DOC,Repair Group C semantic directions instead of numeric pairing.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-11,DOC,Pin embedded Group C archive hash in inventory.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-12,DOC,Disambiguate PREFER vs DEFER in Group C; add thematic links.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-13,DOC,Mark inherited V1 JSON labels in V2 archive.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-14,DW,Carry DEFAULT_DISABLED emergency role into G0-R role manifest.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-15,DOC,Use source-exact Option C phrase.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-16,DOC,Fix RG-F / G4 attribution in gate rows.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-17,DOC,Pin RG and prior owner evidence lineage; no authenticity invented.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-18,DOC,Pin V2 token and dry-run paths by file/line/snapshot hash; no host claims.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-19,DOC,Reconcile IM/A39/38-row lineage as evidence; not 43 semantic links.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-20,G3,Actual exercised oracles and five IG certifications must be proven later.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW
R-21,DW,Source-to-direction meaning and dependency/gate tags per row; not owner decision.,TRACE_TO_FULL_OFFLINE_CORE; DOCUMENTARY_OR_IMPLEMENTATION_PROOF_AS_TAGGED,OPEN,PENDING_INDEPENDENT_REVIEW

```


---

## PACKAGE MEMBER 08_ACCEPTANCE_TEST_CONTRACT_AND_FAILURE_MATRIX.md

# Offline-core acceptance and adapter conformance test contract (NOT_RUN)

**Status:** all tests here are design specifications; no software implementation, simulated trade, IG call, market backtest or failure injection has been executed by this deliverable. Historic Stage D03 has 187 synthetic specifications, not 187 passing tests. Link them under controlled review; do not replace or silently renumber them.

## Pre-registered result fields

Each executed case must record `case_id`, environment/build SHA, fixture-policy SHA, simulator version, signed source-event ID, account-scope (synthetic), initial state, injected failure, expected and observed state/evidence, resulting ledger-event IDs, requested and applied stop, writer fence, no-IG-import/egress result, source hashes, pass/fail and reviewer.

| Family | Required cases | Pass oracle |
|---|---|---|
| TC-DATA | forming bar, missing macro, stale bar, DST, no-price, market closed | no eligible trade without fresh completed fixture input |
| TC-MODEL | wrong model hash, missing calibration artifact, unapproved refit, source-version collision; and the 19 cases MSB-01..MSB-19 of file 24 (intake gates, hostile pickle, static import scan, unavailable model, registration under a frozen contract, source identity, labelling, no cross-substitution) | no eligible new entry; no duplicate intent after model rerun; NO_AUTHORITATIVE_PREDICTION on any gate failure |
| TC-CONF | mislabeled score, side-specific short absent, lower-bound vs point-estimate, drift, positive/negative net realised R-by-band | no unjustified confidence tier; safe denial |
| TC-STRAT | missing executable-side bid/ask, reference-close discrepancy, wrong-side stop, GBPUSD limit-market conversion, US500 side absent | deny invalid geometry or unsupported strategy, while independently allowing valid fixture scenario |
| TC-RISK | below-minimum stake, FX conversion mismatch, simultaneous pending exposure, unsupported netting, breaker trip, missing capital | deny or conservatively reserve, no uplift or fictitious capital |
| TC-ENGINE | prewire crash, one-attempt rule, duplicate event, true distinct event, journal failure, close/fill race | single attempt per intent, UNKNOWN stays reserved, atomic ledger |
| TC-SIM | rejection, UNKNOWN despite execution, delayed read, partial fill/close, external widen, wrong account, stale quote | simulator reflects ambiguous evidence; cannot claim VERIFIED without proof |
| TC-INIT | accepted-but-not-filled, partial/full fill before protection read-back, absent/rejected initial stop, uncertain stop outcome, crash or audit failure, quantity/stop mismatch | protection never `PROTECTION_VERIFIED` before authoritative applied-stop and quantity proof; full reservation and alerts on uncertainty (TC-INIT-01..10) |
| TC-ATC | V2 reference tiers, DV1–DV4 safety divergences, C1–C4 compute-only candidate, BE/trail, failed stop readback, no retry | tighten only; reference parity exact on pinned inputs and every safe divergence logged; no IG writes |
| TC-RECON | lost ack then fill, duplicate fill, partial snapshot, unknown close P&L, late terminal evidence | reconciliation never promotes silence/timeout to rejection or closure |
| TC-STATE | seven-axis transitions, 42 edges/84 denied complements, atomic multi-axis failure, STOP persistence, blackout alert | no partial commit, no false delivered/acknowledged or reset, all invalid edges denied |
| TC-AUDIT | disk full before simulated stop move, malformed actor ID, tamper, stale heartbeat, skipped completed-cycle proof | no unaudited mutation; watchdog cannot self-attest; evidence preserved |
| TC-COMP | V2/V3 observation pairing, censored trade, stop earlier than theoretical TP, spread/contract mismatch, lookahead attempt | no fabricated realised result or falsely comparable cohort |
| TC-ISOLATION | direct IG hostname/DNS/IP/redirect/socket/stream, nested archive secret, unsafe path, unpinned mirror/lockfile | real network denied, secret intake quarantined, zero broker/credential imports |
| TC-INSTR | missing, extra or wrong-typed definition field; T3 value overriding a T2/T1 check; unmanifested or dynamically discovered plug-in; stale or uncertified listing; second synthetic instrument added by definition plus fixture only; synthetic equity of 1,000, 10,000 and larger with a below-minimum stake | unknown field or check denies entry; zero source and zero manifest change for the second instrument (`V3EXT-001` to `V3EXT-011`); no hard-coded instrument and no hard-coded minimum equity |

## Initial protection acceptance oracles — TC-INIT (all NOT_RUN)

| ID | Deterministic fixture event trace | Required oracle |
|---|---|---|
| TC-INIT-01 | Entry intended with missing/unsupported protected-fill capability | `DENY_PRE_ENTRY`; no fill or position; no unguarded entry intent sent |
| TC-INIT-02 | Market request ACCEPTED but no fill or independent stop read-back | Order acceptance only; NOT OPEN/VERIFIED; reservation remains until authoritative terminal evidence |
| TC-INIT-03 | First partial fill with requested stop but no read-back | position `OPEN_CONFIRMED`, protection `PROTECTION_UNVERIFIED`, reserve filled and possible unfilled risk, freeze trailing/next entry, incident/alert |
| TC-INIT-04 | Full or partial fill followed by matching account/position/quantity/stop proof | `PROTECTION_VERIFIED` only after proof; position exposure remains reserved; correct protection version |
| TC-INIT-05 | Filled position with stop rejected, absent, wrong-side or worse than last verified stop | Never VERIFIED; no blind retry; preserve gross reserve; freeze trailing, alert |
| TC-INIT-06 | Stop amendment returns UNKNOWN but was secretly applied; snapshot incomplete/late | Remain UNKNOWN until attempt-specific authoritative read-back; no second send of same intent |
| TC-INIT-07 | Crash, audit disk-full, or restart between fill and protection read-back | Restore pending/UNKNOWN with exposure; fail closed; no fictitious rollback, no automated repair |
| TC-INIT-08 | Partial close/fill/stop-update race with duplicate, conflicting or reordered events | Atomic seven-axis transitions or DENIED; correct open quantity; never overwrite later verified stop with stale evidence |
| TC-INIT-09 | Latest position read shows a smaller/larger quantity than stop covered | Protection unverified; gross exposure retained and no further trailing until authoritative revalidation |
| TC-INIT-10 | Explicit fixture-only rescue simulation of absent stop | No real IG authority, no implicit emergency close; test response selected fixture only and separately audited |

The 187 detailed Stage D03 test specifications and ledger sources are included as immutable bytes under `SOURCE_PINS_UNMODIFIED/STAGE_D03_REVIEW_BYTES/`; this table is additive and does not claim any of them has executed.

## The single two-adapter suite

For every common broker operation defined in `03_...`, implement the same deterministic contract checks with a simulator adapter and with a future IG adapter. Offline runs execute **simulator only**; the IG conformance plan is frozen as tests but actual IG execution remains separately gated. Broker-specific unavailable semantics must be marked NOT_PROVEN, not mocked as an IG guarantee.

## Go/no-go test disposition

A test failure involving financial exposure uncertainty, intent retries, stop truth, audit integrity, external egress, account scope, confirmed close, atomic state or source provenance is safety-blocking for the affected release. Statistical tuning, sample sufficiency and policy-value choices can be parameterized and recorded at the correct gate, provided the build cannot accidentally enable an unselected real-money policy.


---

## PACKAGE MEMBER 09_G1R_PREFLIGHT_EVIDENCE_INVENTORY_NOT_ATTESTED.csv

```csv

evidence_id,required_artifact,needed_by,current_status,acceptance_evidence,evidence_file_hash,attesting_actor
G1-01,Final full R+C module + source amendment list,G0 acceptance,NOT_READY,Signed exact build/module/deny list and approved scope amendment,UNSET,UNASSIGNED
G1-02,Independent review of complete offline core and source alignment,G0 acceptance,NOT_READY,"Distinct reviewer, findings closure and attested proof",UNSET,UNASSIGNED
G1-03,Independent reviewer of WDA-08 and ATC-01,G0 acceptance,NOT_READY,Cannot be R2 as author; appointment and independence evidence,UNSET,UNASSIGNED
G1-04,Owner-selected 14 Stage D + 4 ATC decision dispositions,G0 acceptance,NOT_READY,Exact selection evidence including OD-08 subrows and OD-12 subparts,UNSET,UNASSIGNED
G1-05,43/13/21 controlled disposition and source precedence,G0 acceptance,NOT_READY,"Each item classified without implicit closure, supported by evidence",UNSET,UNASSIGNED
G1-06,Exact 42-edge/3-event source alignment and cross-axis atomicity,G0 acceptance,NOT_READY,"Controlled text, reviewer proof and N12 half-commit negative spec",UNSET,UNASSIGNED
G1-07,Signed environment deny-egress and no-IG-import policy,G1 before clock,NOT_READY,Owner/authorised independent signatory + immutable environment manifest,UNSET,UNASSIGNED
G1-08,"Source quarantine secret scan, nested archive and deletion plan",G1 before clock,NOT_READY,"Actual scan report, hashes, quarantine custodian, fail-closed nested cases",UNSET,UNASSIGNED
G1-09,Zero V2 runtime/source bytes import graph and dependency proof,G1 before clock,NOT_READY,"Pinned build graph, scan, code reuse audit against V2",UNSET,UNASSIGNED
G1-10,"Pinned package mirror, lockfile, dependency hashes and redirect negatives",G1 before clock,NOT_READY,Actual lockfiles and controlled mirror proof or explicit NO_MIRROR policy,UNSET,UNASSIGNED
G1-11,"Named hostile negative tests, expected outcomes and environment paths",G1 before clock,NOT_READY,Test manifests and independent negative test design; no false PASS,UNSET,UNASSIGNED
G1-12,"Signed release and witness/custody, K1/H13 and quorum",Before sitting,NOT_READY,Actual human identities/signatures/external custody evidence,UNSET,UNASSIGNED
G1-13,"27 Oct approved 48h duration/rules (a),(b), exact primary record",Before final group presentation,NOT_VERIFIED_IN_THIS_PACKAGE,"R2-reported source; final original record/hash required, not PENDING_V1",UNSET,UNASSIGNED
G1-14,Full final evidence bundle fixed and hash-complete,Before 48h,NOT_READY,"Every member final hash, full proposal presented as one indivisible group",UNSET,UNASSIGNED
G1-15,48 elapsed hours since last group presentation without changes,Before sitting,NOT_STARTED,"Trusted UTC start/end, signed evidence, no byte/scope changes",UNSET,UNASSIGNED
G1-16,G0-R independent design acceptance exact SHA,Sitting,UNSIGNED,Owner G0 record signed only after verified wait and independent proof,UNSET,UNASSIGNED
G1-17,G1-R implementation grant exact SHA,Sitting,UNSIGNED,Separately signed owner G1 record; no implementation before it,UNSET,UNASSIGNED

```


---

## PACKAGE MEMBER 10_GOVERNANCE_CONFORMANCE_AND_SINGLE_48H_RULE.md

# Grouped 48h cooling-off and dual signature in one sitting — PROCEDURAL CANDIDATE

**Working Path 1: recommended by R2 and sent to the author at the owner's request (13 Nov 2026); recorded as OD-13 and binding only through the owner's signed records.** One indivisible final evidence-bound group, a single full **48 elapsed hours** after the last final presentation, then two separate owner forms (G0-R exact-hash design approval and G1-R exact-hash implementation grant) executed at the **same owner sitting**, and no coding before G1-R signature. This rests on rules (a) and (b) of the owner-approved 27 Oct decision, attached under `SOURCE_PINS_UNMODIFIED` (`A39_GROUP1_COOLING_OFF_OWNER_DECISION_V2.json`, SHA-256 `d3f39baa…`, bytes verified by R2). A local historical `PENDING_V1` placeholder is specifically NOT relied upon. If primary text contradicts this route, stop and present the exact clause, not an inferred exception.

## Requirement-level source and remaining proof

| Requirement | Primary source | Proposed route compliance | Remaining condition |
|---|---|---|---|
| Group 1 principle 3: cooling-off between final proposal and final approval | Group 1 principles approved-source SHA `be6dad1f…` | Freeze entire final group and wait 48h before final owner signatures | Final presentation proof and exact 48h proof; no earlier signatures |
| Group 1 principle 5: review/quorum and independent controls stay | Group 1 principles, V1 record/V2 addendum | Preserve reviewer independence, witness/custody and K1/H13 countersignatures; do not substitute R2 or AI author | Human appointment, attestation, signatures and copy outside workspace |
| 27 Oct rule (a): grouped interval | Owner-approved cooling-off decision (attached) SHA `d3f39baa27d8a8c91050d19dea32d83883b73eb1ddb80cf4d89dcfbee534143b` | One interval covers separately presented G0-R/G1-R final proposals and evidence if all fixed together, starts after **last** presentation | Decision attached and byte-verified; end-to-end group hashes are fixed at the final presentation |
| 27 Oct rule (b): restart on change | Same 27 Oct owner record | Any change of proposal text, scope or SHA restarts whole indivisible group | Full group diff/restart tracking and no reused time credit |
| Master §0 / §10 distinct G0 and G1 grants | Corrected Master V1.8 SHA `dce9968e…` | Two separately signed fingerprinted records in one sitting after the group hold; G1 not automatic | Exact owner signatures and review proof; separate record IDs |
| EXT §7.1 / §8.1 scope and preimplementation controls | EXT-G0R-14 SHA `256ad6bd…` | Exact R+C scope, module and test manifest, approved environment and deny-egress package before clock | Controlled amendment + signed environment and negative-test inventory |
| Controlled source amendment | Master + EXT + Stage D + ATC-01 | Exact old/new text in `23_CONTROLLED_AMENDMENT_EXACT_TEXT.csv`; purposes in `04_...` | Adopt exact controlled amended text and add hashes to final group |
| WDA/ATC authors not independent reviewers | WDA-08, ATC-01 rev2 | Require separate independent reviewer of those sources | Appointment and actual review attestation |
| V3-GOV-48-01 timing alternative | GOV-48-01 REV3 was proposed, not adopted | Do not treat alternative as active or finish its review if Path 1 source-verified | Preserve unadopted status; no implicit change to standing timing |

## Exact sequence INSIDE ONE CONSOLIDATED STAGE

1. Complete all design and G1-R preimplementation artifacts, with verified reviewer/custody/signature procedures. Resolve owner selections **before** final evidence-bound presentation, but no final G0/G1 acceptance signature before the waiting interval. A selection made before the presentation is a provisional input that becomes binding only through the two signed records at the sitting; a selection changed after the presentation is a change to the group and restarts the interval.
2. Seal the **final** indivisible group: core design + controlled source amendments; 61-row consolidated decisions plus all explicit 43/13/21 dispositions; G1 build/environment manifests and genuine evidence; independent review; both unsigned owner forms; source/governance proof. Hash every member and group root. Present **every** final evidence-bound member to owner; record the latest actual presentation timestamp from a trusted clock.
3. Wait a full 48 elapsed hours from the last presentation. Change to any member's bytes/scope/hash -> void previous group interval, re-freeze/re-present whole set and restart. No design or implementation acceptance during hold.
4. When validly elapsed and when human independence, quorum, witness, K1/H13 and custody conditions hold, owner sits **once** and signs G0-R design acceptance **and** a separately identifiable G1-R grant against exact hashes. A single sitting does not mean a single combined signature substitutes for the two records.
5. Implementation may commence **only** after the actual G1-R signed record is verified. No clock triggers deployment by itself. IG integration, DEMO/LIVE use and V2 retirement remain separate future controlled authorisations.

**Important:** Neither preparing this package nor acknowledging this plan constitutes `WAIT_START`. No user-visible or internal clock begins until an independently verifiable presentation of the genuinely final group occurs. No timer is running now.


---

## PACKAGE MEMBER 11_INDEPENDENT_VERIFICATION_AND_QUORUM_RECORD_UNSIGNED.md

# Independent verification / custody / signatures — UNEXECUTED

**Not a performed review.** The source evidence includes R2's bounded 56/56 Stage D03 documentary replay, an ATC-01 revision-2 author's own checks and some prior source checks. These do **not** constitute an independent acceptance of this newly consolidated full offline-core scope, WDA-08 or ATC-01.

| Required role / item | Identity / proof | State |
|---|---|---|
| Full offline-core architecture independent reviewer | `[NAME; affiliation; conflicts review; signature]` | UNASSIGNED |
| WDA-08 independent reviewer (not R2) | `[NAME; proof of independence]` | UNASSIGNED |
| ATC-01 independent reviewer (not R2) | `[NAME; proof of independence]` | UNASSIGNED |
| Required quorum/owner role crosswalk | `[source exact requirement -> verified actors]`; must state whether CAR-01 (Group 1 V1 record, `next_controlled_contract_decision`, status NOT_APPROVED_NOT_PERFORMED) is decided inside this group before a sole-owner record can stand in for the V32 independent-reviewer and quorum rules, K1/H13 countersignatures and two-person rules that Group 1 principle 5 keeps in force, or whether the V32 text shows that a control does not apply to an offline-only grant | UNRESOLVED |
| K1 / H13 countersignature obligations | `[actual signatures/role determination]` | NOT SATISFIED |
| External custody and outside-workspace copy | `[custodian; hash verified; timestamp]` | NOT ATTESTED |
| Scope/design finding closure | `[finding IDs; evidence; independent reviewer]` | NOT PERFORMED |
| G1-R environment/capability proof | `[test/build hashes; actual negative outcomes]` | NOT PERFORMED |

### Reviewer attestation template (blank)

- Reviewer name and verified independence: `________`
- Group baseline root/hash checked: `________`
- Evaluated core module count / 13 components / 61 decisions / 13 freeze / 21 repairs: `________`
- Blocking findings (IDs and location): `________`
- Explicit exceptions with later-gate denial test: `________`
- Confirmation all 16 original modules plus two new offline modules are mapped, and IG gateway absent: `________`
- Evidence of atomic group journal and simulator uncertainty contracts: `________`
- Signed reviewer attestation and timestamp: `________`

**Review standard:** each component is checked once for responsibility, interface, fail-closed invariant and default, remaining UNSET/gate and test contract. Parameters or tuning are recorded, not repeatedly reviewed, unless they are necessary to prove a safety invariant. An AI-authored review is not falsely represented as a human countersignature.

**See `19_GROUP1_INDEPENDENCE_APPLICABILITY_OWNER_ROUTE_NOT_SELECTED.md` for the mandatory source-clause crosswalk and the three alternatives. No option has been selected, and one ordinary witness cannot substitute for a required quorum.**


---

## PACKAGE MEMBER 12_G0R_DESIGN_OWNER_ACCEPTANCE_FORM_UNSIGNED.md

# G0-R: one owner acceptance of the complete offline-core design — BLANK / UNSIGNED

**Owner action required only after full final group presentation, valid 48h wait and independent evidence.** This form is an artifact for review; it is not executable approval merely by inclusion in a ZIP.

- Final accepted immutable group root SHA-256: `________________`
- Final core-design baseline SHA-256: `________________`
- Controlled source amendments AM-01..AM-14 exactly as in `23_CONTROLLED_AMENDMENT_EXACT_TEXT.csv` (its SHA-256) and the adopted amended-source hashes: `________________`
- Owner-selected Master Option R / EXT Option C (yes/no): `________________`
- MS-B dual-source predictions, no refit: file 24, file 25 and tests MSB-01..MSB-19 exactly as hashed; OC-D04-04 stays DEFER and no model cadence is selected (yes/no): `________________`
- Full component schedule hash and all 16+2 dispositions: `________________`
- Formal 14 Stage D decisions + 4 ATC decisions (all identified) hashes and values: `________________`
- All 43 master dispositions, all 13 freeze-finding dispositions, all 21 repair dispositions: `________________`
- Independent review and quorum/witness/custody evidence hashes: `________________`
- 27-Oct rule (a)/(b) primary source hash and applicability: `________________`
- Last complete presentation UTC / cooling-off completion UTC / elapsed hours: `________________`
- Scope exclusions: IG integration, real broker mutations, V2 runtime modifications, DEMO/LIVE and model fitting/promotion unapproved; the only prediction sources are signed test scores and owner-registered non-executable trained models under MS-B (file 24): `[CONFIRM]`
- Accepted residuals, each with denial gate/test and later owner gate: `________________`

**Proposed owner acceptance text (NOT spoken or selected):**

> I accept, for DESIGN_ONLY and broker-independent offline implementation planning, the complete War Rig V3 core under Master Option R and EXT Scope C, against the exact immutable hashes entered above. This includes simulated trading, confidence-based strategies and sizing, TP/SL, adaptive trailing and verification, risk, ledger, watchdog, audit, dashboard and comparison. I separately acknowledge that this G0-R acceptance alone grants no implementation, IG, DEMO or LIVE authority. All listed open or deferred items retain their recorded denials. I have reviewed the independent evidence, signature/quorum/custody proof and completed grouped 48-hour hold under the governing rule.

Owner identity/signature: `________`  UTC: `________`  Independent/countersignature proof: `________`.

**Current state: NOT_SELECTED / NOT_SIGNED / NOT_ACCEPTED.**


---

## PACKAGE MEMBER 13_G1R_OFFLINE_IMPLEMENTATION_GRANT_FORM_UNSIGNED.md

# G1-R: separate full offline-core implementation grant — BLANK / UNSIGNED

**May be signed in the same sitting as G0-R, but it is a distinct approval record.** The full 48-hour grouped wait and independent checks must already be valid and G0-R must have been signed first. Implementation never starts merely because the interval ended.

- Exact same final group root SHA-256 used for G0-R: `________________`
- Executed G0-R acceptance ID, SHA-256 and timestamp: `________________`
- Approved full 18-row offline module/build scope and manifest hash: `________________`
- Signed environment/build deny-egress policy hash and actual egress-negative-test evidence: `________________`
- Quarantine/secret-scan outcome and custody evidence hashes: `________________`
- No-IG-import, no-V2-runtime, zero-V2-source-bytes and dependency graph evidence hashes: `________________`
- Pinned package mirror/lockfile hashes (or signed no-mirror policy): `________________`
- Complete simulator shared contract-test manifest and negative test IDs: `________________`
- Named implementation operators, permission boundaries and handoff safeguards: `________________`
- Independent verification, quorum, witness/custody and K1/H13 proof: `________________`
- Cooling-off start/end UTC and restart-free elapsed 48h evidence: `________________`
- Confirmation: NO real IG credential/account/API/session/stream; NO actual IG write or login; NO production V2 filesystem change; NO DEMO/LIVE: `[CONFIRM]`

**Proposed owner grant text (NOT spoken or selected):**

> I grant G1-R offline implementation **only** of the complete V3 broker-independent trading core defined by the exact hashes above, using signed simulated fixtures and a network-denied, no-IG environment. This includes the offline simulator, market data, prediction from two sources under the MS-B contract of file 24 (signed test scores for pipeline validation; owner-registered non-executable trained models, none of which is registered at presentation; no model is fitted or promoted), confidence, TP/SL, risk, simulated order/position lifecycle, adaptive trailing, reconciliation, audit, watchdog, dashboard and comparison tests. This grant excludes real IG operations, V2 production changes and DEMO/LIVE authority. The corresponding G0-R design acceptance is separately signed; the 48-hour group interval and all prerequisite human and technical evidence have been verified.

Owner identity/signature: `________`  UTC: `________`  Witness/countersignature: `________`.

**Current state: NOT_SELECTED / NOT_SIGNED / NO IMPLEMENTATION AUTHORITY.**


---

## PACKAGE MEMBER 14_GROUP_48H_CLOCK_NOT_STARTED.json

```json

{
  "package_id": "V3-ONE-STAGE-OFFLINE-CORE-CANDIDATE-20261113-V5",
  "status": "NOT_STARTED",
  "interpretation": "PATH1_ON_OWNER_APPROVED_27_OCT_RULES_A_AND_B_VERIFIED_FROM_ATTACHED_BYTES",
  "group_mode": "ONE_INDIVISIBLE_GROUP",
  "group_finalized": false,
  "group_root_sha256": null,
  "latest_final_evidence_bound_presentation_utc": null,
  "wait_completed_utc": null,
  "group_changed_since_presentation": "NOT_APPLICABLE_NOT_PRESENTED",
  "G0R_owner_acceptance": "UNSIGNED",
  "G1R_owner_grant": "UNSIGNED",
  "implementation_permission": false,
  "governing_duration_primary_decision_sha256": "d3f39baa27d8a8c91050d19dea32d83883b73eb1ddb80cf4d89dcfbee534143b",
  "primary_decision_file_verified_locally": true,
  "restart_rule": "Any changed text/scope/hash/evidence member after last group presentation restarts the entire indivisible group",
  "notes": "No timestamp fabricated; preparation is not final presentation or owner approval.",
  "required_duration_hours": 48,
  "duration_elapsed_hours": 0
}

```


---

## PACKAGE MEMBER 15_READINESS_BLOCKERS_AND_UNSET_VALUES.md

# Readiness to present a final immutable group — current blockers / NOT a new stage

This file keeps the process to **one consolidated owner stage**. These are **conditions inside that stage**, not new approval stages. Only a safety defect, master contradiction, unbuildable core contract, misrepresented approval, or missing required human evidence blocks presentation. Numeric fixture tuning may be decided at implementation; unselected values can never authorise real money dealing.

## Remaining substantive completion items

1. **Scope:** Owner has not yet selected exact Master R + EXT C in a controlled register. Original master §3.1A eight-unit restriction must be amended to all broker-neutral offline modules, and paired simulator/IG isolation semantics independently checked.
2. **Decision register:** 14 Stage D and 4 ATC decisions, all 43 master binding questions, 13 freeze findings and 21 repairs remain unselected/open in this candidate. Convert proposals into explicit owner choices and verified dispositions once; do not infer consent from today's request to generate a package.
3. **Source corrections:** EXT §1.1, master §3.1A, OD-01 and OD-06, V3EXT-070, ATC-T11/§5 and the proposed seven-axis/42-edge alignment need controlled final amended source artifacts. The immutable historical pins here are **not amended**.
4. **Technical completeness:** Full offline interface contracts are specified here; independent checker must validate executable feasibility including simulated protection, fixture-only controls, position-closed truth and no-IG capability proof. Stage D03's N12 cross-axis atomicity test contract still needs authoritative alignment. All tests listed are NOT_RUN.
5. **Evidence of reviewer independence:** R2 authored WDA-08 and ATC-01; R2 cannot certify those independently. Reviewer appointment, actual reviewer evidence, quorum, K1/H13/witness and external custody are not supplied and cannot be auto-attested by the author. Only the owner can settle this, once, by choosing one of: name real independent humans for the controls in force; include a CAR-01 decision in this same group; or record from the V32 text that the control does not apply to an offline-only grant.
6. **G1-R packet before group presentation:** signed deny-egress environment policy, real quarantine secret-scan report, build graph, no-V2-bytes proof, mirror/lockfile hashes, and hostile-test manifest all need actual evidence with hashes. Plans for tests are not results.
7. **Primary timing proof:** done. The owner-approved 27 October decision (`A39_GROUP1_COOLING_OFF_OWNER_DECISION_V2.json`, `d3f39baa…`) is attached and byte-verified: 48 elapsed hours, rules (a) and (b). Remaining: record the final-group manifest and the presentation time (UTC) at the final presentation. `V3-GOV-48-01` is not needed under Path 1.
8. **Group presentation:** after final evidence and all source/decision/document values are fixed, record a final indivisible group member manifest, exact SHA256s, latest actual presentation UTC, and the 48 elapsed hours with no changes. This candidate itself is not that final group; changes after presenting would restart the wait.
9. **Two records in one sitting:** G0-R acceptance and G1-R grant require different exact fingerprint records, executed in that order at one owner sitting. No automatic permission after the clock.

## Values deliberately UNSET (not blockers to simulation architecture)

- G3 IG account/epic/product point value, minimum stake/stop/step and stop modification guarantee for five markets;
- real GBP monetary caps, equity/margin/FX/live risk ratios, instrument trade authority and any LIVE exposure limit;
- six D1–D3 / E1–E3 operational clock values, alert recipients/channels, delivery/ACK SLAs;
- active V3 model training cadence and release/promotion authority;
- Core-5 frozen model artifacts (none registered or eligible in the inspected locations; other hosts and S3 not checked; MS-F fit-and-freeze authorisation if wanted), the registered parity tolerance, and the live-folder hash of `live_inference.py` (`PENDING_OWNER_CHECK`);
- per-instrument and per-regime adaptation parameters, candidate split shares and threshold values;
- actual human protective-response A/B/C, backup owner and closed-market IG rescue procedures;
- requested IG-specific quote/confirmation/retry semantics and actual operational data delivery;
- calibrated side-specific short-model production proofs.

Every simulation test must carry a **signed fixture-scoped** value and a negative test proving it cannot be silently promoted into IG authority. No IG gate is activated by this document.

**Bottom line:** The package is ready to review and complete **in one consolidated round**, but is **not yet acceptance-ready** and **must not start the 48-hour clock** until all indicated final group membership and approval prerequisites are genuinely complete.

**Independence applicability crosswalk:** `19_GROUP1_INDEPENDENCE_APPLICABILITY_OWNER_ROUTE_NOT_SELECTED.md` retains Group 1 principle 5, names CAR-01 and the three real choices (human compliance, controlled CAR-01 replacement, source-exact nonapplicability). **None is selected.** The original V32 contract clauses remain missing in this group; a human independent reviewer is not yet appointed.

**Second-review clarification:** core eligibility, simulated monetary risk/exposure, stop monitor and reconciliation are required runtime capabilities in G1-R fixture scope and cannot be deferred as mocked schemas. See `02_...csv`, `03_...` and TC-INIT tests. The candidate publisher and the real quote/anchor module remain excluded; the trained-model loader is limited to the single MS-B intake module of file 24.


---

## PACKAGE MEMBER 16_SOURCE_PROVENANCE_AND_COUNTS.json

```json

{
  "owner_task": "generate one consolidated offline-core acceptance+implementation package after R2 Path1 message",
  "sources": {
    "SOURCE_CORRECTED_V1_8_MASTER_UNCHANGED.md": {
      "sha256": "dce9968ec3645cd03b786409c86eeb513826df9b6d14b340533973b7c08aafdd",
      "bytes": 146386
    },
    "War_Rig_V3_Configurable_Instrument_Offline_Extension_Contract_EXT_G0R_14_PROPOSED_20261112.md": {
      "sha256": "256ad6bd0d78f30e5e005f4fde64f13021d36286c8512640b2adf91a62153092",
      "bytes": 214694
    },
    "War_Rig_V3_Watchdog_and_Audit_Contract_WDA_08_PROPOSED_20261112.md": {
      "sha256": "01697219278154ac808cebdafc6575b93a5ea7ca9cbb2310331a5b30f78966c6",
      "bytes": 135145
    },
    "War_Rig_V3_ATC_01_Adaptive_Trailing_and_Trading_Confidence_Design_Proposal_R2_20261113_rev2.md": {
      "sha256": "ce5301c17b7a8e17b161bea808e4691986b8943b99edc416e0062ff482cf8039",
      "bytes": 37495
    },
    "V3_STAGE_D_14_OWNER_DECISIONS_RECOMMENDATIONS_FOR_REVIEW.md": {
      "sha256": "f16c01ebab2896ecf745b41cfa545c7e5573879ec9874476ac31563de9511b27",
      "bytes": 28899
    },
    "V3_STAGE_D_14_OWNER_CHOICE_MATRIX_NOT_SELECTED.csv": {
      "sha256": "f905bc36c914bada28d42915dbb1d8cafa247d09d71c9252e1cb5375dedc6d8b",
      "bytes": 14430
    },
    "00_STAGE_D01_INTEGRATED_TECHNICAL_SPECIFICATION.md": {
      "sha256": "ae373e60fb136bde6a85862cdb466b6370d1d1af7a7c387d3ecb910c07706dc7",
      "bytes": 31033
    },
    "War_Rig_V3_D05_Risk_Controls_Limits_Circuit_Breakers_Design_Proposal_V2.md": {
      "sha256": "8bedfe2e61466761057831f63ff548900b39b1a81ce419b43be02d5a7c683959",
      "bytes": 35970
    },
    "War_Rig_V3_D06_Operations_Monitoring_Comparison_Design_Proposal_V2.md": {
      "sha256": "72237fb08f13be3d8d37af2fb7149cd8297f4263340106a8106de22f8c66f5c4",
      "bytes": 45243
    },
    "A39_GROUP1_PRINCIPLES_V2_PROPOSED_20261027.md": {
      "sha256": "be6dad1f3247cf882a1912e91bc67c979e0f605d03ece1f3dcfb424d2d132e15",
      "bytes": 6852
    },
    "A39_GROUP1_PRINCIPLES_OWNER_APPROVAL_RECORD_V1.json": {
      "sha256": "8906d7e62467509d7216b41181c77591ec026fc7504cb574dbdb0a85d2192d34",
      "bytes": 4462
    },
    "A39_GROUP1_PRINCIPLES_OWNER_APPROVAL_RECORD_ADDENDUM_V2.json": {
      "sha256": "e5d3bc2bfbc86e18af1c4e0f29fbe60bf096033c87e3c5483b3f7f04534fd2ab",
      "bytes": 6728
    },
    "R2_final_rerun_V3_Stage_D03_20261113.md": {
      "sha256": "b60c98c4d87924286a0530bde3bf307a10dadde354bf5d4fea472c19f2a7d8f4",
      "bytes": 13652
    }
  },
  "primary_owner_decision": {
    "name": "27-Oct owner-approved grouped 48h decision, rules (a) and (b)",
    "file_in_package": "SOURCE_PINS_UNMODIFIED/A39_GROUP1_COOLING_OFF_OWNER_DECISION_V2.json",
    "sha256": "d3f39baa27d8a8c91050d19dea32d83883b73eb1ddb80cf4d89dcfbee534143b",
    "status": "ATTACHED_AND_HASH_RECOMPUTED_FROM_BYTES_BY_R2_20261113"
  },
  "additional_group_members": {
    "note": "Added by the R2 review so that every hash the baseline relies on is fixed in this group.",
    "stage_d03_zip": {
      "file": "War_Rig_V3_StageD03_Bounded_Mechanical_Residual_Fixes_20261113.zip",
      "sha256": "23bdbe3b7d0d34b8b1d19fd78daf9990b7ea89b506634da7d4953cea9ef67ead",
      "members_pinned_here": {
      "00_STAGE_D01_INTEGRATED_TECHNICAL_SPECIFICATION.md": "ae373e60fb136bde6a85862cdb466b6370d1d1af7a7c387d3ecb910c07706dc7",
      "01_EDGE_CONTRACTS_35_DRAFT.json": "eb9e29e14514988f6008815dbcd4bd3e584f62098068a669122adf39f6c6fd28",
      "02_NEGATIVE_GRAPH_COMPLEMENT_59_SOURCE_PRESERVED.json": "8023c7e7d1067f64b40dcea01647e9166af53e91d9a1603e2bbc9e04987e03bf",
      "03_THREE_LEDGER_EVENTS_DRAFT.json": "cc89fb339d068d31c8011fc623d5b4fc4bf5da6083ad1fc06f1228dd3953327a",
      "04_SIX_CLOCK_SCHEMA_DRAFT.json": "df3b788b265c6418b40e512ba2e05cb381d9e81fe675b7e183211a58927bfee9",
      "05_FORMAL_CROSSWALK_COUNTS_AND_PROVENANCE.json": "14136669797992d9c2fe069b4656780525e18f83a2aca6b0f8c99938656cdce1",
      "06_DETERMINISTIC_TEST_PLAN_UNEXECUTED.json": "fedd90a0e940cc4e454fcddb8949fb60a2b45d96b746a55808eb1e72a374b703",
      "07_OWNER_DECISIONS_FOR_CONTROLLED_DISPOSITION.json": "9239eeb9317ef2e1327b2635a8bd32fb93370c2de068dbf49af451bdc9e0f955",
      "12_PROPOSED_EXT_AND_WDA_CONTROLLED_SOURCE_ALIGNMENT_NOT_ADOPTED.md": "e79d78a55ebc696b9f5ac3bd6a2ea87cd37e957dc4c3751f75536fd8ed4fbef1"
      }
    },
    "d03_v3_design_pinned_in_package": {"file": "War_Rig_V3_D03_Order_Lifecycle_Protection_Sizing_Design_Proposal_V3.md", "sha256": "88975c34282f4f611b8d3bcad2c4598c16bf6465316b8d54caa55b3f09646661"},
    "d04_v2_design_pinned_in_package": {"file": "War_Rig_V3_D04_Signals_Models_Pricing_Data_Quality_Design_Proposal_V2.md", "sha256": "5e2ef530f8e50520959d79aa736f758d7256607ab772e8b08f5b1fa7bae41934"}
  },
  "fixed_by_reference_via_pinned_master_section_1_1": {
    "note": "Hashes are listed in the pinned master V1.8 section 1.1 table (D01, D02, D05, D06 and RG-01..RG-07 response ZIPs) and the V2 snapshot archive and instrument_map tables; bytes are held by the owner, not copied here.",
    "master_sha256": "dce9968ec3645cd03b786409c86eeb513826df9b6d14b340533973b7c08aafdd"
  },
  "baseline_counts": {
    "module_rows": 18,
    "StageD_owner_questions": 14,
    "ATC_owner_questions": 4,
    "master_owner_questions": 43,
    "combined_owner_register": 61,
    "freeze_findings": 13,
    "repairs": 21
  },
  "nonbinding": true,
  "source_files_modified": false,
  "reviewer_assigned": false,
  "cooling_off_started": false
}

```


---

## PACKAGE MEMBER 17_EXT_AND_ORIGINAL_UNIT_CROSSWALK.csv

```csv

source_unit,source_file,source_status,mapped_module_row_in_02,mapped_component_in_01,disposition_in_this_grant,test_family,note
unit 01,effective_policy.py,original G1-R unit,EffectivePolicyResolver,"03, 13",ADMITTED,"TC-CONF, TC-ISOLATION",extended by EXT-01
unit 02,intent_identity.py,original G1-R unit,IntentLedger & SingleWriter,10,ADMITTED,"TC-ENGINE, TC-STATE",
unit 03,state_ledger.py,original G1-R unit,IntentLedger & SingleWriter,10,ADMITTED,TC-STATE,"seven axes, 42 edges"
unit 04,audit_events.py,original G1-R unit,AuditCustody & Dashboard; IndependentWatchdog & AlertProof,"10, 11",ADMITTED,TC-AUDIT,
unit 05,control_latches.py,original G1-R unit,StopBreakerControls,10,ADMITTED,TC-STATE,
unit 06,calendar_completion.py,original G1-R unit,SourceSnapshotLoader,01,ADMITTED,TC-DATA,
unit 07,synthetic_observer.py,original G1-R unit,AccountBoundBrokerObserver,"07, 09",ADMITTED (simulated observer only),"TC-SIM, TC-RECON",no live IG read
unit 08,capability_guard.py + tests/offline,original G1-R unit,EffectivePolicyResolver + OfflineBrokerSimulator + audit,13,ADMITTED,TC-ISOLATION,extended by EXT-02
EXT-01,instrument_definition.py,EXT-G0R-14 section 5.2 ADD,EffectivePolicyResolver,"instrument layer (under 01, 03, 04, 13)",ADMITTED,TC-INSTR,V3EXT-001..003
EXT-02,plugin_manifest.py,EXT-G0R-14 section 5.2 ADD,EffectivePolicyResolver + audit (capability guard),instrument layer; 13,ADMITTED,"TC-INSTR, TC-ISOLATION","V3EXT-004, -005"
EXT-03,macro_features.py,EXT-G0R-14 section 5.2 ADD,SourceSnapshotLoader,01,ADMITTED,TC-DATA,as-of / vintage; late publication denies
EXT-04,strategy_evaluator.py,EXT-G0R-14 section 5.2 ADD,EntryEligibilityEngine,"03, 04",ADMITTED (pure evaluation; no model loader),"TC-CONF, TC-STRAT",emits candidates; replaces CandidatePublisher
EXT-05,risk_math.py,EXT-G0R-14 section 5.2 ADD,ExposureRiskLedger,05,ADMITTED,TC-RISK,pure synthetic equations
EXT-06,synthetic_backtester.py + fixture_policy_loader.py + offline_scenario_runner.py,EXT-G0R-14 section 5.2 ADD,ComparisonEvaluator; OfflineBrokerSimulator,"07, 12, 13",ADMITTED,"TC-COMP, TC-SIM",FIXTURE_ONLY signed-domain policy loader
EXT-07,offline_candidate_store.py,EXT-G0R-14 section 5.2 EXCLUDED/RESERVED,CandidatePublisher,none,EXCLUDED_RESERVED,TC-ISOLATION,G1R-08-C stays negative
EXT-08,offline_reconciler.py,EXT-G0R-14 section 5.2 ADD,ConfirmationReconciler,09,ADMITTED,TC-RECON,
EXT-09,audit_projection.py,EXT-G0R-14 section 5.2 ADD,AuditCustody & Dashboard,11,ADMITTED (read-only projection),TC-AUDIT,no control route
EXT-10,data_intake_schema.py,EXT-G0R-14 section 5.2 ADD,SourceSnapshotLoader; ComparisonEvaluator,"01, 12",ADMITTED (schema and mock validation only),"TC-DATA, TC-COMP",real ingestion is a separate authorisation
EXT-11,offline_eligibility.py + supervision_admission_validator.py,EXT-G0R-14 section 5.2 ADD,EntryEligibilityEngine; IndependentWatchdog & AlertProof,"04, 10",ADMITTED,"TC-STRAT, TC-AUDIT",WDA-08 section 4 nine-predicate fixture validator
EXT-12,synthetic_fill_model.py,EXT-G0R-14 section 5.2 ADD,OfflineBrokerSimulator,07,ADMITTED,TC-SIM,never broker proof
EXT-13,contract_listing_registry.py,EXT-G0R-14 section 5.2 ADD,EffectivePolicyResolver,instrument layer,ADMITTED,TC-INSTR,"V3EXT-003, -010"

```


---

## PACKAGE MEMBER 18_REGISTER_DISPOSITION_CLASSES.csv

```csv

item_id,item_kind,disposition_class,plain_words_class_meaning,location_or_gate_and_test_id
OC-D02-01,MASTER_BINDING_ITEM,C_CARRY_PRIOR_DECISION,Earlier proposal or owner evidence carried unchanged as a candidate; independent authenticity and binding status still require proof.,
OC-D02-02,MASTER_BINDING_ITEM,C_CARRY_PRIOR_DECISION,Earlier proposal or owner evidence carried unchanged as a candidate; independent authenticity and binding status still require proof.,
OC-D02-03,MASTER_BINDING_ITEM,C_CARRY_PRIOR_DECISION,Earlier proposal or owner evidence carried unchanged as a candidate; independent authenticity and binding status still require proof.,
OC-D03-06,MASTER_BINDING_ITEM,C_CARRY_PRIOR_DECISION,Earlier proposal or owner evidence carried unchanged as a candidate; independent authenticity and binding status still require proof.,
OC-D06-05,MASTER_BINDING_ITEM,C_CARRY_PRIOR_DECISION,Earlier proposal or owner evidence carried unchanged as a candidate; independent authenticity and binding status still require proof.,
OC-D06-10,MASTER_BINDING_ITEM,C_CARRY_PRIOR_DECISION,Earlier proposal or owner evidence carried unchanged as a candidate; independent authenticity and binding status still require proof.,
OC-D02-04,MASTER_BINDING_ITEM,K_KEEP_OFF_UNTIL_LATER_GATE,"Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",
OC-D03-02,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D03-03,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D03-04,MASTER_BINDING_ITEM,K_KEEP_OFF_UNTIL_LATER_GATE,"Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",
OC-D03-07,MASTER_BINDING_ITEM,K_KEEP_OFF_UNTIL_LATER_GATE,"Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",
OC-D04-02,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D05-02,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D06-08,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D03-01,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D03-08,MASTER_BINDING_ITEM,K_KEEP_OFF_UNTIL_LATER_GATE,"Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",
OC-D04-06,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D04-07,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D05-05,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D05-08,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D06-04,MASTER_BINDING_ITEM,K_KEEP_OFF_UNTIL_LATER_GATE,"Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",
OC-D03-05,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D05-01,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D05-03,MASTER_BINDING_ITEM,K_KEEP_OFF_UNTIL_LATER_GATE,"Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",
OC-D05-04,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D05-06,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D05-07,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D05-09,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D04-01,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D04-03,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D04-04,MASTER_BINDING_ITEM,K_KEEP_OFF_UNTIL_LATER_GATE,"Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",
OC-D04-05,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D04-08,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D06-06,MASTER_BINDING_ITEM,K_KEEP_OFF_UNTIL_LATER_GATE,"Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",
OC-D06-01,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D06-02,MASTER_BINDING_ITEM,K_KEEP_OFF_UNTIL_LATER_GATE,"Stays switched off. The offline simulator may use a labelled test value; the real value is chosen by the owner at G2, G3 or G4. Nothing here allows a real trade.",
OC-D06-03,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D06-07,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D04-09,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D05-10,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D06-09,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D06-11,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
OC-D06-12,MASTER_BINDING_ITEM,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,Proposed rule is to be implemented and tested against simulator only after G1 grant; not yet built or passed.,
D03-FREEZE-01,FREEZE_FINDING,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",01 §State contracts and 08 TC-STATE; authority remains OPEN; test NOT_RUN
D03-FREEZE-02,FREEZE_FINDING,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",01 §State contracts; 03 §Broker protocol; 08 TC-STATE/TC-RECON; test NOT_RUN
D03-FREEZE-03,FREEZE_FINDING,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",01 component 08; 03 protection readback; 08 TC-ATC; test NOT_RUN
D03-FREEZE-04,FREEZE_FINDING,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",03 account-bound identity; 08 TC-RECON; test NOT_RUN
D03-FREEZE-05,FREEZE_FINDING,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",01 component 06 market-entry only; 08 TC-ENGINE; test NOT_RUN
D03-FREEZE-06,FREEZE_FINDING,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",01 §State contracts; 08 TC-STATE; detailed D03 plan included; test NOT_RUN
D04-FREEZE-01,FREEZE_FINDING,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",G3 model option B owner decision OC-D04-04; DENY: G1R-08-M; V3EXT-021
D04-FREEZE-02,FREEZE_FINDING,D_DESIGN_ADOPTED_FOR_OFFLINE_CORE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",File 24 MS-B gates G-1 to G-11 and MSB-01..MSB-19; DENY: G1R-08-M narrowed by AM-10 to one module; V3EXT-015; V3EXT-021; real-artifact registration and MS-F are later and separate
D06-FREEZE-01,FREEZE_FINDING,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",G1 implement canonical deny enum; TC-ISOLATION; DENY unknown enum
D06-FREEZE-02,FREEZE_FINDING,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",G1 actual admission test; TC-STATE/TC-WATCH; DENY unknown supervision
D06-FREEZE-03,FREEZE_FINDING,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",SOURCE_PINS_UNMODIFIED/MASTER_V1_8_CORRECTED_UNCHANGED.md §D06 provenance; check by reviewer
D06-NOTE-01,FREEZE_FINDING,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",G1 detailed negative tests; Stage D03 06 plan; DENY: TC-STATE and TC-ISOLATION
D06-NOTE-02,FREEZE_FINDING,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",11 and 15 responder role UNASSIGNED; default no real broker capability; TC-ISOLATION
R-01,REPAIR,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",G1 evidence crosswalk completion; TC-STATE/TC-CONF; DENY numeric source mismatch
R-02,REPAIR,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",04 source correction register; reviewer to confirm OC-D04-06 exact link
R-03,REPAIR,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",04 source correction register; D06/TC-COMP noninterference link
R-04,REPAIR,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",G1 D01 negative cases in master and Stage D03 plan; TC-ISOLATION; DENY absent cases
R-05,REPAIR,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",G1 D05 stress cases; TC-RISK; DENY missing stress oracle
R-06,REPAIR,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",03 one-attempt pre-wire evidence; TC-ENGINE/TC-RECON; test NOT_RUN
R-07,REPAIR,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",SOURCE_PINS_UNMODIFIED master unchanged; documentary attribution review pending
R-08,REPAIR,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",SOURCE_PINS_UNMODIFIED Group1 record exact hash; documentary filename review pending
R-09,REPAIR,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",G1 clock schemas only; numerical values G3; DENY: TC-WATCH when UNSET
R-10,REPAIR,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",05 43 master entries; semantic class crosswalk 18; owner/reviewer OPEN
R-11,REPAIR,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",G1 source archival hash; 16 provenance; DENY unpinned Group C data
R-12,REPAIR,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",05 owner selections; class mapping 18; reviewer validation still OPEN
R-13,REPAIR,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",SOURCE_PINS_UNMODIFIED archived V1/V2 records source lineage; reviewer validation still OPEN
R-14,REPAIR,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",11 and 15 no broker emergency role; TC-ISOLATION
R-15,REPAIR,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",00 scope R+C exact named proposal; 04 amendment schedule
R-16,REPAIR,CLOSED_IN_DESIGN_TEXT,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",05 StageD register and 10 separate G4; reviewer still to verify provenance
R-17,REPAIR,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",Before final presentation source pins and owner custody; DENY absent hash evidence
R-18,REPAIR,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",G1 V2 frozen snapshot path evidence; TC-ISOLATION denies host/V2 reads
R-19,REPAIR,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",G0R provenance reconciliation to A39 and 43-row master; owner selection still OPEN
R-20,REPAIR,IG_ONLY_EXCLUDED,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",G3 real broker oracle/certification only; G1 deny IG: TC-ISOLATION
R-21,REPAIR,CARRIED_TO_LATER_GATE,"PROPOSED classification only; NOT owner-accepted, finding remains formally OPEN.",Before final owner acceptance each row meaning and tag validated; DENY unresolved approval

```


---

## PACKAGE MEMBER 19_GROUP1_INDEPENDENCE_APPLICABILITY_OWNER_ROUTE_NOT_SELECTED.md

# Group 1 independent-review/quorum applicability and CAR-01 — owner route NOT_SELECTED

**Primary controlling source:** `SOURCE_PINS_UNMODIFIED/GROUP1_PRINCIPLES_UNCHANGED.md`, principle 5 and named CAR-01 section, historically approved source hash `be6dad1f3247cf882a1912e91bc67c979e0f605d03ece1f3dcfb424d2d132e15`. The controlling text keeps independent reviewer/quorum standards, live-release/deployment two-person requirements and K1/H13 signatures/countersignatures; sole ownership by itself does **not** waive them. The original V32 clause-level acceptance document is not included here. Accordingly this table **cannot** establish which listed requirements are inapplicable to offline G0-R/G1-R. Missing original clause evidence is an explicit blocker, not a waiver.

| Existing control | Applicable to offline design/G1? | Evidence needed before final sitting | Disposition now |
|---|---|---|---|
| Independent architecture review and reviewer/quorum standard (V32) | UNKNOWN pending V32 source-clause crosswalk | Exact V32 clause, parties, conflict check, human review record and sign-off | OPEN; no AI self-certification |
| Independent WDA-08 and ATC-01 review | Presumed required under Group 1 and master, pending exact role crosswalk | Named independent reviewer(s), conflicts disclosure, scope, work product and actual attestation | OPEN; R2 is author, not independent reviewer of those items |
| K1 and H13 owner signatures / independent countersignatures | UNKNOWN for offline scope; no automatic exemption | Exact binding K1/H13 clauses, applicability decision, signatures or valid successor | OPEN |
| Live release signing and two-person deployment records | Explicitly LIVE-controlled; offline applicability unproven | Source clause stating stage and release type; live protections remain in force | OPEN for applicability; no LIVE permission |
| Witness, external-custody copy and independent fingerprint attestation | Required as design-fingerprint/custody proof under current Group 1 procedure, subject to exact accepted contract | Named custodian, external hash-verified copy, time, audit proof | NOT ATTESTED |
| CAR-01 controlled alternative | Not yet approved | Clause-by-clause replacement schedule, fingerprints, valid approval under standing rules | NOT_SELECTED |

**Exactly one owner route to resolve within this same group (do not choose for the owner):**

- **A — Existing humans:** appoint qualified real independent human reviewer/witness/countersigners sufficient for every *applicable* original control; provide clause crosswalk, signed proof and custody. A single witness does **not** automatically replace multiple mandated independent roles.
- **B — CAR-01 within this group:** independently evidence, reconcile and explicitly approve each proposed replacement and preserved control via the standing accepted route. The amendment cannot make itself effective retroactively or bypass the approval rules governing its own adoption.
- **C — Verified nonapplicability:** cite source-exact V32, K1, H13 and master clauses proving each supposedly nonapplicable rule truly does not cover offline design/G1. Merely calling it 'offline' or 'single-owner' is insufficient.

**Selection:** `UNSELECTED`. **Real reviewer(s):** `UNAPPOINTED`. **Witness/countersign:** `UNASSIGNED`. **External custody:** `NOT_ATTESTED`. **V32 source bytes/crosswalk:** `NOT_ATTACHED`. This table documents a gate within one stage, not a new design-review stage.


---

## PACKAGE MEMBER 20_CONTROLLED_SOURCE_SUPERSESSION_PROPOSAL_NOT_ADOPTED.md

# One controlled source-supersession proposal — NOT ADOPTED

**Controlling form.** The exact old and new text of each amendment is in `23_CONTROLLED_AMENDMENT_EXACT_TEXT.csv` (AM-01..AM-14). This table only explains the purpose of each change and the test boundary; if it differs from file 23, file 23 controls. Where a row below has no matching AM entry, the pinned text is unchanged and the row only states how this package reads it.

**Purpose.** To resolve secondary finding F-01 and R2's B2/B3/B6 within a single consolidated owner signing; this is a source-level *candidate*, not an effective amendment. No source in `SOURCE_PINS_UNMODIFIED` has been changed, and no implementation may rely on this proposal until controlled acceptance against an exact fingerprint.

| Source/controlled location | Historical rule (retained for provenance) | Proposed superseding offline-only rule | Test/negative authority boundary |
|---|---|---|---|
| Master V1.8 §0 and §3.1A | Restricted original eight-unit, nine-excluded G1-R slice; expansion needs separate grant | On explicit **Option R + EXT §1.1 Option C** selection, permit full 13-component, 18-module broker-neutral offline design *in this same final group*, except IG mutation gateway and named prohibited imports. Implement slices under one G1-R grant only after signature | TC-ISOLATION; 18-module schedule; no implicit authority from draft |
| EXT-G0R-14 §1.1/§1.2/§5.3/§7.1/§8.1 | Credential-free G1-R forbids real and simulated order/stop/close mutation and has import-deny tests | **Real IG/broker** order/stop/close, credentials, transport and sockets remain absent. Simulator-only order/fill/stop/close paths on signed fixtures explicitly allowed. All other non-broker rules and proof obligations preserved | V3EXT-070 revised to `NO_IG_IMPORT/NO_REAL_BROKER_MUTATION`; TC-SIM, TC-INIT, TC-ISOLATION |
| G1R-08-M / ModelArtifactRegistry | No trained-model/runtime registry import | Keep fitting, training, promotion and executable deserialisation denied; permit one intake module for owner-registered, non-executable trained models under MS-B (AM-10, AM-11); the signed test-score source stays as the registered pure strategy | G1R-08-M narrowed to one module; MSB-04, MSB-05, MSB-09, MSB-15; V3EXT-021 unchanged |
| G1R-08-C / CandidatePublisher, EXT-07 | Candidate publication import excluded | **Unchanged**—candidate evaluation through pure EXT-04, no publishing module or store | G1R-08-C, V3EXT-022 negative |
| G1R-08-Q / AnchorQuoteValidator | Broker/anchor quote module import excluded | Keep broker quote feed/anchor module denied; allow pure fixture bid/ask validator with no adapter import | G1R-08-Q, V3EXT-023 negative |
| OD-01 and Master module-to-scope table | Historical restricted offline schema/deny scope | Full simulated trading, risk, confidence, TP/SL, BE, adaptive trailing and reconciliation are *required* in offline G1-R; do not defer these core behaviours | 13-component table, 18-module map, TC-INIT and ATC-X tests |
| OD-06 / ATC-01 T11 / §5 | No protective broker mutation in restricted G0-R and no stop-modify import | IG protective mutations still disabled; `SIMULATOR_ONLY_TIGHTEN` supports a fixture-only local stop-modify/read-back pipeline; distinct from `LIVE_TIGHTEN_ONLY` (still DENIED) | TC-ATC, TC-INIT, static proof no IG import |
| Stage D03 42-edge graph / seven axes | Canonical draft axes and edges not activated | Pin exact D01 integrated design and D03 member bytes unchanged, map simulator operations to them without silently renaming axes | `STAGE_D03_REVIEW_BYTES/` pins, TC-STATE; 187 tests NOT_RUN |
| Group 1 principles 3/5, 27-Oct rule (a)/(b) | 48h grouped wait, review/quorum/countersignature safeguards retained | **No supersession proposed**. Prepare final group, independent verification, two forms in one sitting after elapsed wait; CAR-01 applicability separately resolved | 10/11/19 governance records, clock NOT_STARTED |

**Adoption condition.** An owner `PREFER` or `MODIFY` on the consolidated register is only provisional until the final signed G0-R and G1-R records. The exact source amendments must be independently reconciled and approved by fingerprint in that group. Any scope, text, evidence or SHA change after the final evidence presentation restarts the indivisible 48h clock. If the model intake remains excluded, it must be stated plainly that **offline G1-R exercises the complete trading pipeline on signed fixture scores, not V2's trained model outputs**; future trained-model intake needs a separate controlled grant. None of these conditions is satisfied by writing this file.


---

## PACKAGE MEMBER 21_MERGED_REVIEW_FINDING_DISPOSITION.md

# Consolidated R2 + secondary document-review finding disposition — candidate V2

**Review provenance:** R2 `R2_review_of_consolidated_offline_core_package_and_change_list_20261113.md` (AI, not human independent); the second document-level reviewer findings F-01..F-07 were supplied in the current conversation, are not signed human evidence, and did not recompute hashes or run tests. Neither review is final acceptance. Both are preserved as documentary findings; the wording below reports our corrective changes, **not** R2's own replay acceptance.

| R2 item | Second review | Treatment in this revision | Residual gate |
|---|---|---|---|
| B1 | F-05 | Stage D03 archive and nine pinned members (including D01 integrated technical spec and 187 detailed test specifications) attached byte-for-byte; D03 V3 and D04 V2 pinned | Independent recheck and source-closed owner selection |
| B2 | F-02 (part) | Configurable-instrument layer, second synthetic instrument `V3EXT-006`, 17 crosswalk and TC-INSTR added | Implement/test at G1; all NOT_RUN |
| B3 | F-01/F-02 | Explicit bans preserved for fitting, promotion, executable deserialisation and the candidate publisher; the trained-model loader is limited to one intake module under MS-B (file 24); pure bid/ask validator. Scope amendments given as exact old/new text in 23 (explained in 20) | Full offline trading with two prediction sources; real model registration separate and later; all five Core-5 trained models UNAVAILABLE; owner must approve source amendment |
| B4 | F-03 | Seven canonical state axes corrected to exact Stage D specification; source graph pinned | 42/84 alignment and tests NOT_RUN |
| B5 | F-06 | Actual 27 Oct grouped wait decision attached and hash-matched; clock metadata corrected to 48 *required*, 0 elapsed | No timer until final presentation, independent proof and frozen group |
| B6 | F-06 | Group 1 principle 5, CAR-01 and source applicability table added in 19 | OWNER CHOICE/CLAUSE CROSSWALK OPEN; cannot assume witness sufficient |
| B7 | F-06 (decisions) | 43 historical master classes + 13/21 proposed classes, comments and sources; all 61 remain NOT_SELECTED | Classes require independent semantic validation and owner choice, no implicit closure |
| C1 | F-07 | Pre-presentation choices provisional; elapsed time 0 while NOT_STARTED | Accepted group not presented |
| — | F-01 | Exact old and new text of fourteen amendments in file 23, each old text verbatim and unique in its pinned file (file 20 explains purpose only); original pinned sources immutable | MUST BE owner-approved against final fingerprints before effective scope |
| — | F-04 | Fill-to-initial-protection account/quantity/stop reconciliation contract and TC-INIT-01..10 | Tests NOT_RUN; no real broker proof |
| — | F-05 | Primary ledger spec and detailed 187 synthetic test specifications now included rather than hashes only | Required human/independent source review OPEN |

**No false completion:** all source amendments PROPOSED, 61 decisions OPEN, 13 freeze findings OPEN, 21 repairs OPEN, real human independence/custody/evidence pending, G0-R/G1-R unsigned, no cooling-off. This is a corrected **candidate**, not a freeze-ready final group.

## R2 mechanical replay of V2 and the residual fixes

R2 replayed V2 once (`REVIEW_EVIDENCE/R2_replay_of_V2_and_residual_fix_list_20261113.md`; AI, not human independent). Everything else in V2 passed. It found these residual items: exact old/new amendment text (now file 23, one controlling form), the EXT section 1.2 row in file 04, protection state names aligned to the pinned ledger specification, one precedence sentence over the Group 1 addendum's UNSET duration, package identifiers, and the review-evidence folder carrying the current checker. They are applied in this revision. The author's own run of `verify_v2_replay.py` is the check; no further R2 review round is part of the process.

## MS-B dual-source predictions (R2, 13 Nov 2026)

The owner chose option B (trained models with signed test scores). R2 read the owner's EC2 inventory: no Core-5 model file was found on the one inspected host, the V2 inference code that R2 holds fits a model on every run, and six other model files exist (file 25). The controlled amendment is AM-10..AM-14 in file 23, the contract and its 19 tests are file 24, and the evidence is file 25. The author's own run of `verify_msb.py` is the check; this is part of the same consolidated process, not a new design stage.


---

## PACKAGE MEMBER 22_PRIMARY_EVIDENCE_MOUNT_AND_CONTENT_SHA256.md

# Primary evidence and status audit (added during the merged correction round)

- The original source package SHA is `dac6eb6e377923fe6043d4b583b63d08bdc25f3b4002e4e0c1705dbb09c4c8a7`.
- `SOURCE_PINS_UNMODIFIED/War_Rig_V3_StageD03_Bounded_Mechanical_Residual_Fixes_20261113.zip` is attached as a byte-identical archival copy, SHA-256 `23bdbe3b7d0d34b8b1d19fd78daf9990b7ea89b506634da7d4953cea9ef67ead`.
- Nine extracted `STAGE_D03_REVIEW_BYTES` members are individually hash-verified to the immutable R2 `required_pins.json`, including `00_STAGE_D01_INTEGRATED_TECHNICAL_SPECIFICATION.md` and `06_DETERMINISTIC_TEST_PLAN_UNEXECUTED.json` (the 187 test specification source).
- `SOURCE_PINS_UNMODIFIED/A39_GROUP1_COOLING_OFF_OWNER_DECISION_V2.json` SHA-256 `d3f39baa27d8a8c91050d19dea32d83883b73eb1ddb80cf4d89dcfbee534143b` contains owner rule (a) and (b) and 48h duration, *not* a running timer.
- `SOURCE_PINS_UNMODIFIED/War_Rig_V3_D03_Order_Lifecycle_Protection_Sizing_Design_Proposal_V3.md` SHA-256 `88975c34282f4f611b8d3bcad2c4598c16bf6465316b8d54caa55b3f09646661`.
- `SOURCE_PINS_UNMODIFIED/War_Rig_V3_D04_Signals_Models_Pricing_Data_Quality_Design_Proposal_V2.md` SHA-256 `5e2ef530f8e50520959d79aa736f758d7256607ab772e8b08f5b1fa7bae41934`.
- Actual independent human review, original V32 clause applicability, real G1-R environment evidence, owner selections and approval forms remain absent. Hash verification establishes byte identity **only**, not substantive acceptance.


---

## PACKAGE MEMBER 23_CONTROLLED_AMENDMENT_EXACT_TEXT.csv

```csv

amendment_id,pinned_file,exact_old_text,exact_new_text,takes_effect,negative_test_id
AM-01,EXT_G0R_14_UNCHANGED.md,"real market-data network acquisition, order/stop/close operations, external notifications","real market-data network acquisition, real-broker order/stop/close operations (simulated order, stop and close operations inside the OfflineBrokerSimulator are test-only and have no real transport, credential or network path), external notifications",only when the owner signs the G0-R record against the final group root,"V3EXT-024, V3EXT-025, TC-ISOLATION"
AM-02,EXT_G0R_14_UNCHANGED.md,no stop-modification import or real permit; explicit signed fixture policies only,no real-broker or IG stop-modification import or real permit; a simulator-only stop modification is permitted solely in mode SIMULATOR_ONLY_TIGHTEN under explicit signed fixture policies,only when the owner signs the G0-R record against the final group root,V3EXT-070 (amended oracle)
AM-03,EXT_G0R_14_UNCHANGED.md,"**Five distinct state axes:** `broker_operation`, `working_order`, `position`, `protection`, `realised_result`.","**Seven distinct state axes:** the five Annex G axes `broker_operation`, `working_order`, `position`, `protection`, `realised_result` plus `intent_lifecycle` and `attempt_send_eligibility` (master V1.8 section 3.3, Stage D01 specification section 3).",only when the owner signs the G0-R record against the final group root,TC-STATE
AM-04,ATC_01_REV2_UNCHANGED.md,"`OFF`, `COMPUTE_AND_LOG_ONLY`, `LIVE_TIGHTEN_ONLY`.","`OFF`, `COMPUTE_AND_LOG_ONLY`, `SIMULATOR_ONLY_TIGHTEN`, `LIVE_TIGHTEN_ONLY` (unavailable in this grant).",only when the owner signs the G0-R record against the final group root,TC-ATC
AM-05,MASTER_V1_8_CORRECTED_UNCHANGED.md,"no broker endpoint reachable, no trade, no fitting or policy activation;","no broker endpoint reachable, no real trade (simulated trades against the OfflineBrokerSimulator are permitted), no model fitting, no policy activation;",only when the owner signs the G0-R record against the final group root,TC-ISOLATION
AM-06,MASTER_V1_8_CORRECTED_UNCHANGED.md,### 3.1A Complete module-to-first-slice mapping and test-oracle plan (PROPOSED),"### 3.1A Complete module-to-first-slice mapping and test-oracle plan (REPLACED for Scope C by file 02 of the consolidated package, 18 rows; the 16-row table that follows is superseded)",only when the owner signs the G0-R record against the final group root,TC-ISOLATION
AM-07,OD14_03_REVIEW_UNCHANGED.md,"For restricted offline scope, keep every V3 protective broker action disabled: automatic stop repair, stop tightening or trailing, close and cancel.","For this offline scope, keep every real-broker V3 protective action disabled: automatic stop repair, stop tightening or trailing, close and cancel against IG. Simulated stop tightening, trailing, close and cancel against the OfflineBrokerSimulator are permitted as test-only under mode SIMULATOR_ONLY_TIGHTEN and signed fixture policies.",only when the owner signs the G0-R record against the final group root,"TC-ATC, TC-ISOLATION"
AM-08,OD14_03_REVIEW_UNCHANGED.md,V3 stop tightening or trailing stays disabled until separately decided,real-broker V3 stop tightening or trailing stays disabled until separately decided (simulated tightening and trailing are in scope),only when the owner signs the G0-R record against the final group root,TC-ATC
AM-09,OD14_03_REVIEW_UNCHANGED.md,"Offline V3 cannot send orders, so these cannot run here; `adaptive_protection_required` stays `UNSELECTED` and V3EXT-070 denies.","Offline V3 sends no real orders; these run here against the OfflineBrokerSimulator under signed fixture policies, with stop modification in mode SIMULATOR_ONLY_TIGHTEN; `adaptive_protection_required` stays `UNSELECTED` for any real broker and V3EXT-070 denies every real-broker path.",only when the owner signs the G0-R record against the final group root,"TC-ATC, V3EXT-070"
AM-10,EXT_G0R_14_UNCHANGED.md,**Keep rejection of actual registry/fit/runtime**; allow only hash field/type and registered pure strategy with **no** model loader | `V3EXT-021` confirms permitted pure strategy cannot import a loader; original M remains negative,"**Keep rejection of any fit, training, calibration fitting, promotion, activation for live use, just-in-time training, executable deserialisation (pickle, joblib, dill, cloudpickle, marshal, shelve, numpy allow_pickle) and any model registry or loader import anywhere except the single module `v3/offline/model_intake.py`**; that module may read only the allow-listed non-executable artifact formats of consolidated file 24, and only for an owner-registered artifact that passes every MS-B gate; allow also the hash field/type and the registered pure strategy (the signed test-score source), which still has **no** model loader | `V3EXT-021` still confirms the pure strategy cannot import a loader; MSB-04, MSB-05, MSB-09 and MSB-15 of file 24 are the negative oracles for the loader, and original M remains negative for every other module",only when the owner signs the G0-R record against the final group root,"MSB-04, MSB-05, MSB-09, MSB-15, V3EXT-021"
AM-11,EXT_G0R_14_UNCHANGED.md,Model/runtime registry import rejected | `UNCHANGED_NEGATIVE` | No ModelArtifactRegistry loader/runtime import; pure strategy interface only; V3EXT-021 |,Model/runtime registry import rejected | `NARROWED_BY_AM-10` | No model registry or loader import in any module except `v3/offline/model_intake.py`; no fit or runtime registry anywhere; pure strategy interface only; V3EXT-021 unchanged |,only when the owner signs the G0-R record against the final group root,MSB-15
AM-12,EXT_G0R_14_UNCHANGED.md,"no V2 bytes, live DB mounts or production cohort reads in G1-R |","no V2 bytes (the one exception is an owner-registered converted model artifact admitted under MS-B, file 24: it is data, it enters only through the model-intake route, and it is never an archive member, V2 code or a V2 DB read), live DB mounts or production cohort reads in G1-R |",only when the owner signs the G0-R record against the final group root,"MSB-05, V3EXT-025, V3EXT-027"
AM-13,MASTER_V1_8_CORRECTED_UNCHANGED.md,"**EXCLUDED from G1-R runtime and mocks.** Only a hash field/type in `effective_policy.py` is in scope, not an artifact loader or model registry implementation; later scope grant required.","**Controlled dual-source predictions only (MS-B, consolidated file 24).** In G1-R this module returns a `SignalScore` either from a signed test-score set or, through the single module `v3/offline/model_intake.py`, from an owner-registered, immutable, non-executable trained-model artifact; there is no fitting, no promotion, no runtime registry, no pickle or joblib. This is the later scope grant this row anticipated. Registered artifacts are not group members.",only when the owner signs the G0-R record against the final group root,"MSB-01, MSB-12"
AM-14,EXT_G0R_14_UNCHANGED.md,", model fitting or model activation. All external network egress denied",", model fitting, or any model promotion or activation for live use (offline serving of an owner-registered artifact under MS-B, consolidated file 24, is neither). All external network egress denied",only when the owner signs the G0-R record against the final group root,"MSB-09, V3EXT-015"

```


---

## PACKAGE MEMBER 24_MSB_CONTROLLED_DUAL_SOURCE_PREDICTIONS_CONTRACT.md

# MS-B — CONTROLLED_DUAL_SOURCE_PREDICTIONS / NO_REFIT (PROPOSED, NOT SELECTED, NOT APPLIED)

**Status:** proposal text for the owner sitting. Nothing here is adopted until the owner signs the G0-R record against the final group root. It selects no model cadence, authorises no fitting and approves no model. The exact source amendments it needs are AM-10..AM-14 in `23_CONTROLLED_AMENDMENT_EXACT_TEXT.csv`; the evidence about the models that exist today is in `25_MODEL_ARTIFACT_EVIDENCE_EC2_20261113.csv`.

## 1. In plain words

- V3 has **two ways to produce a prediction, and both are built from the start**: (1) **signed test scores**, fixed and fingerprinted numbers that prove the machinery (sizing, TP/SL, trailing, simulated trades) works; (2) **actual trained models**, finished model files that the owner has registered and that V3 may only read.
- Both feed **one prediction contract** (`SignalScore`, section 4). Every prediction and every simulated trade says which source it came from and carries that source's fingerprint.
- Test scores are never shown as model predictions and never used as evidence of trading performance.
- A trained model is usable only if the owner has registered it, its fingerprint matches, its format cannot run code when opened, and every gate in section 9 passes. If a gate fails, or no model exists, that instrument gets **no prediction**. V3 never quietly switches to test scores, to an older file or to a freshly trained model.
- No registered, frozen Core-5 model was found. The owner's inventory (one host; `/home/ubuntu`, `/opt`, `/srv`) found no Core-5 model file, and V2's code trains its main signal model again on every run and throws it away (section 13). So at presentation all five Core-5 models are recorded **UNAVAILABLE** for offline serving. That is a serving classification, not proof that no model exists anywhere; S3 and other hosts were not inventoried. Making one is a fitting action; this selection does not authorise it, and it is done outside V3 (section 12).
- The contract and its 19 tests are fixed in the group. Real models are registered afterwards, one at a time, under the frozen contract. They are not group members and do not restart the 48-hour clock.

## 2. What MS-B authorises, exactly

- **M1.** Source A, `SIGNED_TEST_SCORE`: a signed, hash-registered, deterministic test-score set (a pure scoring function registered in the EXT section 2.3 plug-in manifest, or a score table inside a signed fixture snapshot). It reads no model file and no network.
- **M2.** Source B, `TRAINED_MODEL`: one module, `v3/offline/model_intake.py`, verifies and evaluates owner-registered artifacts. It is registered in the same plug-in manifest; manifest capabilities restrict and never enable.
- **M3.** Both sources return the same `SignalScore` record to the strategy evaluator `EXT-04` (which keeps no loader) and on to the OfflineBrokerSimulator. Both are part of the initial offline implementation.
- **M4.** The input to either source is a signed feature row produced from the signed snapshots of `SourceSnapshotLoader` (file 02, row 1). Whether a snapshot may be real historical market data is decided by that row and by EXT section 4.1. MS-B does not grant it.

## 3. What MS-B does not authorise

- **N1.** Fitting, re-fitting, calibration fitting, just-in-time training or any other training, anywhere in G1-R or V3. (The A0.10 proposal `A010-ARCH-D017-v22` has a just-in-time mode and a machine authoriser; neither is borrowed.)
- **N2.** Promotion, or activation for live use. `promoted_for_live` must be false on every registered artifact. The serving state in section 8 means "may drive the offline simulator" and nothing more.
- **N3.** Any IG, broker, network or credential path (EXT section 1.2, AM-01).
- **N4.** Any V2 code, V2 database or V2 live-cohort read. `G1R-08-X` stays absolute. V3EXT-025 changes only for converted model data (AM-12). V3EXT-027 is unchanged because a model artifact is data, not source.
- **N5.** Selection of a model cadence. `OC-D04-04` stays `DEFER`. D04 option B (controlled re-fitting) stays unselected. With no refit allowed, the offline build behaves like a retained-frozen model; that is not a selection of option A as the live policy.
- **N6.** Pickle, joblib, dill, cloudpickle, marshal, shelve, `numpy.load` with `allow_pickle`, or any format that runs code when opened, anywhere in G1-R.
- **N7.** Any new route for V2 history. V2 recorded signals and outcomes enter only as the immutable, quarantined, independently pinned V2 snapshot that `ComparisonEvaluator` already admits (file 02, TC-COMP). A replay from V2 recorded signals can compare trailing behaviour without loading a model; it cannot prove trained-model inference parity.

## 4. The common prediction contract (`SignalScore`)

Every `SignalScore` carries these fields, whichever source produced it.

- **S-1** `source_kind`: `SIGNED_TEST_SCORE` or `TRAINED_MODEL`. It is set by the source module, never by the caller. The run manifest declares which source each instrument uses in that run, and the declaration cannot change mid-run.
- **S-2** `source_fingerprint`: the sha256 of the signed test-score set, or of the registered model manifest.
- **S-3** Feature lineage: `feature_row_sha256`, the source snapshot id and hash, and the bar range. For `TRAINED_MODEL` also the feature-schema hash.
- **S-4** `evidence_class`: `PIPELINE_VALIDATION_ONLY` for `SIGNED_TEST_SCORE`; `OFFLINE_MODEL_BEHAVIOUR` for `TRAINED_MODEL`. Neither is live trading-performance evidence (EXT section 4.1).
- **S-5** Direction, raw score, calibrated probability, confidence grade, policy hash and run-manifest hash, as the strategy evaluator already requires.
- **S-6** Every simulated order, position, trade outcome and audit event carries the `prediction_id`, so its source and fingerprint can be read back.
- **S-7** Reports are grouped by `source_kind` and never pooled. Any figure from a `SIGNED_TEST_SCORE` run is stamped `NOT_PERFORMANCE_EVIDENCE` and `NOT_A_MODEL_PREDICTION`. Any figure from a `TRAINED_MODEL` run is stamped `OFFLINE_SIMULATED_MODEL_BEHAVIOUR`, and its report says in words that it shows offline historical or simulated model behaviour and is not verified forward or live trading performance. No offline figure is relabelled as forward or live evidence. A forward-demo evidence class is not created here, because no forward path exists in this scope.
- **S-8** No cross-substitution. A `TRAINED_MODEL` source that fails a gate or has no authorised artifact returns `NO_AUTHORITATIVE_PREDICTION` and is never replaced by a test score, a latest or previous model, or a refit. A `SIGNED_TEST_SCORE` prediction can never carry a model label.

## 5. Signed test-score rules (source A)

- **F-1** The set is registered by hash in the plug-in manifest or sits in a signed fixture snapshot whose hash is checked at load.
- **F-2** Same input, same bytes out.
- **F-3** It opens no model file and no network; it cannot be mistaken for a model by its record (S-1, S-4).
- **F-4** A tampered, unsigned or unregistered test-score set returns `NOT_PROVEN`.

## 6. Allowed model artifact formats (allow-list; anything else is rejected before it is parsed)

| Code | Artifact | Allowed form | Notes |
|---|---|---|---|
| AF-1 | Model | XGBoost native JSON, `gbtree` booster only | objective limited to `binary:logistic` or `reg:squarederror`; any other objective is a contract change |
| AF-2 | Scaler | JSON of named numeric arrays | method `ROBUST` or `STANDARD`; columns listed |
| AF-3 | Calibration | JSON of numeric parameters | method `PLATT` or `ISOTONIC_STEP`; or `NONE_DECLARED` |
| AF-4 | Feature schema | JSON list of ordered column names, dtypes and the missing-value rule | its hash is in the manifest |
| AF-5 | Manifest | JSON, fields of section 7 | its hash is the registered identity of the set |

The evaluator is a pure in-repo tree-ensemble evaluator using the standard-library `json` module with strict parsing (non-finite constants rejected). No `xgboost`, `sklearn`, `joblib` or `pickle` package is imported anywhere in G1-R, so no fit implementation is even present in the process.

## 7. Model manifest fields (all required; `UNKNOWN` may be recorded but yields NOT_PROVEN)

`model_set_id`; `instrument_scope` (Gold, GER40, US500, EURUSD, GBPUSD, or `NONE_NOT_CORE5`); `role` (`SIGNAL_SCORE`, `EXECUTION_FILTER_SKIP`, `EXECUTION_FILTER_R`, `SHADOW_ONLY`); `objective`; `files` (name, format code, sha256, bytes); `feature_schema_sha256`; `scaler_sha256` or `NONE_DECLARED`; `calibration_sha256` or `NONE_DECLARED`; `calibration_required`; `training_snapshot_sha256_and_bar_range`; `fit_procedure_code_sha256`; `producer_environment_identity`; `conversion_record_sha256`; `state`; `promoted_for_live`; `authorisation` (owner signature reference, scope `OFFLINE_SIMULATOR_ONLY`, finite `valid_until`, runtime profile); `registered_utc`.

The conversion record holds the source artifact's sha256 before and after conversion, the converter's code hash, the golden-vector reference hash, the number of golden vectors and the registered parity tolerance. The tolerance is a recorded parameter, UNSET in this contract. Zero is not assumed, because float32 accumulation may differ between the original library and the in-repo evaluator. A conversion record with no registered, justified tolerance cannot reach `VALIDATED`, so that set can never become serving.

## 8. Model states

`CREATED_UNREGISTERED` -> `REGISTERED_IMMUTABLE` -> `VALIDATED` -> `SERVING_AUTHORIZED_OFFLINE_ONLY`; also `SERVING_SUSPENDED`, `REVOKED`, `RETIRED`. The names follow the A0.10 OQ-006 proposal (SHA-256 `1b397d2f…5abb`, R2 copy V22), which is itself `PROPOSED_PENDING_REVIEW`; no authority is claimed from it. Each transition is an owner-signed record. There is no machine authoriser in G1-R.

## 9. Model gates at load (all must pass; any failure returns `NO_AUTHORITATIVE_PREDICTION` and no new entry)

- **G-1** the manifest hash equals the registered manifest hash.
- **G-2** every listed file exists and its sha256 equals the manifest; no unlisted file is in the artifact directory; no directory scanning.
- **G-3** every file is one of AF-1..AF-5 and parses as strict JSON.
- **G-4** the input row equals the feature schema: names, order, dtypes, count.
- **G-5** a declared-required calibration artifact is present with the declared hash.
- **G-6** `instrument_scope` and `role` equal the request.
- **G-7** state is `SERVING_AUTHORIZED_OFFLINE_ONLY` and `valid_until` has not passed on the run clock declared in the run manifest.
- **G-8** `promoted_for_live` is false.
- **G-9** the runtime profile equals the registered profile.
- **G-10** the output is finite and inside its declared domain; it is never clipped or repaired.
- **G-11** identical input and identical artifact give byte-identical output.

## 10. Conversion and registration happen outside G1-R

- **C-1** An existing `.pkl` or `.joblib` file is converted once, in a separate trusted, isolated environment that is not G1-R and not V3: no network, read-only source mount, owner-produced files only, source sha256 recorded before and after.
- **C-2** Opening a pickle or joblib file runs code. That is acceptable only in that environment and only for a file the owner produced, whose hash was recorded in an earlier inventory. It is never done inside V3.
- **C-3** The converter is a recorded, hashed tool. It writes only AF-1..AF-5 files and a parity record on golden vectors. The golden vectors cover the whole inference path in one pass, from the raw signed feature row through feature ordering and the missing-value rule, the scaler, tree traversal and the calibration to the final probability, and are compared with the original library's output for the same rows. A parity check of the tree output alone is not enough.
- **C-4** The set then enters G1-R through the EXT section 7.1 intake quarantine: hash match, format scan, no nested or hidden members, no traversal or symlink, canary scan.
- **C-5** The owner registers the set by signing its manifest hash.

## 11. Registration after the freeze

As in EXT section 3, where new dated listings do not change the family digest (V3EXT-003, V3EXT-032), a registered artifact is separate from the contract. The contract, the 19 tests, a signed test-score set and a synthetic test model are in the group. Each real registration is a separate signed record carrying its own conversion, parity and quarantine evidence. It does not change the contract digest or the group root. A registration that needs a new format, objective or gate is a contract change and restarts the group clock by rule (b).

## 12. Making a model (fit-and-freeze) is not MS-B

Producing a new model, including a one-time freeze of a Core-5 model, is a fitting action. EXT section 4.1 requires a separately named, fingerprinted, credential-free research/data authorisation that specifies input manifests, quarantine, model-fit permissions, outputs, retention, no network and exact negative tests. Call it **MS-F**. MS-F is not selected, not in this package, and not performed inside G1-R or V3. A model it produces is registered through sections 10 and 11 like any other.

## 13. Status at presentation and the evidence behind it

| Instrument or file set | Role | Status at presentation |
|---|---|---|
| Gold | SIGNAL_SCORE | TRAINED_MODEL source UNAVAILABLE: no registered frozen artifact identified in the inspected locations |
| GER40 | SIGNAL_SCORE | TRAINED_MODEL source UNAVAILABLE: no registered frozen artifact identified in the inspected locations |
| US500 | SIGNAL_SCORE | TRAINED_MODEL source UNAVAILABLE: no registered frozen artifact identified in the inspected locations |
| EURUSD | SIGNAL_SCORE | TRAINED_MODEL source UNAVAILABLE: no registered frozen artifact identified in the inspected locations |
| GBPUSD | SIGNAL_SCORE | TRAINED_MODEL source UNAVAILABLE: no registered frozen artifact identified in the inspected locations |
| Two Signal ML V2 `model.joblib` sets, 18 May 2026 | not Core-5 | CREATED_UNREGISTERED; `promoted_for_live` NOT_VERIFIED_BY_R2 (E6); role to be taken from each set's own training manifest at registration |
| Four execution-filter `.pkl` files, 4 and 15 May 2026 | not Core-5 | CREATED_UNREGISTERED |

The `SIGNED_TEST_SCORE` source is available for all five instruments from the first offline build. `UNAVAILABLE` is a serving-authorisation status, not a finding that no model exists anywhere: a Core-5 source becomes eligible only when an artifact passes sections 9 to 11. The sha256, size and date of each model file are in file 25, copied from the owner's inventory output of 13 Nov 2026 (host `ip-172-31-5-61`, 16:27:41Z).

- **E1** The inventory found no Core-5 model file under `/home/ubuntu`, `/opt` or `/srv`. Absence there does not prove absence everywhere; S3 and other hosts were not inventoried.
- **E2** `backtest_ml/live_inference.py`, function `_live_prob` (defined at line 107; the classifier is built at line 138 and fitted at line 144) in the three V2 copies held by R2 (SHA-256 `8a298149c23ec23cd2dee63349834bd09e7e59c13bd533fb39a5e126795e4601`), builds a `RobustScaler` and an `XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=42)`, calls `fit` on all history, reads one `predict_proba` and keeps nothing. Its docstring says "Train on all available history and predict today."
- **E3** The owner's crontab runs `backtest_ml.live_inference` nine times each weekday.
- **E4** The hash of the live-folder file is `PENDING_OWNER_CHECK`. The inventory's code search was capped at 300 lines and did not reach the live folder, so E2 is shown for the copies only.
- **E5** D04-04 (pinned) says per-run transient training without a retained artifact is not eligible to claim reproducibility; Master V1.8 section 8 (a design-proposal table, not a live-host attestation) lists "V2 inference re-fits each call without permanent model hash" with "prior audit reported; code pin needed". E2 to E4 are that code pin once E4 is supplied.
- **E6** Not verified by R2: the contents of the Signal ML V2 training manifests and metrics, including any `promoted_for_live` flag stated in the author's note of 13 Nov, and any models held in S3 (`infrastructure/lambda`, `download_models_to_tmp`). None of these open items is a permission: an artifact whose manifest, provenance or location is unverified stays `CREATED_UNREGISTERED` and is not served.

## 14. Tests (design specifications; none has been run)

| ID | Case | Required result | Anchors |
|---|---|---|---|
| MSB-01 | Synthetic registered model set, evaluated twice on the same signed feature row | score produced; both runs byte-identical; artifact and score hashes in the `SignalScore` | G-1 to G-11 |
| MSB-02 | One byte of any model artifact file flipped after registration | NO_AUTHORITATIVE_PREDICTION; no entry; audit event names the file | G-2 |
| MSB-03 | An unlisted extra file in the artifact directory; a listed file missing | NO_AUTHORITATIVE_PREDICTION for the set | G-2 |
| MSB-04 | A pickle or joblib file with a correct hash; a file with an allowed extension but non-JSON content | rejected before any parse; never deserialised; canary side effect absent | G-3; G1R-08-M |
| MSB-05 | Static scan of the whole build for pickle, joblib, dill, cloudpickle, marshal, shelve, xgboost, sklearn, `allow_pickle` and any fit or train symbol | zero hits; the only model reader is `v3/offline/model_intake.py` using stdlib json | G1R-08-M; V3EXT-025 |
| MSB-06 | Input row with wrong order, a missing column, an extra column, a wrong dtype | NO_AUTHORITATIVE_PREDICTION | G-4 |
| MSB-07 | Calibration declared required but absent or with another hash | NO_AUTHORITATIVE_PREDICTION | G-5 |
| MSB-08 | Wrong instrument or role; expired authorisation; state other than serving; `promoted_for_live` not false; different runtime profile | NO_AUTHORITATIVE_PREDICTION in each of the five cases | G-6 to G-9 |
| MSB-09 | Any run-time call to a fit, train, refit or calibrate entry point, including a hostile plug-in | denied and audited; no score from the call; no fallback | EXT 1.2 as amended (AM-14); V3EXT-015 |
| MSB-10 | Output is NaN, infinite or outside its declared domain | NO_AUTHORITATIVE_PREDICTION; value not repaired | G-10 |
| MSB-11 | Converted synthetic set (a) whose golden-vector outputs differ from the reference by more than the registered tolerance; (b) whose conversion record has no registered, justified tolerance; (c) whose golden vectors cover only the tree output and not the full path | in each case does not reach VALIDATED and cannot become serving | section 7; C-3 |
| MSB-12 | A run declares `TRAINED_MODEL` for an instrument with no authorised artifact (each of the five at presentation) | `NO_AUTHORITATIVE_PREDICTION`; no eligible new entry; not converted into a test-score run | S-8 |
| MSB-13 | Re-scoring the same source event after a model rerun or reload | no second intent; same canonical intent identity | TC-MODEL; D04-04 |
| MSB-14 | Registration of a real artifact under the frozen contract | contract digest and group root unchanged; separate signed record; a registration needing a new format or gate is refused as a contract change | section 11 |
| MSB-15 | Import graph of the strategy artifact EXT-04 and of every module except `model_intake.py` | V3EXT-021 still passes; any other module importing the model reader fails the build | AM-10; V3EXT-021 |
| MSB-16 | Run both sources; follow every order, position, outcome and audit event back | each carries a `prediction_id` that resolves to `source_kind`, `source_fingerprint` and feature lineage; none is missing | S-1 to S-3, S-6 |
| MSB-17 | Produce the run report from a mixed run | results grouped by `source_kind`, never pooled; every `SIGNED_TEST_SCORE` figure stamped `NOT_PERFORMANCE_EVIDENCE` and `NOT_A_MODEL_PREDICTION`; every `TRAINED_MODEL` figure stamped `OFFLINE_SIMULATED_MODEL_BEHAVIOUR` with the words "not verified forward or live trading performance" | S-4, S-7 |
| MSB-18 | A model gate fails mid-run; the run tries to continue with a test score; a test-score prediction is given a model label; the declared source is changed mid-run | all refused and audited; no substitution in either direction | S-1, S-8 |
| MSB-19 | Tampered, unsigned or unregistered test-score set; the same input run twice | `NOT_PROVEN` for the tampered set; identical bytes for the valid set | F-1 to F-4 |

## 15. Owner selections for the sitting (listed once)

1. Accept MS-B (dual-source predictions, no refit) exactly as written here, with AM-10..AM-14, file 25 and tests MSB-01..MSB-19 (yes/no).
2. Confirm that `OC-D04-04` stays `DEFER`, so no model cadence is selected (yes/no).
3. Note that any fit-and-freeze (MS-F) is a separate later authorisation and is not decided at this sitting.


---

## PACKAGE MEMBER 25_MODEL_ARTIFACT_EVIDENCE_EC2_20261113.csv

```csv

artifact_id,item_kind,instrument_scope,path_on_ec2,sha256,bytes,modified_utc,format,state_at_presentation,promoted_for_live,evidence_source,notes
EC2-M-01,MODEL_FILE,NONE_NOT_CORE5,/home/ubuntu/tradingview_webhook/models/execution_r_model.pkl,e314b9c4032e1a7a3f1c3e7b4b8bdf6255909de51cc98e89fba8f8011b138088,255721,2026-05-04T09:06:52Z,pickle,CREATED_UNREGISTERED,NOT_VERIFIED_BY_R2,"owner inventory output 13 Nov 2026 16:27:41Z, host ip-172-31-5-61, section A","execution filter, R regressor, first generation; conversion needed before any use"
EC2-M-02,MODEL_FILE,NONE_NOT_CORE5,/home/ubuntu/tradingview_webhook/models/execution_r_model_proxy_v1.pkl,5de29eb99bb643146a1e8bd5d2ef1ec411dcbb17c588e79f0ce17b63d6372b7a,268834,2026-05-15T21:22:25Z,pickle,CREATED_UNREGISTERED,NOT_VERIFIED_BY_R2,"owner inventory output 13 Nov 2026 16:27:41Z, host ip-172-31-5-61, section A","execution filter, R regressor, proxy_v1"
EC2-M-03,MODEL_FILE,NONE_NOT_CORE5,/home/ubuntu/tradingview_webhook/models/execution_skip_model.pkl,fac25191a6c7e0d598db64b6a3a6226c2831b719c4d48589989d9c531982e6e8,263774,2026-05-04T09:06:52Z,pickle,CREATED_UNREGISTERED,NOT_VERIFIED_BY_R2,"owner inventory output 13 Nov 2026 16:27:41Z, host ip-172-31-5-61, section A","execution filter, skip classifier, first generation"
EC2-M-04,MODEL_FILE,NONE_NOT_CORE5,/home/ubuntu/tradingview_webhook/models/execution_skip_model_proxy_v1.pkl,1d9a16b54eae6672ba2e4af324a5cd552fcc3f129fd3a3776e563eeb50bf0fab,267950,2026-05-15T21:22:25Z,pickle,CREATED_UNREGISTERED,NOT_VERIFIED_BY_R2,"owner inventory output 13 Nov 2026 16:27:41Z, host ip-172-31-5-61, section A","execution filter, skip classifier, proxy_v1"
EC2-M-05,MODEL_FILE,NONE_NOT_CORE5,/home/ubuntu/tradingview_webhook/results/ml/signal_v2/models/signal_v2_20260518T125341Z/model.joblib,aa6f695098f54f0e0558abbd945ca1550feca9abbb38f14d47ebd45cc6bf0c52,514467,2026-05-18T12:53:44Z,joblib,CREATED_UNREGISTERED,NOT_VERIFIED_BY_R2,"owner inventory output 13 Nov 2026 16:27:41Z, host ip-172-31-5-61, section A","Signal ML V2; same folder holds feature_columns.json (547 bytes), training_manifest.json (2558) and metrics.json (2367), not hashed in the inventory"
EC2-M-06,MODEL_FILE,NONE_NOT_CORE5,/home/ubuntu/tradingview_webhook/results/ml/signal_v2/models/signal_v2_20260518T131620Z/model.joblib,539f289e5d55d3d40bcf3ea6b9e9ee8640be5f3a51dd16acc9a29607130ed853,514492,2026-05-18T13:16:24Z,joblib,CREATED_UNREGISTERED,NOT_VERIFIED_BY_R2,"owner inventory output 13 Nov 2026 16:27:41Z, host ip-172-31-5-61, section A",Signal ML V2; created 23 minutes after EC2-M-05; same companion file sizes
EC2-R-01,RECORD_NOT_ARTIFACT,NONE_NOT_CORE5,/home/ubuntu/tradingview_webhook/results/dax_hourly/model_version.json,89014f0c838b8f26aeb6e9d5b13eefe691f657ca6b8891bc47f2d2612e05808f,868,2026-04-26T09:21:41Z,json,NOT_A_MODEL,NOT_APPLICABLE,"owner inventory output 13 Nov 2026 16:27:41Z, host ip-172-31-5-61, section A",named by the inventory pattern; contents not reviewed by R2
EC2-R-02,RECORD_NOT_ARTIFACT,NONE_NOT_CORE5,/home/ubuntu/tradingview_webhook/results/execution_model_metrics.json,093c49fef39d5b0a761907a017f4deac32836aa4130df177012c4b47576189f7,1795,2026-05-04T09:06:52Z,json,NOT_A_MODEL,NOT_APPLICABLE,"owner inventory output 13 Nov 2026 16:27:41Z, host ip-172-31-5-61, section A",named by the inventory pattern; contents not reviewed by R2
CORE5-01,REQUIRED_MODEL_SET,Gold,NONE_FOUND,NONE,0,NONE,NONE,UNAVAILABLE,NOT_APPLICABLE,"owner inventory section A and live_inference.py (file 24 section 11, E1 to E4)","no registered frozen artifact identified in the inspected locations; V2 fits a new model on every run; a one-time freeze is MS-F, not MS-B"
CORE5-02,REQUIRED_MODEL_SET,GER40,NONE_FOUND,NONE,0,NONE,NONE,UNAVAILABLE,NOT_APPLICABLE,"owner inventory section A and live_inference.py (file 24 section 11, E1 to E4)","no registered frozen artifact identified in the inspected locations; V2 fits a new model on every run; a one-time freeze is MS-F, not MS-B"
CORE5-03,REQUIRED_MODEL_SET,US500,NONE_FOUND,NONE,0,NONE,NONE,UNAVAILABLE,NOT_APPLICABLE,"owner inventory section A and live_inference.py (file 24 section 11, E1 to E4)","no registered frozen artifact identified in the inspected locations; V2 fits a new model on every run; a one-time freeze is MS-F, not MS-B"
CORE5-04,REQUIRED_MODEL_SET,EURUSD,NONE_FOUND,NONE,0,NONE,NONE,UNAVAILABLE,NOT_APPLICABLE,"owner inventory section A and live_inference.py (file 24 section 11, E1 to E4)","no registered frozen artifact identified in the inspected locations; V2 fits a new model on every run; a one-time freeze is MS-F, not MS-B"
CORE5-05,REQUIRED_MODEL_SET,GBPUSD,NONE_FOUND,NONE,0,NONE,NONE,UNAVAILABLE,NOT_APPLICABLE,"owner inventory section A and live_inference.py (file 24 section 11, E1 to E4)","no registered frozen artifact identified in the inspected locations; V2 fits a new model on every run; a one-time freeze is MS-F, not MS-B"

```


---

## Package provenance (outer ZIP)

Original V3 package SHA-256: `0e71d874dfc7d1bd26b20f3721e7995a4ec8e509cd77662e3bf861e81e8ecf00`.
R2 MS-B revision 3 evidence: see `REVIEW_EVIDENCE/` for the source amendments, corrected files, reference outputs, and review notes.

V5 MS-B review candidate ZIP SHA-256: `3d6632a2d662deade05b957ad822edd9af6e8eda8c1d7ebca3f098e122760796`.

The final archive contains 69 manifest entries plus the manifest itself. Locally, the V5 structural checker passes 71/71 checks. This does not establish live-host code parity, the training manifests, software/runtime tests, authorised model serving, independent human acceptance or any start of cooling-off.
