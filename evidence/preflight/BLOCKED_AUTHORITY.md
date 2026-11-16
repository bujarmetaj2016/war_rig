# BLOCKED_AUTHORITY — War Rig V3 preflight (master prompt Section 1A)

GATE=BLOCKED_AUTHORITY
SIGNATURE_AUTHENTICITY=UNVERIFIED
Runtime/implementation code: NOT STARTED (by design).

## Verified from supplied files
- Master prompt SHA-256 = ac3344db248c3391327f8e59df8cc8e5c8bc7c208bc2e162e2549bd86120697f (matches expected).
- V5 ZIP SHA-256 = 3d6632a2d662deade05b957ad822edd9af6e8eda8c1d7ebca3f098e122760796 (matches candidate value in prompt s1).
- ZIP: 70 members; manifest lists 69; every listed member hash matches; no unlisted members; no traversal/symlink entries.
- One-file design md SHA-256 = 943aae60d94ca54eecc10349dc8a4ef8f78e556e57d34f78a23732151792e6a9 (reference only).
- V5 member 14 still declares: group_finalized=false, group_root_sha256=null, G0R=UNSIGNED, G1R=UNSIGNED,
  implementation_permission=false, status=NOT_STARTED, duration_elapsed_hours=0.

## Missing evidence (all required; none can be created by the agent)
1. Owner Authority Header (7 fields: FINAL_GROUP_ROOT_SHA256, G0R_RECORD_SHA256, G1R_RECORD_SHA256,
   FINAL_PRESENTATION_UTC, WAIT_COMPLETED_UTC, INDEPENDENT_EVIDENCE_SHA256, ENV_PACKET_SHA256) — not supplied.
   Prompt rule: no complete header => BLOCKED_AUTHORITY, nothing else done.
2. Final evidence-bound group (manifest with root rule, final root) — V5 is a review candidate, not final.
3. Executed, signed G0-R and G1-R records (post-hold, same root; G1-R names G0-R hash) — files not present.
4. Signature/witness/custody procedure inside the group plus independent verification evidence.
5. Trusted presentation receipt and independent proof of >=48h elapsed with unchanged membership.
6. Independent evidence pack (review, quorum, witness, custody; member 09 G1-02/03/12).
7. Signed disposition of OPEN/DEFER/UNSET/NOT_SELECTED owner decisions (or effective denial).
8. G1-R environment packet (member 09 G1-07..11): pinned Python/lock/offline mirror, enforced deny-egress proof,
   scans, negative-test manifest.

## Note
Owner chat declarations of G0-R/G1-R are intent only and do not satisfy the above.

## Next step
Supply the complete header plus the referenced signed records and packets in the workspace, then re-run preflight.
