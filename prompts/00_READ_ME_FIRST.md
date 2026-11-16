# War Rig V3 — Two-Agent IDE Prompt Handoff (16 November 2026)

This bundle supplies **two separate launch instructions**, the unchanged full controlling prompts REV4 (macro research) and R3 (offline implementation), the earlier original R2-concurred prompt required for **historical hash verification only**, and both owner-provided research hypotheses.

**This is NOT a new V3 technical design version.** The original master R3 remains marked `R2_REVIEW_OF_DELTA_PENDING`; any future R2 assessment should review this variant and the implementation, not claim it is byte-identical to the old R2-concurred master. Neither agent gains IG, broker, DEMO, LIVE, EC2 or model-fitting authority. The V5 ZIP and one-file owner design are **already in the owner's** `design/` directory and are deliberately not duplicated here.

## Install into the existing project

Unzip the contents directly into `~/IdeaProjects/war_rig/` preserving paths. This places:

- `prompts/00_AGENT1_LAUNCH_CORE5_MACRO_REV4.md` — paste its complete text into **Agent 1**.
- `prompts/War_Rig_V2_CORE5_MACRO_VERIFICATION_IDE_PROMPT_REV4_20261116.md` — Agent 1's full controlling prompt; do not replace by the launcher.
- `prompts/00_AGENT2_LAUNCH_V3_OFFLINE_R3.md` — paste its complete text into **Agent 2**.
- `prompts/War_Rig_V3_OWNER_DIRECTED_OFFLINE_START_MASTER_IDE_PROMPT_R3_20261116.md` — Agent 2's full controlling implementation prompt; do not execute the old one.
- `prompts/01_SINGLE_IDE_IMPLEMENTATION_PROMPT_R2_AUTHORITY_CONCURRED.md` — **historical reference only**; R3 requires its presence and hash.
- `reference/hypotheses/Core5_Macro_Driver_Table_20261116.md` and `reference/hypotheses/Cross-Asset_Macro_Correlation_Dashboard_1.pdf` — research hypotheses, not policy.

Keep these files byte-for-byte intact; verify the included hashes in `SHA256SUMS.txt`. If a path already exists with **different contents**, stop and compare it before overwriting. A direct `unzip -n` preserves existing files but you must then verify hashes; do not silently keep an older revision.

## Two-agent Git isolation

- Agent 2: the current `~/IdeaProjects/war_rig/` checkout on the implementation branch.
- Agent 1: a separate worktree e.g. `~/IdeaProjects/war_rig_macro_research` on branch `research/core5-macro`. **Only after the V3 repository has its first commit**, an operator may run `git -C ~/IdeaProjects/war_rig worktree add -b research/core5-macro ~/IdeaProjects/war_rig_macro_research HEAD`. If the branch already exists, choose a different branch or reuse its worktree; do not reset or force overwrite.
- Both checkouts need their own copies of the **non-secret** supplied prompt and hypothesis reference files, plus owner-prepared, redacted, hash-pinned V2 reference inputs. Git worktree does not automatically share files that are ignored/untracked. Provision reference files explicitly, not by linking to or reading the active V2 repository.
- Agent 1 produces `evidence/macro/` results and a research commit/manifest. **Owner reviews and merges** that branch before Agent 2 consumes the result. Agent 2 must continue independent foundation work while research is in progress.

## Optional reference inputs still needed for actual V2 parity/history

These are **not included** because they must be supplied separately by the owner and verified: redacted immutable `reference/v2_snapshot/` source copy, `reference/v2_outcomes/` trade exports, `reference/v2_predictions/` recorded signal exports, historical datasets, and a `reference/MANIFEST.sha256` for their files. Without them, the affected evidence is `NOT_VERIFIED` and must never be invented. The macro research can still inventory provided source and examine hypotheses; the implementation can build safe infrastructure independently.

## Real execution prerequisites

Agent 2's V3 test/runtime environment must be genuinely network-denied with pinned dependencies, as in R3 §1C; only the separate Agent 1 research job may use the narrowly allowed public data sources. Neither agent is allowed to use IG or mutate V2. V2 code is read as text only from the owner-provided redacted snapshot. Do not place secrets or private transaction data in public Git repositories.

**Run Agent 2's Stage A and Agent 1's macro research concurrently in separate worktrees once those workspaces are provisioned.** Separate code readiness, macro findings, outperformance evidence and future broker permissions as independent milestones.
