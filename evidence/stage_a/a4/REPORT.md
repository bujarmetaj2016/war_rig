# Stage A / A4 - Signed bounded descriptor-relative no-follow fixture filesystem intake

Decision: PASS for this slice only. Overall Stage A: IN_PROGRESS.
Source reading and exact V5 member/clause mapping are recorded in `../SOURCE_READING.md` and `../STAGE_A_REQUIREMENTS.csv`.

| Gate | Actual result |
|---|---|
| Whole available V3 suite | 256 passed; 0 failed/skipped |
| Cumulative production statements | 668 / 668; 0 missing |
| Cumulative production branch destinations | 196 / 196; 0 missing/partial |
| Coverage exclusions | 0 excluded executable lines; exact inventory checked |
| Ruff lint / format and strict mypy | PASS |
| Explicit safety mutations | 16 killed; 0 survived |
| Cross-process determinism | Two independently launched processes; byte-identical |
| Network denial | Fresh pinned network-none container; six actual blocked probes |
| Source/mirror integrity | 69 V5 members; 482 macro / 374 reference / 19 wheels |

The exact source hashes, base commit, counters, commands and scope are in `GATE.json`; raw runner outputs are retained alongside it. The enclosing Git checkpoint identifies the committed source, rather than inventing a self-referential commit hash. The required negative tests are the executed JUnit cases, not the unexecuted oracles in the design archive.

No real monetary, model, broker, operational timer, DEMO or LIVE policy is selected. Later stages and full-scope R2 acceptance are not implied.
