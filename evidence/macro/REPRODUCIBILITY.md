# Macro research reproducibility

- Analysis script: `evidence/macro/analyze_core5_macro.py`
- Script commit: `0b7d14ae6c9196c195a4c5d994119307b3a39193`
- Script SHA-256: `7049fb19d0ab02604fe639e8c8e1f6b54c3f5e08b38f69591603fe8283815924`
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
