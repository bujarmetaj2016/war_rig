# Stage A / A1 - signed fixture identity and replay clock

Decision: PASS for this bounded slice only. Overall Stage A: IN_PROGRESS.
No trading, broker, model, entry or monetary capability is implemented.
The historical blocked checkpoint was committed unchanged as
`d6549b612b8415ecaa7101bf6e80b7061018199c` before verifying the new inputs.

## Delivered boundary

| Source | Contract mapping | Implemented scope |
|---|---|---|
| `v3/offline/fixture_policy_loader.py` | EXT-06, member 17 crosswalk; EXT-G0R-14 lines 130 and 359 | Pure signed FIXTURE_ONLY identity/validity metadata loader, not a financial policy resolver |
| `v3/offline/calendar_completion.py` | Original unit 06, member 17; Master V1.8 lines 137 and 161 | Immutable UTC replay-clock primitives only, not the complete snapshot/calendar module |
| `tools/run_offline.sh`, preflight/evidence tools | R3 sections 1A-1C, 1B and 6 | Fresh pinned network-none execution, locked install, exact coverage, mutation and independence evidence |

The loader verifies Ed25519 over
`WAR_RIG_DEV_FIXTURE_V1` + one NUL byte + the exact manifest bytes.
The caller supplies an independently pinned public key, not a key taken from
the untrusted payload. Signature authenticity and SHA-256 integrity are
separate checks. Authenticated results carry manifest/payload/signer hashes,
immutable policy/run/simulated-account IDs, instrument IDs and UTC validity.
They have no eligibility or send-permit fields.

The implementation-specific development envelope has exactly these manifest
fields: `schema_version=1`, `domain=FIXTURE_ONLY`, `payload_sha256`,
`max_bytes`, `max_depth`, `max_nodes`. The payload has exactly `policy_id`,
`run_id`, `account_id`, `instrument_ids`, `valid_from`, `valid_until`.
This is not an owner-policy format or a source-contract amendment. Adding
monetary, entry, broker or other unknown fields denies intake. Accounts must
be labelled `SIMULATED_...`; no actual account is read or represented.

Signed parser limits in the synthetic fixture are 16,384 bytes, depth 8 and
128 value nodes. Fixed bootstrap ceilings (4,096 manifest bytes and payload
limits no larger than 1 MiB / depth 32 / 10,000 nodes) protect parsing of the
limits themselves; they select no market, freshness, risk or timer policy.
Nesting is checked before JSON decoding. Duplicate keys, floats/nonfinite
numbers, malformed/oversized input, invalid identities, wrong keys/signatures,
hash mismatch, unknown fields and expired/not-yet-valid/naive timestamps deny
explicitly. Validity is the documented half-open fixture interval
`[valid_from, valid_until)`; there is no wall-clock lookup.

The fixture lists the Core-5 plus `SYNTHETIC_6` without an instrument switch in
code. This proves metadata-list extensibility only, NOT full V3EXT-006
instrument-definition/registration or six-instrument trading.

## Execution evidence

Reproduction: `sh tools/run_offline.sh` from the repository root. No host Python
or host V3 execution is used. It consumes the exact owner-supplied image:

`python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b`

The fresh container has `--network none`, read-only root, all capabilities
dropped, no-new-privileges, bounded memory/PIDs/CPU, a read-only reference
mount, no host credential mounts/environment and executable tmpfs only for
the pinned dependency environment. The mirror install is exactly:

`pip install --no-index --find-links wheelhouse --require-hashes -r requirements-dev.lock`

All 482 macro-manifest entries, all 374 reference-manifest entries and all
19 wheel checksums verify. Exact manifest membership is also checked for the
wheelhouse. There are no missing macro inputs. V5 identity and all 69 member
hashes/path-safety checks pass. The archive is not extracted or executed.
Both external research evidence and the old owner-start/authority reports
remain unchanged.

The active sandbox proved six actual denied probes: literal IP TCP, DNS,
metadata IP TCP, Python-child HTTP, shell-child HTTP and loopback HTTP redirect
to metadata. Only loopback is UP; Docker Desktop exposes additional DOWN
kernel tunnel interfaces, which do not supply egress. The host runner fixes
Docker's network mode and the preflight inspects interfaces before probing.
No broker/cloud/model SDK is present.

