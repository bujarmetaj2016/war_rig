# Stage B source scope

The complete V5 member `24_MSB_CONTROLLED_DUAL_SOURCE_PREDICTIONS_CONTRACT.md`
has been read, including M-1..4, S-1..8, F-1..4, AF-1..5, all required manifest
fields, states, G-1..11, C-1..5 and all 19 acceptance oracles. V5 members 02
and 17 were read for module ownership. D04-02..05 were read in the pinned
`SOURCE_PINS_UNMODIFIED/War_Rig_V3_D04_Signals_Models_Pricing_Data_Quality_Design_Proposal_V2.md`.
The D03-01 identity clause and later Stage-D03 B-02 clause were read to
exclude inference-run/model/policy/build changes from observation identity.
Stage A's already-read EXT-02/EXT-03 clauses remain governing architecture.
Exact per-requirement member/clause references are in `STAGE_B_REQUIREMENTS.csv`.
This is scoped reading, not a claim that the entire 69-member package is read.

R3 Stage B, sections 3/6 and the macro handover have been read. Macro research
is consumed in place, never copied. The 482-entry manifest was reverified in
full. Its SHA-256 remains
`12ebf4559badf11714ff6af71eb1092537230ed699721fc3bda6b95bdb3a17ca`;
owner decision SHA-256 remains
`fdbf1eae05af2307afe0f2bcc18bb16c370c1e5f8936a9748170a3a4a92c9d4a`.

The exact basket definition is REV4 Part 4, lines 74-92: equal weights;
invert EURUSD/GBPUSD/AUDUSD returns; exclude the traded counter-currency;
10-return sums and 250-observation sample standard deviation; strict
`S > sigma/2` / `S < -sigma/2`; side-relative WITH/AGAINST. Sample `ddof=1`
is verified by text-only `research/part4_engine.py:562-595,662-698`,
SHA-256 `ed146b003704170ef90bc2ef01fcc9a030fd24f917aec8793aa7960e87ad0d6d`.
No research code is imported by V3. The proposal and final trade report
were read for prior-UTC-day vintages, unknown handling and the distinction
between a positive pre-entry event match and proof of no event.
Event times must be strictly after entry and at most 24 hours ahead.
NO_EVENT additionally needs all five pre-entry, fresh schedule coverage
intervals; incomplete/date-only/late evidence never establishes absence.
Only the two baskets and five-instrument event telemetry are adopted.

V2 was read as text only:

| File and clause | SHA-256 | Scope |
|---|---|---|
| `reference/v2_snapshot/backtest_ml/audit_entry.py:62-67` | `84e774c10ae043f425c65055bc9f91f6db4d70ec077c7f42b7a72c441fb2241e` | A/B/C/D thresholds 0.60/0.45/0.30; fixture/reference only |
| `reference/v2_snapshot/backtest_ml/live_inference.py:478-521` | `8a298149c23ec23cd2dee63349834bd09e7e59c13bd533fb39a5e126795e4601` | Gold probability-only; FX/equity climate/size-label exceptions; comparison only |

The same pinned `live_inference.py:107-150` was also read as text: `_live_prob`
constructs the scaler/classifier, calls fit/fit_transform at line 144, predicts
and retains no frozen artifact in this function. This confirms MS-B section 13
E2 for the supplied copy only, not a live-host inventory or global absence proof.

## B1 evidence limits

The reader proof is a hand-authored three-node numeric XGBoost-2.0.3-shaped
JSON tree, not training, conversion, original-library parity or owner model
registration. Full-path expected values and their derivations are signed
constants outside the evaluator. It never reaches VALIDATED or SERVING.
The development fixture signer is explicitly NOT the owner signature.
All real Core-5 TRAINED_MODEL sources remain unavailable and deny without
fallback. No real calibration, monetary authority or model eligibility is claimed.

Both source results use the common SignalScore. It represents fixture/read-only
pipeline evidence, not an entry permit. The bounded tiers are signed synthetic
parameters, not financial risk grants. PredictionReference is a typed later-stage
contract, not proof that orders/positions/outcomes or the durable ledger exist.
Macro observations are immutable, pre-outcome attachments and cannot affect the
current prediction/cap path. Actual C/E/F entry, sizing, TP/SL, trailing, ledger
and dashboard integration still requires its own no-effect gates in those stages.

Accepted A5 fixtures and A6 evidence are untouched. The A5 evidence helper now
hashes the exact original ten-file source closure (actual bytes, not old assumed
hashes); B1's independent manifest pins the full current source/dependency closure.
This preserves historical registrations without signing over new code or hiding
new modules from whole-build coverage/import checks.

## B2 integration scope

The new `fixtures/stage_a/b2_prediction/` namespace contains independent signed
snapshot/feature/manifest/artifact packets, intake policies and run declarations.
The historical `stage_a` prefix is required by the accepted bounded filesystem
loader; no accepted Stage A fixture was replaced. Model JSON is transported as
exact signed text through that loader, never discovered or executed. Both
source paths pass through the same dispatcher and confidence contract. Invalid
model packet authentication enters a correlated denial audit, never a fallback.
Five Core-5 runs explicitly declare unavailable models with a null fingerprint;
no fictitious artifact hash stands in for missing evidence.

The pure synthetic numeric profile rejects nonzero magnitudes below `1e-30`
or above `1e30` before arithmetic, and rejects boolean numeric metadata.
Calibration explicitly declares the same side as the model. Date-only event
times cannot prove NO_EVENT; absent macro series, timestamps, schedules and
calendars remain UNKNOWN. Duplicate schedule records are rejected even if an
earlier record was unverified. These are bounded synthetic-reader mechanics,
not an approved production-model numerical domain.

`tools/check_stage_b_predictions.py` replays actual signed filesystem intake:
five model denials, two separately labelled score-fixture predictions and one
synthetic reader prediction, with immutable pre-outcome macro attachments.
The evidence checker launches two independent processes and compares canonical
bytes. V2 mappings are separate comparison-only observations, including Gold,
FX and equity exceptions; they confer neither calibration nor sizing authority.

## B3 completion boundary

The current full-build signed fixtures are in a separate `b3_prediction`
namespace because the authenticated signed-score provider changed the build
fingerprint. The B2 namespace and gate remain immutable historical evidence.
Both signature failures and model-file failures now have common correlated
denial witnesses. The static scan also rejects training symbols and
`allow_pickle`, not only direct fitting calls.

All 19 Stage-B decomposition rows have explicit member/clause/runtime/test
mappings. Fourteen MS-B mechanical oracles have executed final dispositions.
MSB-08,13,14,15,16 remain globally partial: synthetic scope is not real serving,
canonical intent is not a durable intent ledger, no real registration occurred,
EXT-04 does not exist until C, and actual downstream order/position/outcome
lineage awaits D/F. These limits are preserved in global traceability and stage
state, not hidden behind the scoped Stage B PASS.
