# Agent 2 — Core-5 macro research handover (18 Nov 2026)

The owner has merged the Core-5 macro research into `main` and recorded a decision:

- research evidence: `evidence/macro/MANIFEST.sha256`, SHA-256 `12ebf4559badf11714ff6af71eb1092537230ed699721fc3bda6b95bdb3a17ca` (research commit `2fdd7e3981d498ab7783bb81ac643eafe8abe998`);
- owner decision: `evidence/macro/OWNER_DECISION_20261117.md`.

## What to do

1. Merge `main` into your branch. Verify the manifest hash above. Record the manifest hash, the decision file's SHA-256 and the merge commit in `evidence/STAGE_STATE.json`, as R3 §1D item 3 requires. Use the evidence in `evidence/macro/` read-only; never copy it elsewhere.
2. Use `CORE5_MACRO_INVENTORY.csv`, `CORE5_MACRO_GAP.md` and the findings as the P0 V2 macro parity evidence, citing them in `evidence/V2_V3_CAPABILITY_PARITY.csv`. Record the `V2_PARITY` baseline as **comparison only**. Do not implement any V2 macro gate as active V3 behaviour.
3. Implement the adopted classifications as `COMPUTE_AND_LOG_ONLY`, inside the existing V5 design (EXT-03 `macro_features.py`, audit/ledger, dashboard):
   - EURUSD ex-EUR and GBPUSD ex-GBP USD-strength basket (WITH / AGAINST / NEUTRAL / UNKNOWN), with exactly the definitions in the research evidence;
   - event proximity for all five instruments.

   Every classification is computed point-in-time from completed, signed, fixture-supplied observations, and is attached to the signal's audit record before any outcome exists. Missing or stale inputs give `UNKNOWN`, never `NEUTRAL`.
4. Prove with tests, including mutation-style negative tests, that these classifications **cannot** change entry, direction, size, TP/SL, trailing, or any gate. Their only output is logged data. 100% line and branch coverage still applies.
5. Do not add anything else from the proposal. A separate replay backtest (Agent 1, REV5 addendum) is in progress. Its results may add more `COMPUTE_AND_LOG_ONLY` checks later, through an owner amendment; until then, build only the items above.

Report the merge commit, the `STAGE_STATE.json` entries, the files changed, the test results and coverage counters, and any blocker. Continue the R3 stages as before.
