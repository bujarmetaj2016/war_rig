# Core-5 macro gap table

`PRESENT_AND_ACTING` means the input affects V2's model/gate in the stated role.
`PRESENT_BUT_NOT_ACTING` means it is only a displayed/proposed field or lacks a
selected execution policy. `MISSING` means it is absent from that source/profile.
`V3_ONLY` means it appears in the V3 design profile but not in V2's traced
Core-5 paths.

V2 roles below are from the hash-verified source inventory. V3 comparisons are
from the unmodified V5 archive member
`SOURCE_PINS_UNMODIFIED/EXT_G0R_14_UNCHANGED.md` (member SHA-256
`256ad6bd0d78f30e5e005f4fde64f13021d36286c8512640b2adf91a62153092`).
Although candidate `macro_feature_refs` are present in that design, every
instrument's `macro_freshness_policy_id` is `T2 UNSELECTED; deny` (EXT-G0R-14
lines 657-659); these are not acting runtime inputs.

| Instrument | In V2 | REV4 candidate profile | In V3 design (EXT-G0R-14) |
|---|---|---|---|
| EURUSD | `PRESENT_AND_ACTING`: DXY (three model columns and climate gate), VIX (model + climate gate), DGS10 and HY spread (model only). `PRESENT_BUT_NOT_ACTING`: climate `size_mult` for actual stake. | `MISSING`: USD basket excluding EUR (primary), US-German 2-year spread, VIX, DGS2, Brent and event timing. VIX is already present in V2, but only its climate/model roles apply. Rate spreads have no supplied point-in-time source. | `PRESENT_BUT_NOT_ACTING`: `USD_FX` profile, USD climate/macro velocity and as-published rates/policy references; freshness policy unselected. The exact ex-EUR basket, Brent rule and event rule are not selected. |
| GBPUSD | `PRESENT_AND_ACTING`: DXY (three model columns and climate gate), VIX (model + climate gate), DGS10 (model only). `PRESENT_BUT_NOT_ACTING`: climate `size_mult` for actual stake. | `MISSING`: USD basket excluding GBP (primary), US-UK 2-year spread, DGS2, Brent and event timing. VIX is already present in V2, but not a directional gate. | `PRESENT_BUT_NOT_ACTING`: `USD_FX` profile, USD climate/macro velocity, as-published rates/policy and liquidity/calendar-risk references; freshness policy unselected. Exact ex-GBP basket, Brent and event rules are not selected. |
| GOLD/XAUUSD | `PRESENT_AND_ACTING`: DXY, DFII10 real yield and VIX as model features. `PRESENT_BUT_NOT_ACTING`: climate is computed/displayed but does not gate or size Gold; no Governor VIX gate for Gold. | `MISSING`: REV4-defined real-yield/USD/VIX tests, DGS2 and event timing. `T10YIE` is explicitly not tested. No USD-basket outcome can be tested without the permitted histories. | `PRESENT_BUT_NOT_ACTING`: `GOLD_MACRO` profile with DXY, yields/real yields and volatility references; freshness policy unselected. |
| SP500/US500 | `PRESENT_AND_ACTING`: VIX, DGS10, DXY and HY-spread model features; climate gate; separate Governor VIX panic gate (missing VIX fails closed; default z-score threshold 2). `PRESENT_BUT_NOT_ACTING`: climate `size_mult` for actual stake. | `MISSING`: VIX/VIX3M risk-off and HY-spread tests. DGS10 change is a candidate but has no separately specified Part 4 trade-classification rule; US500-vs-DXY is explicitly not tested. | `PRESENT_BUT_NOT_ACTING`: `US_EQUITY` profile with VIX, rates and credit PIT references; freshness policy unselected. VIX/VIX3M term structure is not an active profile. |
| GER40/DAX | `PRESENT_AND_ACTING`: VIX, DXY, DGS10 and DFII10 as model features; climate gate. `PRESENT_BUT_NOT_ACTING`: climate `size_mult` for actual stake. | `MISSING`: REV4 risk-off, EURUSD exporter-channel, and Brent tests. Bund 10-year and prior US500 session are candidate inputs but explicitly not tested by the fixed rules. | `PRESENT_BUT_NOT_ACTING`: `EQUITY_STRUCT` profile with VIX/DXY/US-yield references; freshness policy unselected. Bund, EURUSD, prior-US500 and Brent rules are not selected. |

**Cross-cutting:** event proximity is a V3 calendar proposal, not a V2 macro
input, and no official release schedule was downloaded. Candidate policy and
roles remain owner proposals; nothing in this comparison authorizes an
executable V3 gate.

**Continuation:** verified ALFRED inputs now support partial descriptive results
and two unconfirmed exploratory EURUSD candidates (DGS2 and Brent spot). Here `MISSING` still
describes the V2 or V3 profile, not delivery of a historical research series.
See the [trade-test report](CORE5_MACRO_TRADE_TEST.md).
