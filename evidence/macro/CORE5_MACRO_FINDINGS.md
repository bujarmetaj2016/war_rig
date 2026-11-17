# Core-5 macro findings

**Status:** `SOURCE_TRACE_VERIFIED / TRADE_TEST_NOT_VERIFIED`  
**Scope:** Read-only inspection of the owner-supplied V2 snapshot. No V2 code was
imported or executed. These findings describe source behavior, not adopted V3
policy.

## Input verification and availability

The controlling REV4 prompt and both hypotheses pass `shasum -a 256 -c
SHA256SUMS.txt`. The supplied V2 export manifest hash is
`a06ac2de31fcce5436d9c975ea7b0cf872a050a6b7d475e2e4b2f09fdff1a38b`; all 374
listed files pass its checks. Prompt and hypothesis hashes are also repeated in
`evidence/macro/MANIFEST.sha256`. The V5 archive was read in place; it was not
modified.

Owner-provided V2 source, trade-result, and prediction exports are present and
hash-pinned. `reference/history/macro/` and the V2 daily parquet histories are
absent. The separate isolated research job required for allowed public
downloads was not provisioned or attested; no market or release-calendar
downloads were made. Therefore source inventory is verified, but all trade
performance tests remain `NOT_VERIFIED`.

## 1. USD direction and EURUSD/GBPUSD entries

**`VERIFIED_FROM_V2_SOURCE`: V2 can admit a EURUSD/GBPUSD BUY while USD is
strengthening, or a SELL while USD is weakening, if the generated directional
signal and the other entry checks pass. No side-specific USD-direction gate is
present in the traced path.**

The live model uses DXY, VIX, US10Y and (for EURUSD) credit-spread features in
its input vector. Separately, climate is the average of a DXY score and a VIX
score; DXY strength reduces that aggregate for both long and short signals.
`live_inference` calls `_get_signal(prob)` on the model probability, then
suppresses FX signals only when climate is below 40; climate from 40 up to but
not including 60 labels the signal `HALF`, and climate 60 or above labels it
`FULL`. There is no comparison of `signal_direction` with DXY/USD direction.
The source comments' labels are not treated as evidence; the behavior follows
the computation at `backtest_ml/macro_confidence.py:77-91,151-185` and
`backtest_ml/live_inference.py:487-537`.

**Signal-to-order path reviewed:**

1. `execution/governor.py:1254-1295` accepts only a fresh
   `results/live_signal.csv` (default maximum age 75 minutes), then reads its
   rows. At `1365-1372`, only `BULLISH`/`BEARISH` signals continue; active and
   same-day duplicates are skipped.
2. At `1374-1432`, Governor builds a price/ATR/spread snapshot, optionally
   computes FX ATR geometry, otherwise creates fixed-percent TP/SL geometry.
   The following checks are instrument enabled, capital guard, balance/size
   availability, minimum-size precheck, and duplicate exposure/campaign checks
   (`1435-1500`).
3. `evaluate_signal` requires a current price and ATR and checks expiry,
   stop-loss invalidation, risk floor, and minimum reward/risk
   (`governor.py:649-844`). Its macro entry gate is VIX panic only for
   `SP500`/`US500`: missing VIX fails closed and `vix_zscore >= 2.0` rejects
   (`844-882`). That condition does not apply to EURUSD or GBPUSD.
4. The state machine checks displacement, spread/friction, and—if armed—anchor
   touch/reclaim plus another friction check before returning `IMMEDIATE` or
   `RECLAIM` (`888-1045`).
5. Before routing, Governor checks the stop-trading file, enabled status,
   circuit breaker, balance/size, duplicate/campaign eligibility, execution-time
   capital, Gold-only anchor policy, and minimum-size risk (`1656-1718`,
   `1920-2120`). It calls `route_order` with instrument, direction, size, entry,
   SL and TP (`2302-2310`). No check in these traced stages reads USD direction.

Thus a strengthening DXY can lower climate or the model probability, and
climate below 40 can suppress the signal, but neither a BUY nor a SELL is
rejected solely for opposing USD direction. The theme/Sharpe cluster filter can
also suppress one of EURUSD/GBPUSD, but it does not arbitrate USD direction.
This confirms the reported possibility from source; it does not establish how
often it occurred in realized trades.

## 2. Does FX climate HALF/`size_mult` reach actual stake sizing?

**`VERIFIED_FROM_V2_SOURCE`: the climate suppression reaches the entry
decision, but `HALF`/`size_mult=0.5` does not reach the Governor's actual
position-size formula for EURUSD/GBPUSD. It is a display/telemetry value, not a
stake multiplier.**

