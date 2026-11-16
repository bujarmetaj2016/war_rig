# IDE Agent 1 — Launch Core-5 macro verification (REV4)

You are **Agent 1 — Core-5 Macro Verification**, working on **READ-ONLY V2 RESEARCH**, not V3 runtime implementation. Your controlling task is the complete file:

`prompts/War_Rig_V2_CORE5_MACRO_VERIFICATION_IDE_PROMPT_REV4_20261116.md`

**Read the entire controlling prompt**, including the exact market, macro, timestamp and statistical rules. Do not substitute this launcher for it. Verify the exact file hash against `SHA256SUMS.txt` before proceeding. Do not run an older macro prompt.

## Input discovery

- Repository: independent `war_rig` V3 Git repository. Do your work in a **separate V3 branch/worktree** such as `research/core5-macro`; do not work in Agent 2's checkout. If not provisioned yet, report the missing worktree and provide commands, without modifying Agent 2's Git state.
- Read both supplied research hypotheses, **not as adopted trading policy**, from:
  - `reference/hypotheses/Core5_Macro_Driver_Table_20261116.md`
  - `reference/hypotheses/Cross-Asset_Macro_Correlation_Dashboard_1.pdf`
- The supplied V5 design ZIP in `design/` is the candidate reference for the comparison with EXT-G0R-14. Do not alter its bytes.
- V2 source evidence must come **only** from an owner-supplied, redacted, hash-pinned, **read-only copy** in `reference/v2_snapshot/`. Never enter the original V2 repository, EC2, IG, V2 runtime, credentials or databases. Do not import/execute V2 modules.
- The V2 trade/signal exports must come only from `reference/v2_outcomes/` and `reference/v2_predictions/` and pass recorded integrity checks. If missing, mark the dependent analysis `NOT_VERIFIED` and execute the independently possible work; do not invent evidence or access live sources.
- Public historical research download is only allowed in the isolated research job and from the allow-listed sources in REV4. It must not share a network-enabled execution environment with Agent 2's V3 build.

## Required behaviour

1. Verify and record hashes for the controlling prompt and both hypotheses; inventory source availability and report missing owner-provided evidence together.
2. Trace every Core-5 macro input from computation to its **last real V2 consumer**, distinguishing model feature, entry gate, actual stake multiplier, conflict arbitration, display and unused computation. Confirm or refute the EURUSD/GBPUSD USD-direction and climate-to-stake questions with source path/line/hash evidence.
3. Apply REV4's predefined price/yield calculations, as-of availability restrictions, defined side classifications, exploratory-versus-primary tags, weekly bootstrap and insufficient-sample thresholds **without changing rules after looking at trade results**.
4. Record source timestamps, vintages, close conventions, release calendar availability and unknown observations; do not use unpublished or future values.
5. Produce REV4's complete output set under `evidence/macro/`, plus its `MANIFEST.sha256`, analysis script, reproducible commands, test results, limitations, source hashes and final research commit. Treat all macro-gate recommendations as **proposals requiring explicit owner selection**, not executable V3 policy.
6. Provide Agent 2 a single verified macro-research branch/commit and manifest hash for review and merge. **Never merge into Agent 2's branch yourself while Agent 2 is coding.** Do not rewrite the historical V5 design.

**Start now:** inspect the referenced local files and existing independent V3 worktree. Report `READY_FOR_RESEARCH`, or a precise missing-input/blocker state. Run every safely independent research step without repeated clarification. Never infer evidence from filenames or invent V2 trades.
