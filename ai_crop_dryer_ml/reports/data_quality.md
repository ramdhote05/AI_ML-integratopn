# Data quality inspection

- **Source CSV:** `smart_dryer_combined_dataset.csv`
- **Source path in project:** `data/raw/smart_dryer_combined_dataset.csv`
- **Rows × columns:** 350 × 5
- **Timestamp range:** 2026-10-10 00:31:40 to 2026-10-10 01:29:50
- **Timezone:** No timezone information in the CSV (naive timestamps)
- **Raw data:** read only; this inspection does not modify the source.

## Discovered schema and units

| Column       | CSV dtype   |
|:-------------|:------------|
| Time         | object      |
| temperature  | float64     |
| weight_kg    | float64     |
| weight_grams | float64     |
| humidity     | float64     |

| Column       | Unit / interpretation   | Evidence / caveat                                                             |
|:-------------|:------------------------|:------------------------------------------------------------------------------|
| Time         | Timestamp               | CSV timestamp; timezone awareness is reported separately.                     |
| temperature  | °C (interpreted)        | Consistent with the project notes/specification; not encoded in CSV metadata. |
| weight_kg    | kg (header-declared)    | Candidate weight signal; anomalous values require investigation.              |
| weight_grams | g (header-declared)     | Compare to kilograms only after unit conversion and timestamp alignment.      |
| humidity     | % RH (interpreted)      | Consistent with the project notes/specification; not encoded in CSV metadata. |

Temperature and humidity units are not independently confirmed by CSV metadata or sensor configuration.

## Sample rows

| Time                |   temperature |   weight_kg |   weight_grams |   humidity |
|:--------------------|--------------:|------------:|---------------:|-----------:|
| 2026-10-10 00:31:40 |          33.1 |       0.658 |            658 |       62.9 |
| 2026-10-10 00:31:50 |          33.1 |       0.658 |            657 |       62.9 |
| 2026-10-10 00:32:00 |          33.1 |       0.658 |            657 |       62.9 |
| 2026-10-10 00:32:10 |          33.1 |       0.658 |            658 |       62.8 |
| 2026-10-10 00:32:20 |          33.1 |       0.658 |            658 |       62.8 |

## Missing values, duplicates, and cadence

- Timestamp parse failures: 0
- Duplicate timestamps: 0
- Exact duplicate rows: 0
- Interval between unique valid timestamps (seconds): median `10.0`, minimum `10.0`, maximum `10.0`.
- Intervals flagged as gaps (>1.5× median cadence): 0

### Missing values by column

| Column       |   Missing |
|:-------------|----------:|
| Time         |         0 |
| temperature  |         0 |
| weight_kg    |         0 |
| weight_grams |         0 |
| humidity     |         0 |

### Detected gaps

_None._

## Numeric descriptive statistics

| Column       |   count |       mean |        std |    min |     25% |     50% |     75% |     max |
|:-------------|--------:|-----------:|-----------:|-------:|--------:|--------:|--------:|--------:|
| temperature  |     350 |  32.8797   |   0.161351 | 32.6   |  32.8   |  32.9   |  33     |  33.1   |
| weight_kg    |     350 |   0.430476 |   0.256203 | -0.002 |   0.11  |   0.497 |   0.657 |   0.707 |
| weight_grams |     350 | 430.451    | 256.178    | -2.28  | 110     | 497     | 657     | 707     |
| humidity     |     350 |  62.8223   |   0.569638 | 61.6   |  62.725 |  63.1   |  63.2   |  63.5   |

## Weight signal checks

- Negative `weight_kg` readings: 5; **not changed or removed**.
- Zero `weight_kg` readings: 1.
- Abrupt consecutive `weight_kg` changes flagged at |Δ| ≥ 0.05 kg per observed interval: 11.
- The jump screen is an exploratory flag, not a calibrated physical limit.
- `weight_grams / 1000` versus `weight_kg` on corresponding rows: median absolute difference 0.000000 kg, maximum 0.001000 kg; 270/350 exact matches.
- The two weight columns corroborate a common signal at the same row timestamps, with small rounding/export differences; use `weight_kg` as the provisional candidate only after the measurement anomalies are resolved.

