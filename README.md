# war_rig

Independent, broker-neutral V3 offline implementation. No trading, DEMO/LIVE,
deployment, model-fitting or V2-runtime authority.

Run the complete current V3 slice gate with `sh tools/run_offline.sh`. It uses
the exact image in `evidence/preflight/PYTHON_IMAGE.txt`, Docker `--network none`,
read-only reference inputs, and the owner-supplied hash-locked offline wheelhouse.
Never run V3 code or tests on the host. A clean checkout also needs the separately
supplied `reference/` inputs and `wheelhouse/`; neither is downloaded by the runner.

Stage A slice A1 implements authenticated fixture-policy metadata and immutable
UTC replay-clock primitives, not completed-bar/session eligibility or trading.
Progress and remaining work are in `evidence/STAGE_STATE.json`; executed evidence
is under `evidence/stage_a/a1/`. Each fresh validation run writes a new ignored
directory under `evidence/stage_a/runs/`, leaving committed evidence unchanged.
