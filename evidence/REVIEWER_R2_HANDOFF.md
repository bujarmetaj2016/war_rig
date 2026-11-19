# R2 checkpoint handoff - Stage A complete, full scope unfinished

Stage A foundations pass at the enclosing A6 checkpoint. This is not
READY_FOR_R2_REVIEW for the full R3 deliverable, independent human governance
attestation, release readiness, model approval or trading/broker authority.

| Slice | Commit | Executed tests | Statements | Branch destinations |
|---|---|---:|---:|---:|
| A1 signed identity and clock | `83a4e05` | 77 | 175/175 | 70/70 |
| A2 calendar/completed data | `b63d882` | 152 | 363/363 | 110/110 |
| Amendment 1 exact source gate | `d24d2de` | Four amended checks PASS | Metadata only | Metadata only |
| A3 typed context and tiers | `65e6cc3` | 200 | 569/569 | 162/162 |
| A4 filesystem intake | `3b0b2f3` | 256 | 668/668 | 196/196 |
| A5 family/plug-in/listing registration | `1593a68` | 431 | 956/956 | 268/268 |
| A6 final source-clause traceability | Enclosing checkpoint | 431 | 956/956 | 268/268 |

Locate the exact A6 commit with
`git log -1 --format=%H -- evidence/stage_a/a6/GATE.json`.
The source-base commit in each gate is explicitly not a fabricated
self-referential commit ID; exact runtime source hashes bind the executed code.

Reproduce from the repository root with **`sh tools/run_offline.sh` only**.
Restore the separately supplied `reference/` and `wheelhouse/` inputs first.
The command uses the exact pinned image, offline hash-enforced installation,
six actual hostile egress probes before V3 imports, the whole suite, exact
coverage counters, Ruff/strict mypy, source/import isolation, 19 killed mutants,
two-process deterministic replay, six-profile registration and both
source-count and Stage A traceability gates. No private signing key is needed
to verify the committed fixtures. Never run V3 code/tests on the host.

The current 27-row member/clause/runtime/test/evidence mapping is
`stage_a/STAGE_A_COMPLETION.csv`. Its pre-A2 reading snapshot remains at
`stage_a/STAGE_A_REQUIREMENTS.csv`. The 627-row global trace has three completed
own-ID oracles, 19 partial and 605 unimplemented: 624 final dispositions
remain pending. None is silently labelled an approval blocker or tested pass.
The exact 59/25 aggregate fields, 84 IDs, 38 guarded/84 denied pairs and
ID/pair bijection pass under owner Amendment 1; all 84 NEG rows cite it.

Review the strict definition fields, immutable input-to-family/listing-to-output
graph, exact plug-in source/dependency/build hashes, signed no-follow filesystem
bounds and negative tests in `test_instrument_registration.py`. Challenge the
sixth-profile witness in `stage_a/a6/registration.json`: all runtime and
plug-in-manifest bytes stay unchanged. These are generic fixture schema
profiles, not completed Core-5 strategy implementations. Registration is
serialized process-local schema state, not the later durable operational
ledger, a broker certificate, a research approval or a DEMO/LIVE transition.
Unselected real policies still grant nothing.

Stages B-G, whole-package reading, trained-model intake, strategies, risk,
execution, durable ledger/audit, promotion lifecycles, comparison and adopted
compute-and-log-only macro integration remain unfinished. The scoped Stage A
source-reading record is not a claim that every V5 member was read in full.
Past A1-A5 and source-conflict bundles remain unchanged.

## Historical A1-A2 handoff (superseded; retained for review history)

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

### Historical source-count hard gate after A2

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
