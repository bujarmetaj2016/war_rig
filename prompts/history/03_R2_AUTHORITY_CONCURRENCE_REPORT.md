# R2 targeted review of the authority-gate correction

**Reviewer:** R2 (technical peer review only; not an independent human reviewer, not a signer).
**Date:** 16 November 2026.
**Reviewed:** the author's reconciliation package (zip sha256 `0ce00a15b58f5373f1e5220fd4b5653c1f27118097e70118934bed3cd99296af`). All 7 hashes in its `SHA256SUMS.json` match the actual bytes.

## Verdict

**I concur with the author's two objections, and I withdraw part of my own patch.**

- **Hardened file as sent** (`19169d10…b2`): `REVISE`. It needs six small precision edits (Q-1 to Q-6), all mechanical.
- **Concurred candidate** (`ac3344db248c3391327f8e59df8cc8e5c8bc7c208bc2e162e2549bd86120697f`, hardened file plus Q-1 to Q-6): **`PASS_FOR_IDE_USE`**. This certifies the prompt text only.
- It grants no implementation permission, no design acceptance and no human-independent validation. As things stand today, the prompt will stop at its own authority check, and that is correct.

## In plain words

The author is right on both points, and the pinned governance backs them up.

1. **A hash proves the bytes, not who signed.** My patch recorded `OWNER_ATTESTED_BY_HEADER` and called it a default. It was not mine to default. Your own sources say the signature, custody and review procedures must be completed and included in the group before it is presented. V5 member 10 step 1 says "with verified reviewer/custody/signature procedures. Resolve owner selections before final evidence-bound presentation". The pinned Group 1 record lists "deployment acceptance records and signature scheme" under CAR-01, which is `NOT_APPROVED_NOT_PERFORMED`. Your 27 October decision file records its own approval as `EXPLICIT_CONVERSATION_REPLY_NON_INDEPENDENT_NOT_CRYPTOGRAPHICALLY_SIGNED`. So no signature scheme is adopted yet, and an IDE prompt can't supply one.
2. **The signed records sit outside the group.** I called them "the filled and signed V5 member 12/13 forms". Member 10 step 2 seals "both unsigned owner forms" inside the group. Filling them in would change the presented group and void the interval (step 3 and rule (b)). The executed G0-R and G1-R records are separate records that name the presented root. Form 13 already has the field "Executed G0-R acceptance ID, SHA-256 and timestamp".
3. **A third point is mine to own.** I wrote that the root could follow "another rule" stated in the signed G0-R. That lets the approval record choose the root after the group was presented. The root rule must be fixed inside the group before presentation.

The author's replacement text fixes all three. I checked it against the sources, and the only changes I'm adding are precision edits.

## The six edits

Each edit is source-grounded. The exact old and new text is in `R2_AUTHORITY_DELTA_PATCH.md`.

| Edit | Fixes |
|---|---|
| Q-1 | The signature, witness and custody procedure must be a member of the presented group (or a controlling record a member names). A procedure that appears only in the header or the prompt is not accepted |
| Q-2 | Three exact outcomes: `VERIFIED_CRYPTOGRAPHIC`, `ATTESTED_BY_INDEPENDENT_HUMAN_RECORD`, `UNVERIFIED`. The hardened text had no passing value for the human-witness route, so that route could never pass |
| Q-3 | A group that states no root rule gives `BLOCKED_AUTHORITY`. A conflict with a controlling source gives `BLOCKED_SOURCE_CONFLICT`. The author's scenario list expected `BLOCKED_SOURCE_CONFLICT` for both |
| Q-4 | The presentation receipt must name the same root and cover every manifest member. "The last presented member is covered" could mean only the newest one, and scenarios 7 and 8 were untestable |
| Q-5, Q-6 | "Follows it in time" fails for a same-sitting signing, which member 13 allows. The rule becomes "not earlier than", with G1-R naming the G0-R hash |

## What I checked

- The author's 13-edit file equals my published preview byte for byte (hash `210f7867…`).
- The hardened file differs from it in exactly two hunks, both inside Section 1A. Every other line is identical, so the architecture, tools, tests, 100% line and branch coverage, MS-B, IG, V2 and scope are unchanged. Your 13 original R2 scenarios are untouched.
- The author's 13 targeted scenarios are in `R2_TARGETED_AUTHORITY_TESTS.md`, each with expected decision and enforcing line.
- The checker ran 60 text checks, all passing. They cover inputs and hashes, the two-hunk claim, apply and reverse, safeguard sentences, the value names, source grounding, scenario text, and four negative controls. I also planted five faults in the result text (a removed sentence, a retired value, weakened coverage, a reverted edit, a weakened IG rule). All five were caught.
- The author asked whether an existing pinned contract prescribes a different mechanism. None does. The nearest is CAR-01, quoted above, which is open.

## What this means for the prompt today

Today the prompt will return `BLOCKED_AUTHORITY`, and that is the right behaviour. V5 is not the final group (member 15 item 8) and has no record of a presentation. Member 14 is a `NOT_STARTED` template. The package also contains no signature procedure and no root rule. **No clock has started, so no sitting can be valid until the final group is presented and 48 elapsed hours pass.** The 27 October rules (a) and (b) are your decision, and I can't change them from a prompt.

## What you decide (listed once, before the final presentation)

None of these belong in the prompt. Each must sit inside the presented group, because changing it afterwards restarts the 48 hours.

1. **Independence route** (V5 member 15 item 5): name real independent humans, include a CAR-01 decision in the same group, or record from the V32 text that the control does not apply to an offline-only grant.
2. **The signature scheme for the G0-R and G1-R records**: a cryptographic key or a witnessed human signature, with where the custody copy is held. This is a CAR-01 item.
3. **The group root rule.** The author's suggestion is reasonable and I'd take it: the SHA-256 of the raw bytes of `MANIFEST_SHA256.json`, stated in a group member.
4. **The G1-R environment packet with real evidence** (V5 member 15 item 6, member 09 items G1-07 to G1-11).

The EC2 live-folder hash check is still open. It does not gate this offline build.

## What I could not verify (`NOT_VERIFIED`)

- The author's V5 ZIP bytes (`3d6632a2…`). I reviewed my own rebuild.
- Any signed record, any final group root, any completed wait, any independence, quorum, witness or custody record.
- WDA-08 and ATC-01 correctness. I designed both, so A-06 stays yours.
- Behaviour of any agent. This is a reading of text. No agent was run.

## My own disclosures

- My earlier "D-1" and "D-2" defaults were wrong against your pinned governance. I withdraw both. I had listed them as owner decisions but then recommended defaults that stood in for governance.
- My 63 checks passed on text that was wrong. Check H.4 confirmed the blank templates exist but did not test the group boundary. The author's reconciliation caught it, not my checker.
- The new checker is a text check against files. The planted-fault test shows it can fail, but it cannot show that an agent behaves correctly.

## Files

| File | Purpose |
|---|---|
| `R2_AUTHORITY_CONCURRENCE_REPORT.md` | This report |
| `R2_AUTHORITY_DELTA_PATCH.md` | The six edits with source-grounded reasons and fingerprints |
| `R2_TARGETED_AUTHORITY_TESTS.md` | The author's 13 targeted scenarios, each with decision and enforcing line |
| `01_SINGLE_IDE_IMPLEMENTATION_PROMPT_R2_AUTHORITY_CONCURRED_CANDIDATE.md` | The candidate. Not applied to anyone's file |
| `tools/` | `apply_auth_delta.py`, `verify_authority_delta.py` (60 of 60 pass), `auth_delta.py`, `prompt_patch.py`, `authority_check.txt` and `authority_check.json` |