The Ed25519 development key was generated inside the verified sandbox at the
git-ignored `keys/dev_fixture_signing.key`, mode 0600. Only its public key and
fingerprint are committed, in `evidence/preflight/DEV_FIXTURE_PUBLIC_KEY.json`.
Its fingerprint is
`6dab654164d1e219c5bfc2c4bee1bc73c418f0151bb1162dac6e62150ca0baac`.
The development key confers no owner, risk, model or trading authority.

| Gate | Actual result |
|---|---|
| Whole available V3 suite (`tests/v3`, not independent research tests) | 77 passed; zero failed/skipped |
| Cumulative production statements | 175 covered / 175 total; 0 missing |
| Cumulative production branch destinations | 70 covered / 70 total; 0 missing/partial |
| `calendar_completion.py` | 23 statements, 4 branches; 0 missing |
| `fixture_policy_loader.py` | 152 statements, 66 branches; 0 missing |
| Coverage exclusions | 0 excluded executable lines; exact required-module inventory checked |
| Ruff lint / format | PASS |
| Strict mypy | PASS, all four first-party source files including package initializers |
| Explicit safety mutations | 8 killed, 0 survived, 0 collection errors |
| Cross-process determinism | Two independently launched processes, byte-identical output |
| V2 byte / normalized overlap | 279 source files compared; 0 identical-byte or 12-normalized-line matches |

Coverage includes every Python module in `v3.offline`, including the empty
package initializer, with branch tracking. Test/fixture/build-evidence tooling
is transparently outside the first-party runtime coverage denominator.
The 12-line comparison strips/collapses whitespace and omits blank/full-line
comments. Import allowlists and finite-recall source comparisons do not prove
the absence of every conceivable V2 reuse; no V2 source was imported/executed.

The eight mutants remove signature verification, payload hashing, the
fixture-domain check, duplicate-key rejection, payload byte bounds, signature
domain separation, expiry exclusivity and rewind prevention. The harness
requires actual assertion failures, not collection errors, and verifies the
real source is unchanged after disposable repository-local copies are removed.
No optional third-party mutation tester or vulnerability/licence scanner was
installed or run.

Machine-readable coverage, JUnit, source hashes, preflight errors, mutation
selectors and replay witness are in this directory. A fresh reproduction writes
a new ignored `evidence/stage_a/runs/...` directory rather than overwriting this
committed checkpoint.

## Failed attempts retained honestly

The first dependency install failed with exit 126:
`sh: 1: /opt/venv/bin/pip: Permission denied`. Docker tmpfs defaults included
noexec. No packages or V3 code ran in that attempt. Recreating the same
network-none sandbox with `exec` on the isolated dependency tmpfs resolved it;
the root filesystem remained read-only and network controls were unchanged.

The initial test run had 73 passes and one failure: a deeply nested input
was denied with RESOURCE_BOUND rather than the test's assumed decoder JSON
failure. The implementation was strengthened to reject excessive nesting
before the decoder, and tests now assert that deterministic resource denial.
The retained initial output is not claimed as a pass. An initial preflight
also rejected the DOWN tunnel interfaces by name; it was corrected to check
IFF_UP flags while retaining Docker network-none and actual hostile probes.

## Remaining Stage A and release scope

Full verified-package contract reading and complete requirement-universe /
traceability extraction remain incomplete; this slice's scope mapping is not
the full R3 section 4 deliverable. Completed/forming bars, publication/vintage/
freshness, IANA/DST/session calendars, source/instrument/policy/event identity
binding, T1/T2/T3 resolution, instrument definitions/listings/plug-in manifests,
bounded symlink-safe filesystem intake and fully integrated signed snapshots
remain to be implemented. Operational D1-D3/E1-E3 values remain UNSET.

The adopted USD baskets/event proximity are not implemented or connected to a
signal, audit ledger or dashboard yet. Their approved scope stays
COMPUTE_AND_LOG_ONLY; V2_PARITY remains comparison only. No entry, direction,
size, TP/SL, trailing, model-input or gate behaviour is enabled by this slice.
No performance comparison was run. Stages B-G are unstarted. There is no
READY_FOR_R2_REVIEW/full-scope, release, DEMO or LIVE assertion.