`live_inference.py:501-508,525-537` writes the climate label and multiplier;
`766-790` includes them in the prediction payload. Governor consumes the
CSV's `final_signal` (`1365-1371`) and creates a signal using its instrument,
direction, prices and grade. Its actual size is computed from balance, grade
risk tier, stop distance and broker point size/value (`governor.py:286-350`).
There is no `size_mult` read in that sizing path. The only multiplier applied
there is the separately named campaign `addon_size_mult`, which is not the
climate multiplier (`1802-1807`).

## 3. Macro inputs that are model features rather than hard gates

**`VERIFIED_FROM_V2_SOURCE`: yes, all listed macro columns in the five
instrument feature modules are model features.** `live_inference._live_prob`
trains the classifier on the declared `feature_cols` and predicts from the
latest feature row (`backtest_ml/live_inference.py:107-155,281-292`). They can
change the model probability but are not individually hard gates. The model
feature lists and calculations are:

| Instrument | Macro model features |
|---|---|
| EURUSD | `dxy_level`, `dxy_5d_roc`, `dxy_zscore`, `us10y_5d_change`, `vix_regime`, `credit_spread` |
| GBPUSD | `dxy_level`, `dxy_5d_roc`, `dxy_zscore`, `vix_regime`, `us10y_5d_change` |
| GOLD/XAUUSD | `dxy_5d_roc`, `dxy_zscore`, `real_yield`, `real_yield_5d_change`, `vix_regime` |
| SP500/US500 | `vix_zscore`, `vix_regime`, `vix_5d_change`, `us10y_5d_change`, `dxy_5d_roc`, `credit_spread` |
| DAX/GER40 | `vix_level`, `vix_regime`, `vix_5d_change`, `vix_zscore`, `dxy_5d_roc`, `dxy_trend`, `dxy_liquidity_vacuum`, `dxy_zscore`, `us10y_level`, `us10y_5d_change`, `real_yield`, `real_yield_5d_change` |

These are not the only macro roles: the separate climate threshold suppresses
EURUSD/GBPUSD and DAX/SP500 directional signals below 40; Gold is explicitly
probability-only. Governor's independent VIX panic gate applies only to
SP500/US500. `CORE5_MACRO_INVENTORY.csv` records each exact feature/output,
source, transform, role, reachability and source hash.

## 4. Forming rows and cross-instrument date alignment

**`VERIFIED_FROM_V2_SOURCE`: latest-row selection and lack of an as-of guard.
`UNCLEAR`: whether a particular historical/live row was actually incomplete or
whether timestamps mismatched on a particular date, because the referenced
parquet data are absent.**

`live_inference._live_prob` selects `feat.iloc[-1]` and labels it with
`feat.index[-1]` (`backtest_ml/live_inference.py:146-148`). Climate selects
`series.iloc[-1]` for each instrument (`475-476`), while `data_date` comes from
the independently computed instrument feature date (`530`). The shared
climate series uses VIX and DXY indexes and does not as-of join to each
instrument date (`macro_confidence.py:151-185`). Feature builders instead
forward-fill to each instrument's own date index and drop timezone metadata
without converting it to UTC. The Governor's daily VIX z-score uses
`closes.iloc[-1]` (`core/market_snapshot.py:213-230`).

None of these paths records a completed-bar flag, publication timestamp,
ALFRED vintage, or source-specific UTC close time. Consequently the code can
select a forming latest row and can mix each instrument's market `data_date`
with a newer/older shared climate date; whether either happened on a particular
run is `UNCLEAR` without the source histories and timestamps. The feature
code also does not enforce the REV4 as-published restrictions.

## Additional source findings

- **`VERIFIED_FROM_V2_SOURCE`:** DXY feature mapping is Yahoo Finance
  `DX-Y.NYB`, VIX is `^VIX`, and the FRED feature series map to DGS10, DFII10,
  and BAMLH0A0HYM2 (`backtest_ml/refresh_data.py:37-48,67-72`).
- **`NOT_FOUND`:** no macro-derived position-management rule was found in the
  Position Manager path. The optional `MarketSnapshot.vix_zscore` field is
  passed as `None` by `run_manager`; snapshot-presence telemetry is not a
  position-size or management decision (`execution/market_data.py:23-69`,
  `execution/position_manager.py:1284-1305`).
- Source paths, exact line ranges and per-file SHA-256 values are in the CSV
  evidence column and the final manifest. A `V2` role is not a V3 approval.
