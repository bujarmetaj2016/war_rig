#!/usr/bin/env python3
"""Reproduce the verified Core-5 source inventory and input-availability audit."""

from __future__ import annotations

import csv
import hashlib
import subprocess
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evidence" / "macro"
V2 = "reference/v2_snapshot"
REF_MANIFEST_SHA256 = "a06ac2de31fcce5436d9c975ea7b0cf872a050a6b7d475e2e4b2f09fdff1a38b"
DESIGN_ZIP = "design/War_Rig_V3_Complete_Offline_Design_V5_MSB_REVIEW_CANDIDATE_20261113.zip"
DESIGN_MEMBER = "SOURCE_PINS_UNMODIFIED/EXT_G0R_14_UNCHANGED.md"
TRADE_FILE = "reference/v2_outcomes/trade_results.csv"

INVENTORY_FIELDS = (
    "instrument",
    "input_name",
    "source",
    "transform",
    "timing",
    "role",
    "reaches_entry_decision",
    "reaches_position_size",
    "evidence",
)

SOURCE_MAP = {
    "DXY": ("Yahoo Finance ticker DX-Y.NYB", "backtest_ml/refresh_data.py:37-48"),
    "VIX": ("Yahoo Finance ticker ^VIX", "backtest_ml/refresh_data.py:37-48"),
    "DGS10": ("FRED series DGS10", "backtest_ml/refresh_data.py:67-72"),
    "DFII10": ("FRED series DFII10", "backtest_ml/refresh_data.py:67-72"),
    "BAMLH0A0HYM2": (
        "FRED series BAMLH0A0HYM2",
        "backtest_ml/refresh_data.py:67-72",
    ),
}

FEATURES = {
    "EURUSD": [
        ("dxy_level", "DXY", "DXY close level.", "114-134"),
        ("dxy_5d_roc", "DXY", "(DXY[t] - DXY[t-5]) / DXY[t-5].", "126-130"),
        ("dxy_zscore", "DXY", "5-day DXY ROC / rolling 20-observation std (not demeaned).", "126-130"),
        ("us10y_5d_change", "DGS10", "DGS10[t] - DGS10[t-5], percentage-point series units.", "118-131"),
        ("vix_regime", "VIX", "VIX close bucketed at 15/20/25/30 into labels 0..4.", "115-133"),
        ("credit_spread", "BAMLH0A0HYM2", "FRED high-yield spread level, forward-filled.", "122-134"),
    ],
    "GBPUSD": [
        ("dxy_level", "DXY", "DXY close level.", "113-128"),
        ("dxy_5d_roc", "DXY", "(DXY[t] - DXY[t-5]) / DXY[t-5].", "121-125"),
        ("dxy_zscore", "DXY", "5-day DXY ROC / rolling 20-observation std (not demeaned).", "121-125"),
        ("vix_regime", "VIX", "VIX close bucketed at 15/20/25/30 into labels 0..4.", "115-128"),
        ("us10y_5d_change", "DGS10", "DGS10[t] - DGS10[t-5], percentage-point series units.", "117-128"),
    ],
    "GOLD": [
        ("dxy_5d_roc", "DXY", "(DXY[t] - DXY[t-5]) / DXY[t-5].", "173-177"),
        ("dxy_zscore", "DXY", "5-day DXY ROC / rolling 20-observation std (not demeaned).", "173-177"),
        ("real_yield", "DFII10", "DFII10 real-yield level, forward-filled.", "161-180"),
        ("real_yield_5d_change", "DFII10", "DFII10[t] - DFII10[t-5], percentage-point series units.", "179-181"),
        ("vix_regime", "VIX", "VIX close bucketed at 15/20/25/30 into labels 0..4.", "167-188"),
    ],
    "SP500": [
        ("vix_zscore", "VIX", "(VIX - rolling mean20) / rolling std20.", "171-179"),
        ("vix_regime", "VIX", "VIX close bucketed at 15/20/25/30 into labels 0..4.", "171-179"),
        ("vix_5d_change", "VIX", "VIX[t] - VIX[t-5].", "171-180"),
        ("us10y_5d_change", "DGS10", "DGS10[t] - DGS10[t-5], percentage-point series units.", "155-183"),
        ("dxy_5d_roc", "DXY", "(DXY[t] - DXY[t-5]) / DXY[t-5].", "151-187"),
        ("credit_spread", "BAMLH0A0HYM2", "FRED high-yield spread level, forward-filled.", "162-190"),
    ],
    "DAX": [
        ("vix_level", "VIX", "VIX close level.", "173-180"),
        ("vix_regime", "VIX", "VIX close bucketed at 15/20/25/30 into labels 0..4.", "173-179"),
        ("vix_5d_change", "VIX", "VIX[t] - VIX[t-5].", "173-180"),
        ("vix_zscore", "VIX", "(VIX - rolling mean20) / rolling std20.", "182-184"),
        ("dxy_5d_roc", "DXY", "(DXY[t] - DXY[t-5]) / DXY[t-5].", "186-194"),
        ("dxy_trend", "DXY", "sign(DXY 5-day ROC).", "186-190"),
        ("dxy_liquidity_vacuum", "DXY", "1 when DXY 5-day ROC > 0.008, else 0.", "186-190"),
        ("dxy_zscore", "DXY", "5-day DXY ROC / rolling 20-observation std (not demeaned).", "192-194"),
        ("us10y_level", "DGS10", "FRED DGS10 level, forward-filled.", "159-198"),
        ("us10y_5d_change", "DGS10", "DGS10[t] - DGS10[t-5], percentage-point series units.", "159-198"),
        ("real_yield", "DFII10", "FRED DFII10 real-yield level, forward-filled.", "165-200"),
        ("real_yield_5d_change", "DFII10", "DFII10[t] - DFII10[t-5], percentage-point series units.", "165-200"),
    ],
}

