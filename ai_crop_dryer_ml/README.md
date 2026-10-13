# AI Crop Dryer ML pipeline

This folder contains the first gated stage of the crop-weight prediction
experiment in the [`ramdhote05/AI_ML-integratopn`](https://github.com/ramdhote05/AI_ML-integratopn/tree/main/ai_crop_dryer_ml)
repository. The discovered source CSV is kept in `data\raw` and is read-only;
generated files are kept under this project directory.

## Current phase

Phase 0 discovery and Step 1 data inspection are implemented. The Step 1
report currently blocks cleaning and model training because the input contains
five negative weights and 11 consecutive changes larger than the exploratory
0.05 kg screen. Their causes are unknown. The user-designated windows are
explicitly unverified:

- `00:59:00–00:59:40`
- `01:07:40–01:08:00`
- `01:11:40–01:13:10`
- `01:19:20–01:19:30`

No values have been clamped, interpolated, removed, or classified as valid or
invalid. Training remains blocked until the windows and weight signal can be
checked against original Grafana exports, sensor logs, calibration records,
and tare/handling history, and an explicit data policy is agreed.

The available observation is about 58 minutes long. Even after the data-quality
issue is resolved, it can support only an exploratory five-minute-ahead weight
prediction experiment; it cannot establish production-ready drying-completion
ETA performance.

## Findings from the current CSV

The inspected file has 350 rows and these columns: `Time`, `temperature`,
`weight_kg`, `weight_grams`, and `humidity`. There are no missing fields,
duplicate timestamps, duplicate rows, or detected gaps. The median sampling
interval is 10 seconds. The timestamps do not specify a timezone.

The CSV headers identify the weight units. On matching rows, `weight_grams`
converted to kilograms differs from `weight_kg` by a median of 0 kg and a
maximum of 0.001 kg (270 exact matches out of 350). Temperature (°C) and
humidity (% RH) are interpretations from the supplied notes/specification,
not units independently confirmed by sensor metadata. Only the combined CSV
was available; original separate Grafana exports and sensor/calibration logs
were not included.

## Project contents

- `1_check_data.py` — read-only CSV inspection and report generator.
- `data/raw/smart_dryer_combined_dataset.csv` — original combined CSV; do not
  edit in place.
- `reports/data_quality.md` — schema, sampling, summary statistics, negative
  readings, abrupt weight changes, and gate decision.
- `reports/anomaly_review.csv` — all source sensor columns for rows in the
  four user-designated windows, marked `unverified_anomaly`.
- `reference/` — supplied project specification, dataset notes, and existing
  diagnostic plots.
- `requirements.txt` — Python packages needed by the inspection and planned
  pipeline.

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
and consecutive weight changes at or above 0.05 kg. The latter is only an
exploratory screening threshold, not a calibrated physical limit. The script
also exports user-designated time windows, with all original sensor columns,
to `.\reports\anomaly_review.csv`. These readings are flagged for review only;
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
In particular, no model has been trained and no predictive metrics are
available.
