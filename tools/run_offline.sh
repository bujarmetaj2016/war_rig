#!/bin/sh
# The host launches Docker only; no V3 import/test/install is allowed on the host.
set -eu
cd "$(dirname "$0")/.."
root=$(pwd -P)
image=$(cat evidence/preflight/PYTHON_IMAGE.txt)
output="evidence/stage_a/runs/$(date -u +%Y%m%dT%H%M%SZ)-$$"
if [ "$image" != "python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b" ]; then
    printf '%s\n' "Pinned image changed; review and update the sandbox contract first." >&2
    exit 1
fi
docker run --rm --pull never --network none --read-only \
    --cap-drop ALL --security-opt no-new-privileges \
    --pids-limit 128 --memory 1g --cpus 2 \
    --tmpfs /tmp:rw,noexec,nosuid,nodev,size=256m \
    --tmpfs /opt/venv:rw,exec,nosuid,nodev,size=512m \
    --mount "type=bind,src=$root,dst=/repo" \
    --mount "type=bind,src=$root/reference,dst=/repo/reference,readonly" \
    --workdir /repo --env HOME=/tmp --env PIP_DISABLE_PIP_VERSION_CHECK=1 \
    --env "OFFLINE_EVIDENCE_DIR=$output" \
    "$image" /bin/sh -eu -c '
        report="$OFFLINE_EVIDENCE_DIR"
        mkdir -p "$report"
        python -I tools/offline_preflight.py > "$report/preflight.json"
        python -m venv /opt/venv
        /opt/venv/bin/pip install --no-index --find-links wheelhouse --require-hashes \
            -r requirements-dev.lock > "$report/install.txt" 2>&1
        /opt/venv/bin/pip check
        /opt/venv/bin/pip freeze --all > "$report/installed.txt"
        /opt/venv/bin/ruff check v3 tests/v3 tools > "$report/lint.txt"
        /opt/venv/bin/ruff format --check v3 tests/v3 tools >> "$report/lint.txt"
        /opt/venv/bin/python -m mypy --strict v3 > "$report/types.txt"
        /opt/venv/bin/python -m pytest -q --strict-markers --strict-config \
            --cov=v3.offline --cov-branch --cov-report=term-missing \
            --cov-report=json:"$report/coverage.json" \
            --cov-report=xml:"$report/coverage-report.xml" \
            --cov-fail-under=100 --junitxml="$report/junit.xml" \
            > "$report/tests.txt" 2>&1 || {
                cat "$report/tests.txt"
                exit 1
            }
        /opt/venv/bin/python -I tools/check_stage_a_evidence.py "$report" \
            > "$report/checks.json"
        /opt/venv/bin/python -I tools/check_stage_a_mutations.py \
            > "$report/mutations.json"
        /opt/venv/bin/python -m tools.check_stage_a_registration \
            > "$report/registration.json"
        /opt/venv/bin/python -I tools/record_stage_a_completion.py --check \
            > "$report/stage-a-traceability.json"
        cat "$report/tests.txt"
        cat "$report/lint.txt" "$report/types.txt"
        printf "%s\n" "Exact counters, independence, replay and mutation checks: PASS"
        python -I tools/extract_requirement_universe.py --check-source-counts \
            > "$report/traceability-check.txt" 2>&1 || {
                status=$?
                cat "$report/traceability-check.txt"
                printf "%s\n" \
                    "BLOCKED: source-count/cardinality gate failed; runtime results above are separate." >&2
                exit "$status"
            }
    ' || {
        status=$?
        printf 'Evidence: %s\nRunner exit code: %s\n' "$output" "$status" >&2
        exit "$status"
    }
printf 'Evidence: %s\n' "$output"
