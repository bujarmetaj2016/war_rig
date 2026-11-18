# R3 blockers - 18 November 2026

## BLOCKED_ENVIRONMENT - Stage A execution

The checkout has no `requirements-dev.lock`, `wheelhouse/` or
`wheelhouse/SHA256SUMS`. There is no verified, hash-locked offline distribution
of pytest, pytest-cov, coverage, strict typing, lint/format and cryptography
with all transitive dependencies for the pinned runtime image.

R3 section 1C requires owner-run mirror preparation before sandbox execution,
using the same pinned Python image. No versions, package hashes or approval
have been invented. No networked installer or downloader was run. A local
Python 3.12.16 image supports successful preliminary no-egress checks, but
does not satisfy the missing dependency gate or establish approved interpreter
provenance. Do not execute V3 code/tests on the host as a workaround.

Resume: supply the complete locked mirror and its hashes, verify it in the
network-disabled container, install with
`pip install --no-index --find-links wheelhouse --require-hashes -r requirements-dev.lock`,
repeat the complete safety preflight, then begin Stage A. Fixtures must be
signed inside that sandbox before their runtime use. Stages A-G and the adopted
macro implementation, audit/dashboard integration and mutation-style tests
are not complete. Coverage is NOT_RUN, not 100% or a vacuous 0/0 pass.

## BLOCKED_SOURCE_INTEGRITY - historical macro reproduction only

The exact handover macro manifest hash matches. Of 482 filesystem entries,
412 verify and 70 cannot be read because their files are missing:
13 under `reference/history/macro-fred-next/` and 57 under
`reference/history/macro-schedules-retry/`. Exact paths are recorded in
`preflight/SOURCE_VERIFICATION_20261118.json`. Do not modify the research
manifest to conceal missing inputs, copy inputs from another worktree, or
redownload them without the separate authorised research process.

All 374 entries of `reference/MANIFEST.sha256` verify; the V2 snapshot,
prediction and outcome exports are present, not generically missing.
The inventory, gap, findings and proposal are also locally hash-verified.
Their source-trace facts can support a partial P0 inventory, but historical
research reproduction and performance claims remain unavailable.

## Uncompleted requirements, not invented policy choices

- No earlier `STAGE_STATE.json` or passed implementation checkpoint exists.
- The V5 archive is integrity-verified but full technical-contract reading,
  requirement-universe extraction and exact traceability mapping are pending.
- `V2_V3_CAPABILITY_PARITY.csv` contains only initial macro source-summary and
  adopted-classification rows. It is not the complete per-feature P0 inventory.
- Core-5 model eligibility, macro freshness policies, risk/session/model
  decisions and comparison-plan adoption have not been independently
  adjudicated in this checkpoint. No production serving artefact is registered.
- Only the owner's two USD-basket classifications and Core-5 event proximity
  are adopted, COMPUTE_AND_LOG_ONLY. No other proposal item, entry gate, size
  modifier or automatic promotion is adopted. V2_PARITY is comparison only.

The historical `preflight/BLOCKED_AUTHORITY.md` remains unchanged. Its old
procedural gate is superseded by R3 for internal offline development; missing
legacy signatures are not the current blocker.
