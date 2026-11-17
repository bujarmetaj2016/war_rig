# Core-5 V3 macro profile proposal

**Status: `PROPOSAL_ONLY / OWNER_SELECTION_REQUIRED`.** No entry gate is
recommended by the trade results because the fixed tests could not run. The V5
design's macro freshness policies are unselected and deny; this report does
not select or activate them.

| Instrument | Candidate inputs and proposed role | Evidence status / rationale |
|---|---|---|
| EURUSD | USD-strength basket excluding EUR — `MODEL_FEATURE`; VIX, US 2-year yield and Brent — `LOG_ONLY`; US-German 2-year spread — `LOG_ONLY` pending a point-in-time source. | USD basket is the preregistered primary hypothesis. Existing V2 DXY is circular for EURUSD and has no direction-specific gate; its macro test is `NOT_VERIFIED`. Do not promote to `ENTRY_GATE` or `SIZE_MODIFIER`. |
| GBPUSD | USD-strength basket excluding GBP — `MODEL_FEATURE`; VIX, US 2-year yield and Brent — `LOG_ONLY`; US-UK 2-year spread — `LOG_ONLY` pending a point-in-time source. | Primary USD-basket test is `NOT_VERIFIED`; existing V2 DXY overlaps GBPUSD. No evidence supports a directional entry gate or actual stake modifier. |
| GOLD/XAUUSD | DFII10 real yield, independent USD strength and VIX — `MODEL_FEATURE`; event proximity and DGS2 — `LOG_ONLY`. | Exploratory tests are `NOT_VERIFIED`; the hypothesis itself notes the real-yield relation weakened after 2022. `T10YIE` remains not tested. |
| SP500/US500 | VIX level/VIX3M term structure, DGS10 change, and high-yield spread — `MODEL_FEATURE`; scheduled-event proximity — `LOG_ONLY`. | Tests are `NOT_VERIFIED`; DGS10 has no fixed Part 4 trade-classification rule. V2's VIX panic gate is documented historical behavior only and is not carried into V3 by this proposal. |
| GER40/DAX | VIX, EURUSD and Brent — `MODEL_FEATURE`; Bund yield, prior US500 session and event proximity — `LOG_ONLY` pending data/rules. | The three fixed exploratory tests are `NOT_VERIFIED`; Bund and prior-US500 are expressly not tested. Treat EURUSD's exporter sign as regime-dependent. |

**No `ENTRY_GATE` or `SIZE_MODIFIER` is proposed from current evidence.** Every
input above remains a candidate for an owner-selected profile and frozen
forward/DEMO validation. If adopted later, it must use completed observations,
as-published FRED/ALFRED vintages, explicit source close conventions and
per-instrument freshness policies. Unknown or late data must not silently
become a neutral pass. The event window is a calendar/timing observation, not a
directional signal.

V2's climate HALF value did not scale actual FX stake in Governor. V3 must not
inherit that label as a `SIZE_MODIFIER` without an explicit owner decision and
an end-to-end sizing test. Historical removal of losing trades is not an
estimate of future gains; capital use and later signal selection change under
any gate.
