# war_rig

Independent, broker-neutral V3 offline implementation. No trading, DEMO/LIVE,
deployment, model-fitting or V2-runtime authority.

Run the complete current V3 slice gate with `sh tools/run_offline.sh`. It uses
the exact image in `evidence/preflight/PYTHON_IMAGE.txt`, Docker `--network none`,
read-only reference inputs, and the owner-supplied hash-locked offline wheelhouse.
Never run V3 code or tests on the host. A clean checkout also needs the separately
supplied `reference/` inputs and `wheelhouse/`; neither is downloaded by the runner.

Stage A is complete (A1-A6): authenticated fixture metadata and signed synthetic
completed snapshots, point-in-time publication/revision/freshness checks, explicit
source/unit bindings, UTC replay/event clocks and signed IANA calendar/session/DST
evidence, distinct immutable identities, exact source-price units and a
restriction-only T1/T2/T3 fixture policy resolver. These are data/parameter
assessments, not entry permission or trading. Signed filesystem policies constrain
descriptor-relative, no-follow intake to bounded regular JSON fixture files.
Immutable family definitions, exact build-bound plug-in metadata and separate
per-field listings/forward-only outcomes support six schema profiles. Signed
configuration commands use process-local serialized expected-state checks;
this is not the later operational ledger or any promotion/approval authority.
The final gate has 431 passing tests, 956/956 statements, 268/268 branch
destinations and 19 killed safety mutants, with no coverage exclusions.
Executed evidence is under `evidence/stage_a/a1/` through `a6/`. All 27 Stage A
requirements have exact V5 member/clause and runtime/test/evidence mappings in
`evidence/stage_a/STAGE_A_COMPLETION.csv`. The earlier
`STAGE_A_REQUIREMENTS.csv` preserves the pre-A2 reading checkpoint.
Each fresh run writes a new ignored directory under `evidence/stage_a/runs/`,
leaving committed evidence unchanged.

Stages B-G remain unstarted. The 627-row global trace has three completed
whole-source oracles, 19 partially implemented and 605 unimplemented; 624 have
no final disposition. Stage A completion is not full-scope readiness or
implementation of Core-5 trading strategies. See `evidence/STAGE_STATE.json`
and `evidence/REVIEWER_R2_HANDOFF.md`.

The full command also enforces R3's extracted source-count gate. Owner Amendment 1
resolves the former NEG conflict using exact aggregate fields, 84 unique IDs and
the independently rederived graph bijection; the universe remains 627.
See `evidence/stage_a/amendment_1/checks.json` and
`evidence/REQUIREMENT_UNIVERSE_REPORT.json`. No source is adjusted automatically.
