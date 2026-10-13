# AI Crop Dryer ML pipeline

This project contains the first gated stage of the crop-weight prediction
experiment. The discovered source CSV is kept in `data\raw` and is read-only;
generated files are kept under this project directory.

## Current phase

Phase 0 discovery and Step 1 data inspection are implemented. The Step 1
report currently blocks cleaning and model training because the input contains
negative weights and unexplained, abrupt weight changes. No values have been
clamped, interpolated, or removed. Continue only after the scale/event history
and a written handling policy make the target interpretable.

The available observation is about 58 minutes long. Even after the quality
issue is resolved, it cannot establish production-ready drying-completion ETA
performance.

## Run data inspection

From PowerShell:

```powershell
cd .\ai_crop_dryer_ml
python .\1_check_data.py
```

The script reads `.\data\raw\smart_dryer_combined_dataset.csv` by default and
writes `.\reports\data_quality.md` and `.\reports\anomaly_review.csv`. To
inspect a different CSV:

```powershell
python .\1_check_data.py --input "C:\path\to\sensor.csv" --timestamp-column "Time"
```

Inspection reports missing values, duplicate timestamps/rows, cadence and
gaps, numeric summaries, candidate weight-unit consistency, negative weights,
and large consecutive weight changes. It also saves the user-designated
unverified time ranges, with all original sensor columns, to
`.\reports\anomaly_review.csv`. These readings are flagged for review only;
the script does not classify, alter, remove, replace, or interpolate them.
Check the report against original Grafana exports, sensor logs, calibration
records, and tare/handling history.

## Current outputs

- `reports\data_quality.md` — generated Step 1 inspection and gate result.
- `reports\anomaly_review.csv` — timestamped source readings in the four
  unverified review intervals.
- `data\raw\smart_dryer_combined_dataset.csv` — original combined input, kept
  unchanged.
- `reference\` — supplied project specification, dataset notes, and existing
  diagnostic plots.

Cleaning, feature engineering, training, prediction, and model-evaluation
outputs are intentionally not generated until the data-quality gate passes.
