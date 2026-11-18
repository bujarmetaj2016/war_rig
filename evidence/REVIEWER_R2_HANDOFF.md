# R2 checkpoint handoff - Stage A / A1 only

Status: PARTIAL_IMPLEMENTATION_REVIEWABLE, not READY_FOR_R2_REVIEW for the full
R3 deliverable. No independent review, formal governance attestation, software
release readiness or trading authority is asserted.

The unchanged historical blocked checkpoint is commit
`d6549b612b8415ecaa7101bf6e80b7061018199c`. The source checkpoint and evidence
hashes are recorded in `STAGE_STATE.json` and `stage_a/a1/`.

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
   instants, immutable nondecreasing replay; this is not yet a completed-bar or
   session eligibility implementation.
3. `tools/run_offline.sh` and `tools/offline_preflight.py`: exact image, absence
   of host credentials, reference read-only mount, install provenance and
   six actual egress probes. Build/evidence tooling is not included in the
   runtime coverage denominator.
4. `tests/v3/`, mutation/evidence checkers and `stage_a/a1/`: independently
   challenge the 175/175 statement and 70/70 branch counters and eight killed
   safety mutants; distinguish fixture metadata extensibility from full
   instrument onboarding.

Complete slice scope, test failures fixed, explicit limitations, fixture schema
and remaining work are in `stage_a/a1/REPORT.md`. The full requirement universe,
all-stage traceability, risk/entry/trade lifecycle and adopted macro logging
remain unfinished; do not infer their completion from this handoff.