### Negative weight readings

| Timestamp           |   weight_kg |
|:--------------------|------------:|
| 2026-10-10 01:12:00 |     -0.0004 |
| 2026-10-10 01:12:10 |     -0.002  |
| 2026-10-10 01:12:20 |     -0.0015 |
| 2026-10-10 01:12:30 |     -0.0005 |
| 2026-10-10 01:12:50 |     -0.0013 |

### Abrupt weight changes

| Previous timestamp   | Timestamp           |   Previous weight_kg |   weight_kg |   Change (kg) |
|:---------------------|:--------------------|---------------------:|------------:|--------------:|
| 2026-10-10 00:59:00  | 2026-10-10 00:59:10 |               0.657  |      0.521  |       -0.136  |
| 2026-10-10 00:59:10  | 2026-10-10 00:59:20 |               0.521  |      0.11   |       -0.411  |
| 2026-10-10 00:59:20  | 2026-10-10 00:59:30 |               0.11   |      0.305  |        0.195  |
| 2026-10-10 00:59:30  | 2026-10-10 00:59:40 |               0.305  |      0.5    |        0.195  |
| 2026-10-10 01:07:40  | 2026-10-10 01:07:50 |               0.497  |      0.707  |        0.21   |
| 2026-10-10 01:07:50  | 2026-10-10 01:08:00 |               0.707  |      0.0982 |       -0.6088 |
| 2026-10-10 01:11:40  | 2026-10-10 01:11:50 |               0.11   |      0.0555 |       -0.0545 |
| 2026-10-10 01:11:50  | 2026-10-10 01:12:00 |               0.0555 |     -0.0004 |       -0.0559 |
| 2026-10-10 01:12:50  | 2026-10-10 01:13:00 |              -0.0013 |      0.213  |        0.2143 |
| 2026-10-10 01:13:00  | 2026-10-10 01:13:10 |               0.213  |      0.284  |        0.071  |
| 2026-10-10 01:19:20  | 2026-10-10 01:19:30 |               0.284  |      0.0692 |       -0.2148 |

## Unverified anomaly review windows

These intervals were supplied for review. **Every included row remains unverified**: this report does not classify readings as valid or invalid, and does not modify, remove, replace, or interpolate them. All source sensor columns are retained.

- Detailed timestamped readings: `anomaly_review.csv` (20 rows across 4 intervals).
- Review against the original Grafana exports, sensor logs, and calibration records.
- Timestamp alignment, load-cell calibration, unit consistency across original streams, and tare/handling history cannot be resolved from the combined CSV alone.

| Flagged interval (inclusive)   | Review status             |
|:-------------------------------|:--------------------------|
| 00:59:00-00:59:40              | Unverified; cause unknown |
| 01:07:40-01:08:00              | Unverified; cause unknown |
| 01:11:40-01:13:10              | Unverified; cause unknown |
| 01:19:20-01:19:30              | Unverified; cause unknown |

## Gate decision

**Inspection completed. Supervised-learning/cleaning gate: BLOCKED: 5 negative `weight_kg` readings; 11 consecutive `weight_kg` changes exceeded the exploratory screen**
The largest flagged absolute change is 0.6088 kg in one 10-second interval.

Do not replace negative values with zero, discard flagged rows, interpolate, or train until the target is physically interpretable and an explicit handling policy is confirmed. Abrupt drops may reflect physical handling, tare/reset, sensor faults, or alignment issues; the CSV has no event/calibration log to distinguish these explanations. The flagged intervals remain unverified until checked against source exports, sensor logs, calibration records, and tare/handling history.
