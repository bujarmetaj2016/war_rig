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
