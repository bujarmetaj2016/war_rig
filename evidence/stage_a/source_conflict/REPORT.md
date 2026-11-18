# Stage A hard-gate report

Status: **BLOCKED_SOURCE_CONFLICT**. Stage A is not complete.
A2 was committed at `b63d8822bc137fa0434763edda26a2846a1d04f5`.
The original accepted A1 checkpoint is preserved unchanged.

The Stage A V5 source clauses were read before A2 and are cited by member and
clause in `../STAGE_A_REQUIREMENTS.csv`; `../SOURCE_READING.md` states the exact
reading scope. Whole-package reading is not claimed complete.

| Gate | Actual result |
|---|---|
| Whole available V3 suite | 152 passed; zero failed/skipped |
| Cumulative production statements | 363 covered / 363 total; zero missing |
| Cumulative production branch destinations | 110 covered / 110 total; zero missing/partial |
| `calendar_completion.py` | 136 statements / 22 branches; zero missing |
| `data_intake_schema.py` | 65 statements / 22 branches; zero missing |
| `fixture_policy_loader.py` | 162 statements / 66 branches; zero missing |
| Coverage exclusions | Zero excluded executable lines; exact inventory checked |
| Ruff lint / format / strict mypy | PASS |
| Explicit safety mutations | 12 killed; zero survived/collection errors |
| Cross-process determinism | Two independently launched processes; byte-identical |
| V2 byte / normalized overlap | 279 files; zero identical-byte / 12-line matches; finite recall |
| Actual isolation | Exact pinned image; network none; six real hostile probes denied |
| Immutable inputs | 69 V5 members, 482 macro entries, 374 reference entries, 19 wheels verified |
| Full runner, including source-count gate | **Exit 2 / BLOCKED_SOURCE_CONFLICT**, not PASS |

The new A2 runtime covers signed synthetic snapshots, exact source/run/policy/
unit bindings, completed/forming/missing/failed/expected-stale distinctions,
publication/observation/vintage/revision availability, signed freshness limits,
signed TZif-backed IANA/session/DST evidence, immutable lineage references and
verified synthetic event-clock domain/skew/monotonic comparisons. It creates no
entry permit or real broker/operational-clock authority.

## Exact source conflict

R3 section 4 requires 59 negative IDs in
`SOURCE_PINS_UNMODIFIED/STAGE_D03_REVIEW_BYTES/02_NEGATIVE_GRAPH_COMPLEMENT_59_SOURCE_PRESERVED.json`.
Its authoritative `$.negative_cases[*].negative_id` field contains **84 distinct
IDs**: `CC1-NEG-001..059` plus `SD2-MST-NEG-001..025`.
The 59-ID subset does not exhaust the named source. Neither the source bytes nor
the expected count has been changed. A controlled count disposition is required.

The candidate source contains 42 actual candidates, as expected. Its POS/NEG
oracle identifiers are not additional candidate edges. The independently
rederived 38 guarded and 84 denied pairs also match. They are graph-pair totals,
not authority to replace the negative-ID acceptance count.

## Traceability totals

The mechanically extracted universe and traceability CSV each contain **627
unique rows**, with no absent/extra/duplicate mapping IDs. Each retains exact
source provenance. All 627 whole-contract implementation dispositions remain
honestly pending; zero are promoted to `IMPLEMENTED_TESTED`,
`DENIED_BY_POLICY_TESTED`, `OUT_OF_G1_SCOPE`,
`BLOCKED_MISSING_APPROVAL` or `NOT_APPLICABLE_WITH_SIGNED_PROOF`.
This does not erase the separately passed A1-A2 primitive slices.
There is **one source-count blocker**, not 627 missing owner approvals.

Verified source-class counts: 13 components; 18 modules; 61 decision rows
(43/14/4); 13 findings; 21 repairs; 187 D03 test specifications; 42 candidate
IDs; 84 negative IDs; 19 MS-B cases; 10 initial-protection cases; 83 EXT IDs;
57 ATC IDs; 59 WDA oracles plus six canonical vectors; 38 inherited G1R IDs.
Classes overlap by source identity, so their counts must not be summed as a
unique-universe count. Exact extraction rules and graph derivation are in
`../../REQUIREMENT_UNIVERSE_REPORT.json`.

The current full command is `sh tools/run_offline.sh`: runtime checks pass, then
`--check-source-counts` fails explicitly. `runner.txt` and
`runner_exit_code.txt` preserve the actual output and exit status; `full_run/`
contains that fresh run's complete artifacts. Pending later implementation alone
does not fail the source-count mode.

R3 says this conflict blocks traceability completion, not safe independent
runtime work. The owner's latest instruction asks for an immediate hard-gate
report, so this checkpoint reports the blocker without claiming or beginning
the remaining tier-precedence, filesystem-intake or instrument-registration /
sixth-instrument slices. No full Stage A, full-scope R2, release, DEMO or LIVE
readiness is asserted.
