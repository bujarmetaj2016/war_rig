# Macro research reproducibility

- Analysis script: `evidence/macro/analyze_core5_macro.py`
- Script commit: `1e97d5b2912456ac9bc3431f9017040312492cbd`
- Script SHA-256: `8755beb77b0946c2fd86e0bce711627ada6ba3ccce05a1fd644ee3581df25b4a`
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

Stage `research/download_macro.py` in the separate REV4 research job, inject the dedicated research key as `FRED_API_KEY` through that job's secret configuration, and mount a fresh writable `/out`. No pip step is needed:

```sh
python3 download_macro.py --out /out
```

This downloads vintages for DGS2, DFII10, BAMLH0A0HYM2 and DCOILBRENTEU. `fred_download_manifest.json` records the series, download times, credential-free source URLs, row counts and CSV hashes. After validating them in the research job, stage the artifacts under `reference/history/macro/`. This downloader does not fetch Yahoo Finance prices or release calendars.

Use the vintage in force on the UTC day before entry. An observation first published on the entry date is `UNKNOWN`; an older vintage remains eligible even if a revision was first dated on the entry date. Missing values are not backfilled with subsequent releases.

Offline checks from the repo root (mocked HTTP, no key needed):

```sh
python3 -B -m unittest research.test_download_macro
```

Five offline downloader tests passed; live API behavior was not verified.
