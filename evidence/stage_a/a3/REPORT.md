# Stage A / A3 - Typed identities, exact source units and restriction-only T1 T2 T3 policy

Decision: PASS for this slice only. Overall Stage A: IN_PROGRESS.
Source reading and exact V5 member/clause mapping are recorded in `../SOURCE_READING.md` and `../STAGE_A_REQUIREMENTS.csv`.

| Gate | Actual result |
|---|---|
| Whole available V3 suite | 200 passed; 0 failed/skipped |
| Cumulative production statements | 569 / 569; 0 missing |
| Cumulative production branch destinations | 162 / 162; 0 missing/partial |
| Coverage exclusions | 0 excluded executable lines; exact inventory checked |
| Ruff lint / format and strict mypy | PASS |
| Explicit safety mutations | 14 killed; 0 survived |
| Cross-process determinism | Two independently launched processes; byte-identical |
| Network denial | Fresh pinned network-none container; six actual blocked probes |
| Source/mirror integrity | 69 V5 members; 482 macro / 374 reference / 19 wheels |

The exact source hashes, base commit, counters, commands and scope are in `GATE.json`; raw runner outputs are retained alongside it. The enclosing Git checkpoint identifies the committed source, rather than inventing a self-referential commit hash. The required negative tests are the executed JUnit cases, not the unexecuted oracles in the design archive.

No real monetary, model, broker, operational timer, DEMO or LIVE policy is selected. Later stages and full-scope R2 acceptance are not implied.
