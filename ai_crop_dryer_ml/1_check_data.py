"""Inspect the discovered dryer CSV without changing its source data."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_DIR / "data" / "raw" / "smart_dryer_combined_dataset.csv"
DEFAULT_REPORT = PROJECT_DIR / "reports" / "data_quality.md"
DEFAULT_ANOMALY_REPORT = PROJECT_DIR / "reports" / "anomaly_review.csv"
WEIGHT_JUMP_SCREEN_KG = 0.05
UNVERIFIED_INTERVALS = (
    ("00:59:00", "00:59:40"),
    ("01:07:40", "01:08:00"),
    ("01:11:40", "01:13:10"),
    ("01:19:20", "01:19:30"),
)


def _format_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_None._"
    return frame.to_markdown(index=False)


def inspect_csv(
    csv_path: Path,
    timestamp_column: str,
    report_path: Path,
    anomaly_report_path: Path,
) -> dict[str, object]:
    data = pd.read_csv(csv_path)
    if timestamp_column not in data.columns:
        raise ValueError(
            f"Timestamp column {timestamp_column!r} was not found. "
            f"Observed columns: {list(data.columns)}"
        )

    parsed_time = pd.to_datetime(data[timestamp_column], errors="coerce")
    valid_time = parsed_time.dropna()
    ordered_times = valid_time.sort_values().drop_duplicates()
    intervals = ordered_times.diff().dropna().dt.total_seconds()
    cadence = float(intervals.median()) if not intervals.empty else None
    gaps = (
        intervals[intervals > cadence * 1.5]
        if cadence is not None and cadence > 0
        else intervals.iloc[0:0]
    )
    gap_rows = []
    for end_time, seconds in gaps.items():
        end_position = ordered_times.searchsorted(valid_time.loc[end_time])
        start_time = ordered_times.iloc[end_position - 1]
        missing_ticks = max(round(seconds / cadence) - 1, 0) if cadence else 0
        gap_rows.append(
            {
                "From": start_time,
                "To": ordered_times.iloc[end_position],
                "Interval (s)": seconds,
                "Missing expected ticks": missing_ticks,
            }
        )

    numeric_columns = data.select_dtypes(include="number")
    numeric_summary = numeric_columns.describe().transpose().reset_index()
    numeric_summary = numeric_summary.rename(columns={"index": "Column"})
    missing = data.isna().sum().rename_axis("Column").reset_index(name="Missing")
    dtypes = pd.DataFrame(
        {"Column": data.columns, "CSV dtype": [str(dtype) for dtype in data.dtypes]}
    )
    unit_interpretations = {
        timestamp_column: (
            "Timestamp",
            "CSV timestamp; timezone awareness is reported separately.",
        ),
        "temperature": (
            "°C (interpreted)",
            "Consistent with the project notes/specification; not encoded in CSV metadata.",
        ),
        "humidity": (
            "% RH (interpreted)",
            "Consistent with the project notes/specification; not encoded in CSV metadata.",
        ),
        "weight_kg": (
            "kg (header-declared)",
            "Candidate weight signal; anomalous values require investigation.",
        ),
        "weight_grams": (
            "g (header-declared)",
            "Compare to kilograms only after unit conversion and timestamp alignment.",
        ),
    }
    schema_rows = [
        {
            "Column": column,
            "Unit / interpretation": unit_interpretations.get(
                column,
                ("Not identified from the column name", "Confirm from sensor documentation."),
            )[0],
            "Evidence / caveat": unit_interpretations.get(
                column,
                ("Not identified from the column name", "Confirm from sensor documentation."),
            )[1],
        }
        for column in data.columns
    ]

    weights = {}
    for column in ("weight_kg", "weight_grams"):
        if column in data.columns:
            weights[column] = pd.to_numeric(data[column], errors="coerce")

    negative_rows = pd.DataFrame()
    jump_rows = pd.DataFrame()
    consistency: dict[str, object] | None = None
    if "weight_kg" in weights:
        kg = weights["weight_kg"]
        negative_rows = pd.DataFrame(
            {
                "Timestamp": parsed_time,
                "weight_kg": kg,
            }
        ).loc[kg < 0]
        sorted_weight = pd.DataFrame(
            {"Timestamp": parsed_time, "weight_kg": kg}
        ).dropna().sort_values("Timestamp")
        sorted_weight["Previous timestamp"] = sorted_weight["Timestamp"].shift()
        sorted_weight["Previous weight_kg"] = sorted_weight["weight_kg"].shift()
        sorted_weight["Change (kg)"] = sorted_weight["weight_kg"].diff()
        jump_rows = sorted_weight.loc[
            sorted_weight["Change (kg)"].abs() >= WEIGHT_JUMP_SCREEN_KG,
            [
                "Previous timestamp",
                "Timestamp",
                "Previous weight_kg",
                "weight_kg",
                "Change (kg)",
            ],
        ]

    if {"weight_kg", "weight_grams"} <= weights.keys():
        difference = (weights["weight_grams"] / 1000 - weights["weight_kg"]).abs()
        consistency = {
            "median_abs_difference_kg": float(difference.median()),
            "max_abs_difference_kg": float(difference.max()),
            "exact_matches": int((difference == 0).sum()),
            "rows": int(difference.notna().sum()),
        }

    timezone_description = (
        str(parsed_time.dt.tz)
        if hasattr(parsed_time, "dt") and parsed_time.dt.tz is not None
        else "No timezone information in the CSV (naive timestamps)"
    )
    sample = data.head(5)
    time_range = (
        f"{valid_time.min()} to {valid_time.max()}" if not valid_time.empty else "Unavailable"
    )
    anomaly_parts = []
    if not valid_time.empty:
        base_date = valid_time.min().normalize()
        for start_clock, end_clock in UNVERIFIED_INTERVALS:
            start = base_date + pd.to_timedelta(start_clock)
            end = base_date + pd.to_timedelta(end_clock)
            in_window = parsed_time.between(start, end, inclusive="both")
            if in_window.any():
                part = data.loc[in_window].copy()
                part.insert(0, "review_status", "unverified_anomaly")
                part.insert(
                    1, "flagged_interval", f"{start_clock}-{end_clock} (inclusive)"
                )
                anomaly_parts.append(part)
    anomaly_data = (
        pd.concat(anomaly_parts, ignore_index=True)
        if anomaly_parts
        else pd.DataFrame(columns=["review_status", "flagged_interval", *data.columns])
    )
    anomaly_report_path.parent.mkdir(parents=True, exist_ok=True)
    anomaly_data.to_csv(anomaly_report_path, index=False)
    blockers = []
    if "weight_kg" not in weights:
        blockers.append("no `weight_kg` field was identified for the requested target")
    if len(negative_rows):
        blockers.append(f"{len(negative_rows)} negative `weight_kg` readings")
    if len(jump_rows):
        blockers.append(
            f"{len(jump_rows)} consecutive `weight_kg` changes exceeded the exploratory screen"
        )
    gate_status = (
        "BLOCKED: " + "; ".join(blockers)
        if blockers
        else "No negative or screened abrupt `weight_kg` readings detected; physical "
        "interpretability still requires confirmation."
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Data quality inspection",
        "",
        f"- **Source CSV:** `{csv_path.name}`",
        f"- **Source path in project:** `data/raw/{csv_path.name}`",
        f"- **Rows × columns:** {data.shape[0]} × {data.shape[1]}",
        f"- **Timestamp range:** {time_range}",
        f"- **Timezone:** {timezone_description}",
        "- **Raw data:** read only; this inspection does not modify the source.",
        "",
        "## Discovered schema and units",
        "",
        _format_table(dtypes),
        "",
        _format_table(pd.DataFrame(schema_rows)),
        "",
        "Temperature and humidity units are not independently confirmed by CSV metadata or sensor configuration.",
        "",
        "## Sample rows",
        "",
        _format_table(sample),
        "",
        "## Missing values, duplicates, and cadence",
        "",
        f"- Timestamp parse failures: {int(parsed_time.isna().sum())}",
        f"- Duplicate timestamps: {int(valid_time.duplicated().sum())}",
        f"- Exact duplicate rows: {int(data.duplicated().sum())}",
        f"- Interval between unique valid timestamps (seconds): "
        f"median `{cadence}`, minimum `{intervals.min() if not intervals.empty else 'n/a'}`, "
        f"maximum `{intervals.max() if not intervals.empty else 'n/a'}`.",
        f"- Intervals flagged as gaps (>1.5× median cadence): {len(gap_rows)}",
        "",
        "### Missing values by column",
        "",
        _format_table(missing),
        "",
        "### Detected gaps",
        "",
        _format_table(pd.DataFrame(gap_rows)),
        "",
        "## Numeric descriptive statistics",
        "",
        _format_table(numeric_summary),
        "",
        "## Weight signal checks",
        "",
        f"- Negative `weight_kg` readings: {len(negative_rows)}; **not changed or removed**.",
        f"- Zero `weight_kg` readings: {int((weights['weight_kg'] == 0).sum()) if 'weight_kg' in weights else 'not available'}.",
        f"- Abrupt consecutive `weight_kg` changes flagged at |Δ| ≥ {WEIGHT_JUMP_SCREEN_KG:.2f} kg per observed interval: {len(jump_rows)}.",
        "- The jump screen is an exploratory flag, not a calibrated physical limit.",
    ]
    if consistency is not None:
        lines.extend(
            [
                f"- `weight_grams / 1000` versus `weight_kg` on corresponding rows: "
                f"median absolute difference {consistency['median_abs_difference_kg']:.6f} kg, "
                f"maximum {consistency['max_abs_difference_kg']:.6f} kg; "
                f"{consistency['exact_matches']}/{consistency['rows']} exact matches.",
                "- The two weight columns corroborate a common signal at the same row timestamps, "
                "with small rounding/export differences; use `weight_kg` as the provisional "
                "candidate only after the measurement anomalies are resolved.",
                "",
                "### Negative weight readings",
                "",
                _format_table(negative_rows),
            ]
        )
    lines.extend(
        [
            "",
            "### Abrupt weight changes",
            "",
            _format_table(jump_rows),
            "",
            "## Unverified anomaly review windows",
            "",
            "These intervals were supplied for review. **Every included row remains unverified**: "
            "this report does not classify readings as valid or invalid, and does not modify, "
            "remove, replace, or interpolate them. All source sensor columns are retained.",
            "",
            f"- Detailed timestamped readings: `{anomaly_report_path.name}` "
            f"({len(anomaly_data)} rows across {len(anomaly_parts)} intervals).",
            "- Review against the original Grafana exports, sensor logs, and calibration records.",
            "- Timestamp alignment, load-cell calibration, unit consistency across original streams, "
            "and tare/handling history cannot be resolved from the combined CSV alone.",
            "",
            _format_table(
                pd.DataFrame(
                    [
                        {
                            "Flagged interval (inclusive)": f"{start}-{end}",
                            "Review status": "Unverified; cause unknown",
                        }
                        for start, end in UNVERIFIED_INTERVALS
                    ]
                )
            ),
            "",
            "## Gate decision",
            "",
            f"**Inspection completed. Supervised-learning/cleaning gate: {gate_status}**",
            (
                f"The largest flagged absolute change is "
                f"{jump_rows['Change (kg)'].abs().max():.4f} kg in one "
                f"{cadence:g}-second interval."
                if not jump_rows.empty and cadence is not None
                else ""
            ),
            "",
            "Do not replace negative values with zero, discard flagged rows, interpolate, or train "
            "until the target is physically interpretable and an explicit handling policy is "
            "confirmed. Abrupt drops may reflect physical handling, tare/reset, sensor faults, or "
            "alignment issues; the CSV has no event/calibration log to distinguish these explanations. "
            "The flagged intervals remain unverified until checked against source exports, sensor "
            "logs, calibration records, and tare/handling history.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "rows": len(data),
        "columns": list(data.columns),
        "missing": int(data.isna().sum().sum()),
        "duplicate_timestamps": int(valid_time.duplicated().sum()),
        "duplicate_rows": int(data.duplicated().sum()),
        "cadence_seconds": cadence,
        "gap_count": len(gap_rows),
        "negative_weight_count": len(negative_rows),
        "weight_jump_count": len(jump_rows),
        "anomaly_report_rows": len(anomaly_data),
        "gate_status": gate_status,
        "report": report_path,
        "anomaly_report": anomaly_report_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--timestamp-column", default="Time")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--anomaly-report", type=Path, default=DEFAULT_ANOMALY_REPORT)
    args = parser.parse_args()

    result = inspect_csv(
        args.input, args.timestamp_column, args.report, args.anomaly_report
    )
    print(f"CSV: {args.input}")
    print(f"Rows/columns: {result['rows']} / {len(result['columns'])}")
    print(f"Columns: {', '.join(result['columns'])}")
    print(f"Missing values: {result['missing']}")
    print(f"Duplicate timestamps / rows: {result['duplicate_timestamps']} / {result['duplicate_rows']}")
    print(f"Median cadence (seconds): {result['cadence_seconds']}")
    print(f"Detected gaps: {result['gap_count']}")
    print(f"Negative weight readings: {result['negative_weight_count']}")
    print(f"Abrupt weight changes: {result['weight_jump_count']}")
    print(f"QUALITY GATE: {result['gate_status']}")
    print(f"Report: {result['report']}")
    print(
        f"Unverified anomaly rows: {result['anomaly_report_rows']}; "
        f"anomaly report: {result['anomaly_report']}"
    )


if __name__ == "__main__":
    main()
