# war_rig

Independent, broker-neutral V3 offline implementation. No trading, DEMO/LIVE,
deployment, model-fitting or V2-runtime authority.

Run the complete current V3 slice gate with `sh tools/run_offline.sh`. It uses
the exact image in `evidence/preflight/PYTHON_IMAGE.txt`, Docker `--network none`,
read-only reference inputs, and the owner-supplied hash-locked offline wheelhouse.
Never run V3 code or tests on the host. A clean checkout also needs the separately
supplied `reference/` inputs and `wheelhouse/`; neither is downloaded by the runner.

Stage A slices A1-A5 implement authenticated fixture metadata and signed synthetic
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
Progress and remaining work are in `evidence/STAGE_STATE.json`; executed evidence
is under `evidence/stage_a/a1/` through `a5/`. V5 file/clause citations are in
`evidence/stage_a/STAGE_A_REQUIREMENTS.csv`. Each fresh validation run writes a new ignored
directory under `evidence/stage_a/runs/`, leaving committed evidence unchanged.

The full command also enforces R3's extracted source-count gate. Owner Amendment 1
resolves the former NEG conflict using exact aggregate fields, 84 unique IDs and
the independently rederived graph bijection; the universe remains 627.
See `evidence/stage_a/amendment_1/checks.json` and
`evidence/REQUIREMENT_UNIVERSE_REPORT.json`. No source is adjusted automatically.