FEATURE_FILES = {
    "EURUSD": "backtest_ml/eurusd_v2_features.py",
    "GBPUSD": "backtest_ml/gbpusd_v2_features.py",
    "GOLD": "backtest_ml/gold_v2_features.py",
    "SP500": "backtest_ml/sp500_v2_features.py",
    "DAX": "backtest_ml/dax_v2_features.py",
}

TESTS = [
    ("EURUSD", "USD strength basket excluding EUR", "PRIMARY"),
    ("EURUSD", "VIX risk-off", "EXPLORATORY"),
    ("EURUSD", "Brent spot oil", "EXPLORATORY"),
    ("EURUSD", "US 2-year yield (DGS2)", "EXPLORATORY"),
    ("EURUSD", "Scheduled-event proximity", "EXPLORATORY"),
    ("GBPUSD", "USD strength basket excluding GBP", "PRIMARY"),
    ("GBPUSD", "VIX risk-off", "EXPLORATORY"),
    ("GBPUSD", "Brent spot oil", "EXPLORATORY"),
    ("GBPUSD", "US 2-year yield (DGS2)", "EXPLORATORY"),
    ("GBPUSD", "Scheduled-event proximity", "EXPLORATORY"),
    ("GOLD", "US 10-year real yield (DFII10)", "EXPLORATORY"),
    ("GOLD", "USD strength basket", "EXPLORATORY"),
    ("GOLD", "VIX risk-off", "EXPLORATORY"),
    ("GOLD", "US 2-year yield (DGS2)", "EXPLORATORY"),
    ("SP500", "VIX / VIX3M risk-off", "EXPLORATORY"),
    ("SP500", "High-yield spread (BAMLH0A0HYM2)", "EXPLORATORY"),
    ("DAX", "VIX risk-off", "EXPLORATORY"),
    ("DAX", "EURUSD 10-day change", "EXPLORATORY"),
    ("DAX", "Brent spot oil", "EXPLORATORY"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def cite(path: str, line_range: str) -> str:
    full_path = ROOT / path
    return f"{path}:{line_range} SHA-256={sha256(full_path)}"


def verify_checksum_list(path: Path) -> list[tuple[str, str]]:
    entries = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ValueError(f"Malformed checksum row in {relative(path)}: {line}")
        expected, file_name = parts[0], parts[-1]
        actual = sha256(ROOT / file_name)
        if actual != expected:
            raise ValueError(f"Checksum mismatch: {file_name}")
        entries.append((expected, file_name))
    return entries


def source_text(series: str) -> tuple[str, str]:
    source, location = SOURCE_MAP[series]
    return source, cite(f"{V2}/{location.split(':')[0]}", location.split(":")[1])


def add_inventory_row(rows: list[dict[str, str]], **row: str) -> None:
    if tuple(row) != INVENTORY_FIELDS:
        row = {field: row[field] for field in INVENTORY_FIELDS}
    rows.append(row)


def build_inventory() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    feature_timing = (
        "Daily parquet index; loader parses timestamps then drops timezone without "
        "UTC conversion; macro values reindex/forward-fill to each instrument index. "
        "No completed-bar, publication-time, ALFRED-vintage, or as-of guard; actual "
        "close convention and observation availability are unknown."
    )
    live_inference = cite(
        f"{V2}/backtest_ml/live_inference.py", "107-155,281-292"
    )

    for instrument, features in FEATURES.items():
        feature_path = f"{V2}/{FEATURE_FILES[instrument]}"
        for name, series, transform, line_range in features:
            source, source_citation = source_text(series)
            add_inventory_row(
                rows,
                instrument=instrument,
                input_name=name,
                source=source,
                transform=transform,
                timing=feature_timing,
                role="MODEL_FEATURE",
                reaches_entry_decision="YES (through model probability; not a hard gate)",
                reaches_position_size="NO",
                evidence=(
                    f"{cite(feature_path, line_range)}; {live_inference}; "
                    f"{source_citation}"
                ),
            )

    climate_cite = (
        cite(f"{V2}/backtest_ml/macro_confidence.py", "138-185")
        + "; "
        + cite(f"{V2}/backtest_ml/live_inference.py", "471-537,766-790")
    )
    for instrument in FEATURES:
        climate_role = "DISPLAY_ONLY" if instrument == "GOLD" else "ENTRY_GATE"
        reaches_entry = "NO" if instrument == "GOLD" else "YES"
        for name, source, transform in (
            (
                "vix_zscore",
                "Yahoo Finance ticker ^VIX",
                "20-row z-score of VIX close; NaN/zero std filled as 0; score is "
                "50 + 25*z for GOLD, otherwise 50 - 25*z, clamped to 0..100.",
            ),
            (
                "dxy_zscore",
                "Yahoo Finance ticker DX-Y.NYB",
                "5-day DXY simple ROC, then rolling 20-row demeaned z-score; NaN/"
                "zero std filled as 0; score is 50 - 25*z, clamped to 0..100.",
            ),
            (
                "climate",
                "Yahoo ^VIX + DX-Y.NYB",
                "Arithmetic mean of VIX and DXY scores. For EURUSD/GBPUSD a "
                "directional signal is suppressed below 40; 40 <= climate < 60 "
                "labels HALF; for DAX/SP500 a signal is suppressed below 40. "
                "GOLD climate does not gate its signal.",
            ),
        ):
            add_inventory_row(
                rows,
                instrument=instrument,
                input_name=name,
                source=source,
                transform=transform,
                timing=(
                    "Shared daily VIX/DXY series; latest climate row selected by "
                    "live_inference with iloc[-1], independently of each instrument "
                    "data_date; no completed-bar or vintage check."
                ),
                role=climate_role,
                reaches_entry_decision=reaches_entry,
                reaches_position_size="NO",
                evidence=climate_cite
                + "; "
                + cite(
                    f"{V2}/backtest_ml/refresh_data.py",
                    "37-48",
                ),
            )
        add_inventory_row(
            rows,
            instrument=instrument,
            input_name="size_mult",
            source="Derived from climate / signal output",
            transform=(
                "FX: 0.5 for 40 <= climate < 60, 1.0 at climate >= 60, 0.0 "
                "otherwise; indices: 1.0 or 0.0; GOLD: 1.0 for directional signal. "
                "Stored/displayed, not applied by Governor sizing."
            ),
            timing="Generated with live inference row; persisted to CSV/ML telemetry.",
            role="DISPLAY_ONLY",
            reaches_entry_decision="NO (the separate final_signal suppression does)",
            reaches_position_size="NO",
            evidence=(
                cite(f"{V2}/backtest_ml/live_inference.py", "487-537,766-790")
                + "; "
                + cite(f"{V2}/execution/governor.py", "1365-1371,286-350")
            ),
        )

    for instrument in FEATURES:
        role = "ENTRY_GATE" if instrument == "SP500" else "DISPLAY_ONLY"
        reaches_entry = "YES" if instrument == "SP500" else "NO"
        add_inventory_row(
            rows,
            instrument=instrument,
            input_name="MarketSnapshot.vix_zscore (Governor)",
            source="Yahoo Finance ticker ^VIX",
            transform=(
                "Z = (last daily Close - mean(last up-to-252 daily Closes)) / "
                "sample std; history request is 1 year; window may contract to "
                "20 rows; SP500/US500 denied when unavailable or z >= 2.0 by default."
            ),
            timing=(
                "yfinance daily history; current value is closes.iloc[-1]; no "
                "completed-bar/as-of validation. The same snapshot field is logged "
                "for other instruments but does not gate them."
            ),
            role=role,
            reaches_entry_decision=reaches_entry,
            reaches_position_size="NO",
            evidence=(
                cite(f"{V2}/core/market_snapshot.py", "213-230")
                + "; "
                + cite(f"{V2}/execution/governor.py", "615-646,844-882")
            ),
        )
        add_inventory_row(
            rows,
            instrument=instrument,
            input_name="MarketSnapshot.vix_zscore (Manager)",
            source="Optional upstream ^VIX value; run_manager passes None",
            transform=(
                "Optional snapshot metadata only. run_manager passes None; "
                "snapshot presence is logged, and position-management decisions "
                "do not read this field."
            ),
            timing="No Manager macro computation or as-of rule; explicit None in run_manager.",
            role="COMPUTED_UNUSED",
            reaches_entry_decision="NO",
            reaches_position_size="NO",
            evidence=(
                cite(f"{V2}/execution/market_data.py", "23-69")
                + "; "
                + cite(f"{V2}/execution/position_manager.py", "1284-1305")
            ),
        )

    return rows


def read_trade_summary() -> tuple[list[dict[str, str]], Counter, dict[str, Counter]]:
    with (ROOT / TRADE_FILE).open(newline="") as stream:
        trades = list(csv.DictReader(stream))
    labels = Counter(row.get("final_outcome_label", "") for row in trades)
    per_instrument: dict[str, Counter] = defaultdict(Counter)
    for row in trades:
        per_instrument[row.get("instrument", "UNKNOWN")][
            row.get("final_outcome_label", "UNKNOWN")
        ] += 1
    required = ("instrument", "direction", "fill_time", "exit_r", "final_outcome_label")
    if any(not (row.get(field) or "").strip() for row in trades for field in required):
        raise ValueError("trade_results.csv has missing required trade fields")
    return trades, labels, per_instrument


def current_script_commit() -> str:
    script_path = relative(Path(__file__))
    commit = subprocess.run(
        ["git", "-C", str(ROOT), "log", "-1", "--format=%H", "--", script_path],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not commit:
        raise RuntimeError("Commit the analysis script before generating final outputs.")
    return commit


def write_inventory(rows: list[dict[str, str]]) -> None:
    path = OUT / "CORE5_MACRO_INVENTORY.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=INVENTORY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_trade_test(
    labels: Counter,
    per_instrument: dict[str, Counter],
    script_commit: str,
    prediction_entries: list[tuple[str, str]],
) -> None:
    strict_total = labels["WIN"] + labels["LOSS"]
    lines = [
        "# Core-5 macro trade test",
        "",
        "**Status: `NOT_VERIFIED` — no trade/macro classifications or performance tests were run.**",
        "",
        "## Availability and execution status",
        "",
        f"- Predefined instrument × macro tests: **{len(TESTS)}**; executed: **0**; "
        "statistical recommendations: **0**.",
        "- `reference/history/macro/` is absent/empty. The allowed separate research "
        "container/job was not provisioned or attested, so no public downloads were made.",
        "- The verified V2 exports provide 204 trade-result rows: "
        f"{strict_total} strict WIN/LOSS labels ({labels['WIN']} WIN, {labels['LOSS']} "
        f"LOSS) and {labels['SCRATCH']} SCRATCH outcomes. SCRATCH records are not "
        "recast as WIN or LOSS.",
        f"- Analysis script commit: `{script_commit}`.",
        f"- Trade-results input: `{TRADE_FILE}` SHA-256 "
        f"`{sha256(ROOT / TRADE_FILE)}`.",
        "- V2 reference manifest SHA-256 "
        f"`{sha256(ROOT / 'reference/MANIFEST.sha256')}`.",
        "- Verified prediction exports (integrity inputs only; not used for trade "
        "counts or tests):",
    ]
    if prediction_entries:
        lines.extend(
            f"  - `{path}` SHA-256 `{digest}`"
            for digest, path in prediction_entries
        )
    else:
        lines.append("  - `NOT_PROVIDED`")
    lines.extend(
        [
            "- The five instruments have the following full strict-label counts before "
            "any macro availability exclusions:",
            "",
            "| Instrument | WIN | LOSS | Strict WIN/LOSS n |",
            "|---|---:|---:|---:|",
        ]
    )
    for instrument in ("EURUSD", "GBPUSD", "GOLD", "SP500", "DAX"):
        counts = per_instrument[instrument]
        lines.append(
            f"| {instrument} | {counts['WIN']} | {counts['LOSS']} | "
            f"{counts['WIN'] + counts['LOSS']} |"
        )
    lines.extend(
        [
            "",
            "The GBPUSD (n=19), GOLD (n=18), and SP500 (n=17) totals are already "
            "below the fixed 20-trade bucket threshold before any WITH/AGAINST split. "
            "EURUSD and DAX still require at least 20 usable trades in both buckets.",
            "",
            "## Fixed test matrix",
            "",
            "| Instrument | Macro | Preregistered status | Result |",
            "|---|---|---|---|",
        ]
    )
    for instrument, macro, kind in TESTS:
        lines.append(f"| {instrument} | {macro} | {kind} | `NOT_VERIFIED` |")
    lines.extend(
        [
            "",
            "## Frozen rules and unavailable observations",
            "",
            "No rule was changed after reviewing outcomes. If data are later provisioned "
            "in the permitted isolated job, apply REV4 exactly: `S` is the sum of ten "
            "daily log returns for price/FX/USD/oil series, or latest minus ten "
            "observations earlier in percentage points for yields/spreads; `sigma` is "
            "the standard deviation of that S over the trailing 250 observations. "
            "Fewer than 250 valid observations, missing timestamps, or unavailable "
            "as-published FRED/ALFRED vintages means UNKNOWN. USD_UP/DOWN requires "
            "S > +0.5 sigma / S < -0.5 sigma; risk-off is VIX/VIX3M > 1 or VIX > "
            "1.25 times its trailing 20-day median. All remaining signs, headwinds, "
            "weekly bootstrap, and decision thresholds are those in the controlling "
            "REV4 prompt.",
            "",
            "- Every trade–macro pair is currently `UNKNOWN`; no WITH/AGAINST/NEUTRAL "
            "bucket, win rate, mean/total R, weekly bootstrap CI, removal fraction, or "
            "driver-agreement statistic can be calculated.",
            "- Price-series daily close conventions and UTC close timestamps: "
            "`UNKNOWN` (no series downloaded).",
            "- FRED observation publication timestamps and ALFRED vintages: "
            "`UNKNOWN` (no vintage data supplied/downloaded).",
            "- Official Fed, ECB, BoE, and BLS release dates/times, time zones, and "
            "page publication/update dates: `UNKNOWN` (no schedule pages downloaded).",
            "- Macro histories, price histories, release schedules, and their hashes: "
            "`NOT_PROVIDED`; no future or unpublished values were substituted.",
            "- These unavailable market/release inputs have no hashes because they "
            "were not supplied or downloaded.",
            "- US–German/US–UK 2-year spreads remain "
            "`NOT_TESTED_DATA_UNAVAILABLE`; other candidate drivers without a fixed "
            "REV4 rule remain `NOT_TESTED`.",
            "",
            "There are 19 predefined tests; multiple comparisons would produce chance "
            "differences even if all drivers had no effect. These data do not support "
            "any gate recommendation. V2's verified closed-trade sample is small, and "
            "historical removal of losing trades would only be a partial counterfactual, "
            "not a measured future gain. No macro gate is executable V3 policy without "
            "explicit owner adoption and forward DEMO validation.",
            "",
        ]
    )
    (OUT / "CORE5_MACRO_TRADE_TEST.md").write_text("\n".join(lines))


def write_reproducibility(
    prompt_entries: list[tuple[str, str]],
    reference_entries: list[tuple[str, str]],
    rows: list[dict[str, str]],
    labels: Counter,
    commit: str,
) -> None:
    script_path = relative(Path(__file__))
    content = [
        "# Macro research reproducibility",
        "",
        f"- Analysis script: `{script_path}`",
        f"- Script commit: `{commit}`",
        f"- Script SHA-256: `{sha256(Path(__file__))}`",
        f"- Verified prompt/hypothesis checksum entries: {len(prompt_entries)}",
        f"- Verified V2 reference manifest entries: {len(reference_entries)}",
        f"- Verified V2 trade-result rows: {labels['WIN'] + labels['LOSS'] + labels['SCRATCH']}",
        f"- Static source inventory rows: {len(rows)}",
        f"- Predefined instrument × macro tests: {len(TESTS)}; executed: 0",
        "- Self-checks: checksum manifests, required trade columns, sample counts, "
        "and the 19-test matrix all passed.",
        "- V2 source files were read only as text. No V2 module was imported or run.",
        "- No network calls, public market downloads, release-calendar downloads, "
        "or V2/IG/runtime/database access were made.",
        "",
        "## Reproducible commands",
        "",
        "```sh",
        "shasum -a 256 -c SHA256SUMS.txt",
        "shasum -a 256 -c reference/MANIFEST.sha256",
        "python3 evidence/macro/analyze_core5_macro.py",
        "shasum -a 256 -c evidence/macro/MANIFEST.sha256",
        "```",
        "",
        "The final command checks all pinned filesystem inputs and generated outputs; "
        "the manifest excludes itself because a checksum manifest cannot hash its own "
        "final bytes.",
        "",
    ]
    (OUT / "REPRODUCIBILITY.md").write_text("\n".join(content))


def write_manifest(
    prompt_entries: list[tuple[str, str]],
    reference_entries: list[tuple[str, str]],
    commit: str,
) -> None:
    script_path = relative(Path(__file__))
    design_path = ROOT / DESIGN_ZIP
    with zipfile.ZipFile(design_path) as archive:
        member_bytes = archive.read(DESIGN_MEMBER)
    member_hash = hashlib.sha256(member_bytes).hexdigest()

    entries: dict[str, str] = {}
    for digest, path in prompt_entries + reference_entries:
        entries[path] = digest
    entries["SHA256SUMS.txt"] = sha256(ROOT / "SHA256SUMS.txt")
    entries["reference/MANIFEST.sha256"] = sha256(
        ROOT / "reference/MANIFEST.sha256"
    )
    entries[DESIGN_ZIP] = sha256(design_path)

    output_paths = [
        "evidence/macro/CORE5_MACRO_INVENTORY.csv",
        "evidence/macro/CORE5_MACRO_FINDINGS.md",
        "evidence/macro/CORE5_MACRO_GAP.md",
        "evidence/macro/CORE5_MACRO_TRADE_TEST.md",
        "evidence/macro/CORE5_V3_MACRO_PROFILE_PROPOSAL.md",
        "evidence/macro/REPRODUCIBILITY.md",
        script_path,
    ]
    output_entries = {path: sha256(ROOT / path) for path in output_paths}

    lines = [
        f"# Script commit {commit}",
        f"# V5 EXT-G0R-14 archive-member SHA-256 {member_hash} ({DESIGN_MEMBER})",
        "# Filesystem inputs and outputs follow in sha256sum-compatible format.",
    ]
    lines.extend(f"{digest}  {path}" for path, digest in sorted(entries.items()))
    lines.extend(
        f"{digest}  {path}" for path, digest in sorted(output_entries.items())
    )
    (OUT / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    prompt_entries = verify_checksum_list(ROOT / "SHA256SUMS.txt")
    reference_manifest = ROOT / "reference" / "MANIFEST.sha256"
    if sha256(reference_manifest) != REF_MANIFEST_SHA256:
        raise ValueError("Owner-supplied V2 reference manifest hash mismatch")
    reference_entries = verify_checksum_list(reference_manifest)
    if len(prompt_entries) != 8:
        raise ValueError(f"Expected 8 trusted prompt/hypothesis pins, got {len(prompt_entries)}")
    if len(reference_entries) != 374:
        raise ValueError(f"Expected 374 V2 reference pins, got {len(reference_entries)}")

    trades, labels, per_instrument = read_trade_summary()
    if len(trades) != 204 or labels != Counter({"WIN": 128, "LOSS": 71, "SCRATCH": 5}):
        raise ValueError("Verified trade-result summary changed; re-audit before proceeding")
    if len(TESTS) != 19 or len({instrument for instrument, _, _ in TESTS}) != 5:
        raise ValueError("Fixed test matrix is incomplete")

    rows = build_inventory()
    commit = current_script_commit()
    prediction_entries = [
        (digest, path)
        for digest, path in reference_entries
        if path.startswith("reference/v2_predictions/")
    ]
    write_inventory(rows)
    write_trade_test(labels, per_instrument, commit, prediction_entries)
    write_reproducibility(prompt_entries, reference_entries, rows, labels, commit)
    write_manifest(prompt_entries, reference_entries, commit)
    print(
        f"OK: {len(prompt_entries)} prompt pins, {len(reference_entries)} reference "
        f"pins, {len(trades)} trade rows, {len(rows)} inventory rows, "
        f"{len(TESTS)} tests defined / 0 run."
    )


if __name__ == "__main__":
    main()
