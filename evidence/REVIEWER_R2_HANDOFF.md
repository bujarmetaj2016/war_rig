# R2 checkpoint handoff - Stage A / A1-A2 only

Current source-count gate: **PASS under owner Amendment 1 (`9cd873d`)**.
The four exact checks pass, the 627 unique IDs are unchanged, and all 84 NEG rows
cite the amendment and mechanical re-derivation. No per-ID source classification
is inferred. `stage_a/amendment_1/checks.json` supersedes the historical source
conflict described below; the old executed exit-two bundle remains immutable.

Status: PARTIAL_IMPLEMENTATION_REVIEWABLE, not READY_FOR_R2_REVIEW for the full
R3 deliverable. No independent review, formal governance attestation, software
release readiness or trading authority is asserted.

The unchanged historical blocked checkpoint is commit
`d6549b612b8415ecaa7101bf6e80b7061018199c`. The source checkpoint and evidence
hashes are recorded in `STAGE_STATE.json`, `stage_a/a1/` and `stage_a/a2/`.

Reproduce using **only** `sh tools/run_offline.sh` at the repository root,
with the owner-provided `reference/` inputs and `wheelhouse/` restored.
It uses the exact pinned image, installs offline with hash verification, and
runs actual egress denial before V3 imports. Never execute V3 tests on the host.
The development private key is not needed to verify the committed fixtures or
run the suite; the public trust anchor is committed. A fresh run does not
overwrite committed checkpoint evidence.

Review priorities:

1. `v3/offline/fixture_policy_loader.py`: domain-separated signature and pinned
   key boundary, payload hashing, strict schema, limits before decoding,
   duplicate/nonfinite handling, UTC validity and explicit typed denials.
2. `v3/offline/calendar_completion.py`: no wall-clock authority, UTC-only
   instants, immutable nondecreasing replay, signed synthetic event-clock domain/
   skew proof and completed-bar/PIT/session checks. TZif bytes come from the signed
   pinned-image calendar fixture, not a host timezone lookup.
   `data_intake_schema.py` authenticates a closed synthetic snapshot schema;
   distinguish immutable lineage references from an actual computed feature row.
3. `tools/run_offline.sh` and `tools/offline_preflight.py`: exact image, absence
   of host credentials, reference read-only mount, install provenance and
   six actual egress probes. Build/evidence tooling is not included in the
   runtime coverage denominator.
4. `tests/v3/`, mutation/evidence checkers and `stage_a/a1/`: independently
   challenge the cumulative 363/363 statement and 110/110 branch counters and 12 killed
   safety mutants; distinguish fixture metadata extensibility from full
   instrument onboarding.

Complete slice scope, test failures fixed, explicit limitations, fixture schema
and remaining work are in `stage_a/a1/REPORT.md` and `stage_a/a2/REPORT.md`.
Each Stage A requirement has a V5 member/clause citation in
`stage_a/STAGE_A_REQUIREMENTS.csv`, read before A2. The full requirement universe,
all-stage traceability, risk/entry/trade lifecycle and adopted macro logging
remain unfinished; do not infer their completion from this handoff.

## Source-count hard gate after A2

A2's validated source/evidence commit is
`b63d8822bc137fa0434763edda26a2846a1d04f5`.
The follow-up checkpoint records `BLOCKED_SOURCE_CONFLICT`: D03 file02 has
84 distinct `$.negative_cases[*].negative_id` values (59 preserved plus
25 Master-derived), while R3 section 4 requires 59. The actual source IDs are
retained; no source or expected acceptance count is silently changed.
The 42 candidate IDs and rederived 38 guarded / 84 denied pairs do match.

`requirement_universe.csv`, `traceability.csv` and
`REQUIREMENT_UNIVERSE_REPORT.json` preserve extraction provenance and honest
pending mappings. No overall source-contract requirement is marked fully
implemented merely because A1-A2 primitives passed. Challenge the count
disposition independently before accepting traceability completion.
The current `sh tools/run_offline.sh` checks runtime first and then fails the
source-count gate explicitly; A2's enclosing historical commit reproduces its
passed runtime gate without claiming the later traceability failure passed.

The generated CSVs preserve quoted, multiline original source records, including
their original whitespace. Count parsed CSV records, not physical lines. The
checkpoint whitespace check excludes only `evidence/requirement_universe.csv`
and `evidence/traceability.csv` for that reason; code, tools and all other
evidence pass the normal check. Normalising original text merely to silence
that check would destroy the retained byte-faithful provenance.
