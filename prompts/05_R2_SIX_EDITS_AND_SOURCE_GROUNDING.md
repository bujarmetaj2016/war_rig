# R2 AUTHORITY DELTA - six exact edits on the author's authority-hardened prompt

**Status:** `PROPOSED_NOT_APPLIED` to the author's file. The candidate is a separate file.

| Fingerprint | SHA-256 |
|---|---|
| Original master prompt | `916f139321e4ceacb31bb5137423361617fa03d5f59f7b7319afc44c8f3f5346` |
| R2 13-edit prompt (author's file equals R2's preview byte for byte) | `210f786762aef83bcc4566f243a0b1ca6c12d6716a74b6e17e51062575108d1c` |
| Base of this delta: author's authority-hardened candidate | `19169d10c9a7bcd04dce9a1d072c13210ef5e6afa44a1fdf18a021b8b6f2e2b2` |
| After this delta (6 edits, byte-exact) | `ac3344db248c3391327f8e59df8cc8e5c8bc7c208bc2e162e2549bd86120697f` |

**Apply:** `python3 -I -B apply_auth_delta.py HARDENED.md OUT.md`. It stops and writes nothing if the base hash is wrong, if any old text does not occur exactly once, or if it was already applied.

**What it does not touch:** every line outside Section 1A is identical to R2's 13-edit prompt (checked, D.3), so architecture, tools, tests, 100% line and branch coverage, MS-B, IG, V2 and scope are unchanged. It changes no source pin, no clock and no accepted scope.

---

## Q-1 - prompt line 51 of the candidate

**Why (source-grounded):** The signature procedure must be inside the presented group (V5 member 10, sequence step 1: 'verified reviewer/custody/signature procedures' are completed BEFORE the final presentation). The base says 'the accepted procedure' without saying where it must live, so a procedure named only in the header or the prompt could be taken as accepted.

**Old text (must occur exactly once in the hardened candidate):**

```text
If the accepted procedure uses cryptographic signatures, verify each against the independently trusted authorised key and record the key fingerprint, trust anchor, scope and validation result.
```

**New text:**

```text
The signature, witness and custody procedure must itself be a member of the presented group (or an adopted controlling record that a member names); a procedure that appears only in the header, this prompt or the author's text is not accepted. If the accepted procedure uses cryptographic signatures, verify each against the independently trusted authorised key and record the key fingerprint, trust anchor, scope and validation result.
```

## Q-2 - prompt line 51 of the candidate

**Why (source-grounded):** The base only says what must never be marked `VERIFIED`; it defines no passing value for the human-witness path, so that path can never be satisfied or the agent has to improvise. Three exact values make the outcome testable and keep the agent from claiming it authenticated a human signature.

**Old text (must occur exactly once in the hardened candidate):**

```text
the implementing agent cannot create or independently authenticate such an attestation. A typed name, matching hash, pasted header, self-signed note without trusted key, or the author's assertion alone must **never** be marked `SIGNATURE_AUTHENTICITY=VERIFIED`.
```

**New text:**

```text
the implementing agent cannot create or independently authenticate such an attestation. Record exactly one value: `SIGNATURE_AUTHENTICITY=VERIFIED_CRYPTOGRAPHIC` (the agent verified each signature against the trusted key), `SIGNATURE_AUTHENTICITY=ATTESTED_BY_INDEPENDENT_HUMAN_RECORD` (the agent verified only that the named independent human's signed attestation exists, is held outside the workspace and names the exact record hashes) or `SIGNATURE_AUTHENTICITY=UNVERIFIED`. Only the first two can pass, and only under the procedure in the presented group. A typed name, matching hash, pasted header, self-signed note without trusted key, or the author's assertion alone must **never** be marked as either passing value.
```

## Q-3 - prompt line 53 of the candidate

**Why (source-grounded):** Today no V5 member states a root rule (V5 member 10 step 2 says only 'hash every member and group root'). The base leaves the no-rule case undefined (a 'when the controlling source explicitly specifies' clause). The rule must sit inside the group before presentation, and its absence must give one fixed result.

**Old text (must occur exactly once in the hardened candidate):**

```text
The final group's approved root algorithm must be established in the pre-presentation governing manifest/record; when the controlling source explicitly specifies a SHA-256 manifest root, recompute it from the exact raw manifest bytes and verify every listed entry.
```

**New text:**

```text
The presented group must state its root rule in one of its own members (or in an adopted controlling record that a member names), for example the SHA-256 of the raw bytes of its manifest file; quote that statement in the preflight report, recompute the root from the exact raw bytes and verify every listed entry. If no member states a root rule, the result is `GATE=BLOCKED_AUTHORITY`.
```

## Q-4 - prompt line 55 of the candidate

**Why (source-grounded):** 'The last presented group member is covered' can be read as covering only the newest member. Targeted scenarios 7 and 8 (partial presentation; change after presentation) are only testable if the receipt must name the root and cover every manifest member.

**Old text (must occur exactly once in the hardened candidate):**

```text
confirm that the last presented group member is covered,
```

**New text:**

```text
confirm that the receipt names the same root and covers every member listed in the final manifest,
```

## Q-5 - prompt line 55 of the candidate

**Why (source-grounded):** V5 member 13 allows G1-R 'in the same sitting as G0-R' with 'G0-R signed first'. 'Follows it in time' fails when both carry the same UTC minute; the binding that proves order is G1-R naming the G0-R hash (member 13 line 'Executed G0-R acceptance ID, SHA-256 and timestamp').

**Old text (must occur exactly once in the hardened candidate):**

```text
and verify both owner signatures occurred only after the hold (G0-R then G1-R) and before the first implementation commit
```

**New text:**

```text
and verify both owner signatures occurred only after the hold, that the G0-R time is not later than the G1-R time, and that both precede the first implementation commit
```

## Q-6 - prompt line 53 of the candidate

**Why (source-grounded):** Same point as Q-5, in the paragraph that describes the executed records.

**Old text (must occur exactly once in the hardened candidate):**

```text
and follows it in time.
```

**New text:**

```text
and is not earlier than it (the same sitting is allowed).
```
