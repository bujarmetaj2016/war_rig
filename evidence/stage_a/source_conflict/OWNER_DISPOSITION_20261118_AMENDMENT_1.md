# Amendment 1 to OWNER_DISPOSITION_20261118.md (18 Nov 2026)

Reason: file 02 has no per-record provenance field (only aggregate counts and a reason), and all 84 NEG- ids are already in the
627-row requirement universe. Points 1, 2 and 4 of the original disposition cannot be applied as written. They are replaced as follows;
points 3 and 5 stand.

1. No per-id preserved/derived classification is required. Do not infer one from id prefixes, order or the reason text.
2. The NEG count gate in R3 §4 is satisfied if, and only if, all of these hold:
   a. file 02's own aggregate fields state 59 source-preserved and 25 Master-derived (cite the exact fields);
   b. file 02 contains exactly 84 distinct NEG- ids;
   c. the independent mechanical re-derivation from the V5 transition graph gives exactly 84 denied pairs (and 38 guarded);
   d. the 84 ids and the 84 re-derived pairs match one-to-one.
   If any of a–d fails, the gate stays BLOCKED_SOURCE_CONFLICT.
3. The requirement universe stays at 627 rows. No ids are added or duplicated. Each of the 84 NEG rows cites this amendment and the
   re-derivation evidence.
4. R3 is not edited.
