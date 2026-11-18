# Owner decision — Core-5 macro research (17 Nov 2026)

Research evidence: research/core5-macro @ 2fdd7e3981d498ab7783bb81ac643eafe8abe998,
evidence/macro/MANIFEST.sha256 = 12ebf4559badf11714ff6af71eb1092537230ed699721fc3bda6b95bdb3a17ca.

1. Adopted as COMPUTE_AND_LOG_ONLY in V3 (no effect on entry, size or exits):
   - EURUSD ex-EUR and GBPUSD ex-GBP USD-strength basket classifications (WITH / AGAINST / NEUTRAL / UNKNOWN).
   - Event-proximity classification for all five instruments (FOMC, ECB, BoE, US CPI, US NFP).
2. DEMO rule for the EURUSD basket: as in CORE5_V3_MACRO_PROFILE_PROPOSAL.md; the buckets are WITH and AGAINST relative to
   the USD basket, at least 20 V3 trades in each. If the minimum is not reached by the end of the DEMO, the result is
   INCONCLUSIVE and the check stays COMPUTE_AND_LOG_ONLY. No automatic promotion; any gate or size modifier needs a separate owner decision.
3. The V2_PARITY baseline is for comparison only; no V2 macro gate is enabled in V3 by this decision.
4. No ENTRY_GATE or SIZE_MODIFIER is adopted. A replay backtest (REV5 addendum) is in progress; it can only lead to
   further COMPUTE_AND_LOG_ONLY checks, through a separate owner amendment.
5. The process deviation (agent-run network probes) is documented in REPRODUCIBILITY.md; no affected output was used.
