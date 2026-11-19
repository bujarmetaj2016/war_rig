# R3 outstanding work - after Stage A / A2

## Resolved environment and source blockers

The original blocked checkpoint is preserved in commit
`d6549b612b8415ecaa7101bf6e80b7061018199c`. The owner subsequently supplied
the hash-locked mirror, pinned Python-image reference and all 70 missing macro
inputs. All 482 macro entries, 374 reference entries and 19 wheels now verify.
Installation inside the exact pinned network-none container succeeds and all
six active hostile egress probes are denied. These are no longer blockers.
See `stage_a/a1/preflight.json`, `install.txt` and `REPORT.md`.

No current input/environment failure prevents continuing independent Stage A
work. This does not make the entire Stage A or full implementation complete.

## Resolved: prior BLOCKED_SOURCE_CONFLICT (R3 section 4)

Owner Amendment 1, committed at `9cd873d`, replaces the original disposition's
points 1, 2 and 4. All four amended checks pass: the exact aggregate fields
`source_negative_count=59` and `new_master_axis_negative_count=25`, 84 distinct
IDs, independently derived 38 guarded/84 denied pairs and a bijective exact
ID/pair match. No per-ID provenance classification is inferred. All 84 rows
cite the amendment and re-derivation; the universe remains 627. Current evidence:
`stage_a/amendment_1/checks.json`. The historical failure below is retained,
not asserted as a current blocker. No V5 or R3 bytes were changed.

The preserved V5 member
`SOURCE_PINS_UNMODIFIED/STAGE_D03_REVIEW_BYTES/02_NEGATIVE_GRAPH_COMPLEMENT_59_SOURCE_PRESERVED.json`
contains **84 distinct authoritative negative IDs** at
`$.negative_cases[*].negative_id`:
`CC1-NEG-001..059` and `SD2-MST-NEG-001..025`.
R3 section 4 requires **59** from that named source and explicitly requires
`BLOCKED_SOURCE_CONFLICT` when a source count differs. Counting only the 59
preserved IDs would silently omit the 25 additional Master-derived cases.
The source archive and controlling prompt have not been amended.

The candidate-edge source has **42** actual candidates at
`$.edge_contracts[*].candidate_id`, not 80. The larger number counts separate
positive/negative oracle identifiers and is **not** a candidate-count blocker.
The independently rederived graph has **38 guarded / 84 denied pairs**, matching
those two expected graph totals; pair totals are not the negative-ID count.

`tools/extract_requirement_universe.py` preserves every actual source ID and
its provenance in `requirement_universe.csv` and one matching row per universe
ID in `traceability.csv`. `REQUIREMENT_UNIVERSE_REPORT.json` records actual and
expected counts. Pending implementation is kept separate from source conflict;
an unfinished later-stage module is not a missing owner approval or an executed
pass. The build source-count gate must fail, not silently choose a new count.

This blocks **traceability completion**, not safe independent implementation
under R3. A2 was gated and committed before this conflict checkpoint. The latest
owner instruction requires an immediate report when a hard gate blocks the
requested Stage A completion, so A3-A5 are not claimed complete or silently
continued before that report. A controlled disposition of the 59-versus-84
requirement is needed; no source or acceptance threshold is self-amended.

## Incomplete Stage A requirements

- Full technical reading of the verified V5 package, full requirement-universe
  extraction/traceability completion are not satisfied. The actual extracted
  universe is recorded, but the count conflict above prevents its final gate.
- A1-A2 authenticate signed synthetic snapshots and distinguish completed,
  forming, absent, failed and expected-stale inputs; publication/observation/
  vintage/revision/freshness/source alignment and signed IANA/DST/session checks
  are implemented. Their PASS verdict is fixture-data-only, not entry permission.
- Instrument definitions, dated listings, evidence graph, registration /
  plug-in manifests and the complete sixth-instrument onboarding proof remain.
- A5 passes full closed family-schema validation, exact plug-in/build binding,
  separate per-field listing and forward-only outcome evidence, process-local
  authenticated configuration registration and sixth-profile onboarding with
  zero changed source/plug-in-manifest bytes. Final Stage A traceability remains.
- A4 passes signed, bounded no-follow filesystem intake, including links, FIFO,
  hidden/unlisted files and explicit I/O faults.
- A3 implements distinct typed identity/run/replay records, exact source units
  and signed restriction-only T1/T2/T3 policy resolution. Missing bounds,
  forbidden T3 overrides, unsupported entry types and scope mismatches deny;
  no real owner-policy resolution or entry permit is provided.
- No monetary, real-market, timer or model policy has been invented. Open
  source decisions stay unavailable; the current loader cannot express a
  broker permit, entry flag, risk fraction or real owner-policy load.

The Stage A clauses were read and cited before A2 in
`stage_a/STAGE_A_REQUIREMENTS.csv` and `stage_a/SOURCE_READING.md`.
Whole-package reading is not inferred from that scoped reading record.

## Unstarted downstream work

Stages B-G, the full per-feature P0 inventory, complete traceability and the
paired comparison plan are not complete. Only initial macro summary/adoption
rows are recorded in `V2_V3_CAPABILITY_PARITY.csv`. No production Core-5 model
has been registered or used, and no performance comparison has been run.

The adopted EURUSD ex-EUR / GBPUSD ex-GBP basket and Core-5 event proximity
remain unimplemented. They may only become COMPUTE_AND_LOG_ONLY; no other
proposal item, entry gate, size modifier or automatic promotion is adopted.
V2_PARITY is comparison only. Their signal/audit/dashboard integration and
trading-decision noninterference tests remain pending.

The historical `preflight/BLOCKED_AUTHORITY.md` and original owner-start record
are unchanged. Their old statuses are historical evidence, not current
procedural barriers. No full-scope READY_FOR_R2_REVIEW, release, DEMO or LIVE
claim is made.
