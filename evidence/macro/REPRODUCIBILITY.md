# Macro research reproducibility

- Analysis script: `evidence/macro/analyze_core5_macro.py`
- Script commit: `ef73c3db900aaccd8f2854721db181c0f3352c91`
- Script SHA-256: `2c1b6067cd1baa69013ee4c13ba729b40ab4eddd615112d2678b8583a55845b3`
- Verified prompt/hypothesis checksum entries: 8
- Verified V2 reference manifest entries: 374
- Verified V2 trade-result rows: 204
- Static source inventory rows: 64
- REV4 matrix: 22 comparisons, including all five event rows.
- Self-checks: checksum manifests, required trade columns, sample counts, and the 22-comparison matrix all passed.
- V2 source files were read only as text. No V2 module was imported or run.
- This worktree made no network calls and did not access V2/IG/runtime/databases. The owner-delivered ALFRED CSVs passed local verification.

## Reproducible commands

```sh
shasum -a 256 -c SHA256SUMS.txt
shasum -a 256 -c reference/MANIFEST.sha256
python3 -B -m unittest discover -s research -p 'test_*.py'
python3 -B -m research.verify_alfred --history reference/history/macro-fred-next --trades reference/v2_outcomes/trade_results.csv
python3 evidence/macro/analyze_core5_macro.py --events-only
shasum -a 256 -c evidence/macro/MANIFEST.sha256
```

The final command checks all pinned filesystem inputs and generated outputs; the manifest excludes itself because a checksum manifest cannot hash its own final bytes.

## FRED/ALFRED download (isolated research job only)

Stage `research/download_macro.py` and the pinned redacted `reference/v2_outcomes/trade_results.csv` (as `trade_results.csv`) in the separate REV4 research job, inject the dedicated research key as `FRED_API_KEY` through that job's secret configuration, and mount a fresh writable `/out`. No pip step is needed:

```sh
python3 download_macro.py --out /out
```

This downloads 12 vintage series: DGS2, DFII10, BAMLH0A0HYM2, DCOILBRENTEU, VIXCLS, VXVCLS, DEXUSEU, DEXJPUS, DEXUSUK, DEXCAUS, DEXSZUS and DEXUSAL. FX manifest rows identify base and quote currencies. For the pinned trade export, the inclusive real-time range is 2026-05-06 through 2026-11-09 (the UTC days before the first and last entries). The observation range starts 2024-11-03, 550 calendar days before the first entry to allow 260 observations plus non-trading days and missing values; it ends 2026-11-09. The baseline must still be checked per series. The downloader pages vintage dates first, then requests and merges consecutive windows of at most 1,500 vintage dates. `fred_download_manifest.json` records the series, download times, bounds and derivation, credential-free source URLs, row counts and CSV hashes. After validating them in the research job, stage the artifacts under `reference/history/macro/`. This downloader does not fetch Yahoo Finance prices or release calendars.

Use the vintage in force on the UTC day before entry. An observation first published on the entry date is `UNKNOWN`; an older vintage remains eligible even if a revision was first dated on the entry date. Missing values are not backfilled with subsequent releases.

Offline checks from the repo root (mocked HTTP, no key needed):

```sh
python3 -B -m unittest research.test_download_macro
```

Nine offline downloader tests passed; live API behavior was not verified.

Download official schedules only in the isolated job, with the verified ALFRED manifest:

```sh
python3 download_release_schedules.py --manifest /inputs/fred_download_manifest.json --out /out
```

Place the schedule output under `reference/history/macro/schedules/`. A schedule download alone does not prove that today's page was available before entry. After reviewing completeness and publication evidence, an `as_known_coverage.json` in that directory may identify inclusive UTC entry `start` and `end` dates, the `download_manifest_sha256`, and `complete_official_page_by_event_type` (a map from each event type to its verified source-page file). Include the full 24-hour forward horizon. Without that review or usable metadata, event comparisons remain UNKNOWN.
The corrected ECB path is `/press/calendars/mgcgc/html/index.en.html`. All five official roots and a disposable isolated acquisition run succeeded; the smoke-test output was not used for trade classification.

### Process deviation

The assistant's earlier live URL probes and acquisition smoke test made network requests from this agent's local macOS environment, not the owner-run research job. They were launched through the Bash tool from `/Users/bujarmetaj/IdeaProjects/war_rig_macro_research` using the local Docker daemon and disposable `python:3.12-slim` containers. The acquisition smoke test mounted `research/` at `/research` and the expanded FRED manifest at `/inputs/fred_download_manifest.json`, both read-only, and wrote to `/tmp/schedules` inside the container. No FRED key was passed; the container was removed and its output was excluded. The final event evaluation used only the separately owner-delivered `reference/history/macro-schedules-retry/`.

The optional `reference/history/macro/price_manifest.json` has a `series` array with `name`, `file`, `source_url`, `downloaded_at_utc`, `close_convention`, `sha256` and `expected_dates` (sorted UTC close dates). The named, hash-pinned CSV uses `close_time_utc,close,complete`, with explicit true/false completion. Use only allow-listed Yahoo sources and verified close times, not midnight inferred from daily labels. Missing series remain UNKNOWN.
For FRED-sourced Brent, VIX, VIX3M and FX, eligible numeric ALFRED vintages are completed observations without a separate session calendar. For the optional `BRENT_FRONT_MONTH` fallback, the price manifest must supply `roll_dates`, `roll_date_documentation`, and `roll_dates_complete: true`; each documented roll-day return is excluded. No futures fallback was needed for the Brent rerun.
