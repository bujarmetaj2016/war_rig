# Macro research reproducibility

- Analysis script: `evidence/macro/analyze_core5_macro.py`
- Script commit: `f6dbf1045650c2d296d58baecf0c37248fa0ea29`
- Script SHA-256: `7a8e6afe3d90d40a4b30b4afd7a52ac8b84975d3339bba5a84b0dac9e441690a`
- Verified prompt/hypothesis checksum entries: 8
- Verified V2 reference manifest entries: 374
- Verified V2 trade-result rows: 204
- Static source inventory rows: 64
- Predefined instrument × macro tests: 19; executed: 0
- Self-checks: checksum manifests, required trade columns, sample counts, and the 19-test matrix all passed.
- V2 source files were read only as text. No V2 module was imported or run.
- No network calls, public market downloads, release-calendar downloads, or V2/IG/runtime/database access were made.

## Reproducible commands

```sh
shasum -a 256 -c SHA256SUMS.txt
shasum -a 256 -c reference/MANIFEST.sha256
python3 evidence/macro/analyze_core5_macro.py
shasum -a 256 -c evidence/macro/MANIFEST.sha256
```

The final command checks all pinned filesystem inputs and generated outputs; the manifest excludes itself because a checksum manifest cannot hash its own final bytes.

## FRED/ALFRED download (isolated research job only)

Stage `research/download_macro.py` and the pinned redacted `reference/v2_outcomes/trade_results.csv` (as `trade_results.csv`) in the separate REV4 research job, inject the dedicated research key as `FRED_API_KEY` through that job's secret configuration, and mount a fresh writable `/out`. No pip step is needed:

```sh
python3 download_macro.py --out /out
```

This downloads vintages for DGS2, DFII10, BAMLH0A0HYM2 and DCOILBRENTEU. For the pinned trade export, the inclusive real-time range is 2026-05-06 through 2026-11-09 (the UTC days before the first and last entries). The observation range starts 2024-11-03, 550 calendar days before the first entry to allow 260 observations plus non-trading days and missing values; it ends 2026-11-09. The baseline must still be checked per series. The downloader pages vintage dates first, then requests and merges consecutive windows of at most 1,500 vintage dates. `fred_download_manifest.json` records the series, download times, bounds and derivation, credential-free source URLs, row counts and CSV hashes. After validating them in the research job, stage the artifacts under `reference/history/macro/`. This downloader does not fetch Yahoo Finance prices or release calendars.

Use the vintage in force on the UTC day before entry. An observation first published on the entry date is `UNKNOWN`; an older vintage remains eligible even if a revision was first dated on the entry date. Missing values are not backfilled with subsequent releases.

Offline checks from the repo root (mocked HTTP, no key needed):

```sh
python3 -B -m unittest research.test_download_macro
```

Nine offline downloader tests passed; live API behavior was not verified.
