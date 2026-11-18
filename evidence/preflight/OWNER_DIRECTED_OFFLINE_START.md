# Owner-directed offline start - 18 November 2026

OFFLINE_DEVELOPMENT_ROUTE=OWNER_DIRECTED
FORMAL_GOVERNANCE_ATTESTATION=NOT_VERIFIED
TRADING_AUTHORITY=NONE
BROKER_CAPABILITY=DENIED
REFERENCE_PACKAGE=V5_CANDIDATE
EXECUTION_GATE=BLOCKED_ENVIRONMENT

The current user instructed execution of the macro handover and continuation of
R3. The owner-declared acceptance of Option R / Scope C and the cooling-off
period described in R3 are recorded as OWNER_DECLARED, not
INDEPENDENTLY_VERIFIED_FORMAL_HOLD. This is internal broker-independent offline
development only: no deployment, notifications, DEMO/LIVE, V2 runtime access,
model fitting, promotion or trading authority. No signature or R2 approval is
asserted.

## Input identities

| Input | SHA-256 |
|---|---|
| Current R3 prompt, `prompts/War_Rig_V3_OWNER_DIRECTED_OFFLINE_START_MASTER_IDE_PROMPT_R3_20261116.md` | `52d86cfc4b4e2b4bcb9791d04c35ae2bd9c876198f55a147622c21d341de41b5` |
| Historical R2-concurred prompt, read but not executed | `ac3344db248c3391327f8e59df8cc8e5c8bc7c208bc2e162e2549bd86120697f` |
| V5 candidate ZIP in `design/` | `3d6632a2d662deade05b957ad822edd9af6e8eda8c1d7ebca3f098e122760796` |
| V5 internal `MANIFEST_SHA256.json` | `756cc650770105a30ef7e824d275476ce7e642b77dccf407f704e7146ec5a135` |
| `reference/MANIFEST.sha256` | `a06ac2de31fcce5436d9c975ea7b0cf872a050a6b7d475e2e4b2f09fdff1a38b` |
| `evidence/macro/MANIFEST.sha256` | `12ebf4559badf11714ff6af71eb1092537230ed699721fc3bda6b95bdb3a17ca` |
| Macro owner decision | `fdbf1eae05af2307afe0f2bcc18bb16c370c1e5f8936a9748170a3a4a92c9d4a` |
| Historical `BLOCKED_AUTHORITY.md`, preserved unchanged | `53f37c69cd870df237ec8fe8c9d83e4860823ceca3a8cbc9ce63c5831a12d589` |

Baseline checkout: independent `war_rig` repository, branch `main`, commit
`f64c138b145e7000bb81559d79316bfba29b419d`. No previous stage state, V3 package
or V3 test tree exists in this checkout. `git merge main` returned
`Already up to date.` No new merge commit was created. Research commit
`2fdd7e3981d498ab7783bb81ac643eafe8abe998` is an ancestor of HEAD through
merge `efece4a3c981033b161f49769db42ed06eb6ea69`.

## Verified scope and limitations

`shasum -a 256 -c SHA256SUMS.txt` passed all eight entries. A bounded,
non-extracting ZIP inspection verified all 69 manifest members, all member
sizes/hashes, exact membership and unique safe paths in the 70-member archive.
No executable members or symlinks were found. Candidate ID:
`V3-ONE-STAGE-OFFLINE-CORE-CANDIDATE-20261113-V5`;
status `PROPOSED_CANDIDATE_NOT_FROZEN`. This is not a final approved group root.
Detailed contract reading and requirement-universe extraction are not complete.

All 374 reference-manifest entries verify. The macro manifest's own hash
matches the handover, and 412 of its 482 filesystem entries verify, including
the inventory, gap, findings and proposal. Seventy historical input paths are
absent; no available file has a mismatched hash. The exact missing list is in
`SOURCE_VERIFICATION_20261118.json`. This limits historical reproduction, not
the verified source inventory. Research files were read in place only and
were not modified or copied.

Docker Desktop is available. The locally present immutable image
`sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b`
reports Python 3.12.16. It was used for preflight-only standard-library
inspection and egress probes, not V3 code. This observation does not select an
approved runtime interpreter or supply pinned dependency provenance.

Outbound literal-IP TCP, DNS, metadata-IP TCP, Python-child HTTP and
shell-child HTTP all failed inside `--network none`. Repository and reference
mounts were read-only; no host credential directories or environment variables
were forwarded. Raw probe errors are in `INSPECTION_20261118.json`.
No V3 runtime/tests or V2 source were imported or executed.

The full execution gate remains BLOCKED_ENVIRONMENT: `requirements-dev.lock`,
`wheelhouse/` and `wheelhouse/SHA256SUMS` are absent. No dependency was fetched
or installed. Signed fixtures, fixture signing keys, dependency/broker SDK
scans, redirect probes and the complete repeatable runtime safety suite remain
unexecuted. Resume Stage A only after the R3 section 1C environment is complete;
the successful preflight probes are not a stage PASS.
