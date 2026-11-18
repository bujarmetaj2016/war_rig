# war_rig

Independent, broker-neutral V3 offline implementation. No trading, DEMO/LIVE,
deployment, model-fitting or V2-runtime authority.

Run the complete current V3 slice gate with `sh tools/run_offline.sh`. It uses
the exact image in `evidence/preflight/PYTHON_IMAGE.txt`, Docker `--network none`,
read-only reference inputs, and the owner-supplied hash-locked offline wheelhouse.
Never run V3 code or tests on the host. A clean checkout also needs the separately
supplied `reference/` inputs and `wheelhouse/`; neither is downloaded by the runner.

Stage A slices A1-A2 implement authenticated fixture metadata and signed synthetic
completed snapshots, point-in-time publication/revision/freshness checks, explicit
source/unit bindings, UTC replay/event clocks and signed IANA calendar/session/DST
evidence. These are data assessments, not entry permission or trading.
Progress and remaining work are in `evidence/STAGE_STATE.json`; executed evidence
is under `evidence/stage_a/a1/` and `a2/`. V5 file/clause citations are in
`evidence/stage_a/STAGE_A_REQUIREMENTS.csv`. Each fresh validation run writes a new ignored
directory under `evidence/stage_a/runs/`, leaving committed evidence unchanged.

The current full command also enforces R3's extracted source-count gate. It is
explicitly blocked on D03 file02's 84 negative IDs versus the required 59; the
runtime gate remains separately recorded as passed. See
`evidence/BLOCKED_REQUIREMENTS.md` and `evidence/REQUIREMENT_UNIVERSE_REPORT.json`.
No count or source is adjusted automatically.
