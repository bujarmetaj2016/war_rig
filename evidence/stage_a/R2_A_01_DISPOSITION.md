# R2-A-01 - session-close completion correction

**Finding:** MAJOR. Implementation fixed; reviewer acceptance is not asserted.
This is a Stage A correction with cumulative Stage B revalidation, not new
strategy, entry, model, broker or trading authority.

## V5 source and interpretation

The verified V5 candidate remains
`3d6632a2d662deade05b957ad822edd9af6e8eda8c1d7ebca3f098e122760796`.
The following archived members/clauses were read before changing semantics:

| V5 member | Clause and member lines | Governing distinction |
|---|---|---|
| `SOURCE_PINS_UNMODIFIED/War_Rig_V3_D04_Signals_Models_Pricing_Data_Quality_Design_Proposal_V2.md` | D04-02, lines 30-35 | Last completed **and available** bar, as-of time and independently measured input age are distinct. Closed-session stale-data exceptions must be explicit; none is invented here. |
| Same member | D04-07, lines 64-69 | Candidate validity derives from input-event time plus explicit calendar-aware policy, not job/file time. |
| Same member | D04-06, lines 58-62 | Decision-time executable quotes and account/product/session rechecks are separate eligibility/wire concerns, not a requirement that snapshot assessment precede source-session close. |
| `SOURCE_PINS_UNMODIFIED/EXT_G0R_14_UNCHANGED.md` | section 3.2, lines 209-216 | Configured intervals, completed-not-forming rules, signed IANA/DST evidence, explicit session profiles and freshness policies. |
| `SOURCE_PINS_UNMODIFIED/MASTER_V1_8_CORRECTED_UNCHANGED.md` | section 0.5 item 3, line 137; unit 06, line 161; SourceSnapshotLoader, line 266 | Source-specific completed-bar/session status, forming-bar denial and G1R-06-A/B DST/late-calendar checks. |

These governing clauses do **not** restrict snapshot assessment to in-session
decision instants. Session containment applies to the source bar:
`session_open <= bar.start < bar.end <= session_close`. Decision availability
still requires the exact completed bar, expected close, publication, observation,
vintage/revision availability and the selected maximum age. No weekend grace,
stale-data fallback or closed-market entry permission is added.

The defect was the additional `session_open <= replay.at < session_close`
condition. Combined with `bar.end <= replay.at`, it made a session-closing
bar impossible to accept. The coupled Stage B feature-expiry cap at
`session_close` independently recreated that denial after snapshot validation;
it is also removed. Run/context/source expiry remains enforced.

## Exact regression evidence

`tests/v3/test_completed_snapshots.py` covers the reported 00:00-22:00Z bar:
acceptance at close and 1/300/600 seconds afterwards; denial one second before
close, at 601 seconds, while forming, or before any required publication/vintage.
London daily windows crossing spring/fall DST use actual UTC durations of
23/25 hours; wrong signed local-close offsets still deny.

`test_daily_features_and_prediction_remain_valid_after_close_until_data_max_age`
proves actual signed feature loading and common prediction after close, with
independent run-context caps and an audited stale denial.

`test_daily_interval_instrument_registers_by_configuration_only_after_close`
uses the persisted signed SYNTHETIC_6 definition with `intervals=[86400]`
and a full 24-hour source session. Registration happens five seconds after
close; all runtime and plug-in manifest bytes are unchanged during onboarding.
The other five profiles retain their intraday fixtures.

`a7/` and `b4_prediction/` are new signed current-build fixture revisions.
Historical `a5/`, `b2_prediction/`, `b3_prediction/` and sealed A/B gates are
not overwritten. The helper's logical `a5/...` names resolve explicitly to
the current `a7/` revision and its signed intake paths.

The mutation gate restores both the erroneous replay-session restriction and
the erroneous feature-expiry cap, and separately excludes the closing bar.
Each must fail a real assertion; forming-bar and all previous safety mutants
remain enforced.

Reproduce after checkout with `sh tools/run_offline.sh stage_a`. The one-time
developer command `stage_a --prepare-r2-a-01` formats and signs **new** revisions
inside the preflight-verified pinned network-none sandbox; it refuses existing
registration revisions. Normal verification needs no private signing key.
The immutable executed bundle is `evidence/stage_a/r2_a_01/`.

## Minor findings: documented, not silently closed

Typed denial reasons and extraction of shared private parsers into a public
module are deferred to a separate slice; this correction changes neither API.

**EXT-01 requires definition versioning for an existing instrument.**
EXT section 3.1 A/B (lines 184-188) separates immutable definitions from
append-only digest-referencing registry events. Section 3.3, especially
lines 261, 269 and 272, expressly requires new definition versions for
effective configuration changes and resets affected promotion evidence.
This means a new immutable definition digest/version, not mutation of the old
record or inheritance of its authority. The current process-local registry
still rejects a second registration for the same instrument at
`contract_listing_registry.py`'s immutable-instrument guard. Supporting a
properly controlled successor version remains an **open minor**, not a
claimed capability or an implied authority grant.
