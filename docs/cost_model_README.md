# Cost model workbook

This workbook compares the monthly cost of running inference on-device versus in the cloud using a small set of workload drivers. Text-based exports live in `docs/cost_model_inputs.csv`, `docs/cost_model_comparison.csv`, and the CI-friendly summary `docs/cost_model.csv`. Use the generator script to optionally build an Excel workbook without committing binary artifacts.

## Inputs and assumptions
- **Session volume (per month):** Total inference sessions you expect to serve monthly.
- **Avg inference duration:** Average minutes of compute per session.
- **DAL traffic per session:** Gigabytes of data exchanged with the data-access layer for each session.
- **Hot-update cadence & package size:** Frequency and size of model/config updates.
- **Device amortization & capacity:** Monthly hardware cost per device and the sessions-per-month it can support.
- **Network/distribution costs:** Per-GB rates to push updates to edge devices or cloud replicas.
- **Control-plane overhead:** Fixed monthly spend to operate orchestration/configuration in each model.

Defaults live in `scripts/generate_cost_model.py` within the `inputs` list. Adjust them to reflect your environment before regenerating the workbook or CSVs.

## Formulas (Comparison sheet)
- **Device count:** `CEILING(Session volume / Sessions per device capacity)`
- **DAL traffic:** `Session volume * DAL traffic per session`
- **DAL cost:** `DAL traffic * DAL egress cost`
- **On-device compute:** `Device count * Device amortization`
- **On-device updates:** `Device count * Hot-update cadence * Update package size * Update distribution cost`
- **Cloud compute:** `Session volume * Avg inference duration * Cloud inference cost`
- **Cloud updates:** `Hot-update cadence * Update package size * Cloud update distribution cost`
- **Totals:** Sum of compute + DAL + hot-update + control-plane overhead for each scenario.

The `Comparison` sheet surfaces these formulas alongside descriptive notes, while the `Derived Metrics` section clarifies device counts and total DAL traffic volume.

## Refreshing the numbers
1. Modify the `inputs` list in `scripts/generate_cost_model.py` to match your target workload or pricing.
2. Run `python scripts/generate_cost_model.py` from the repo root. The script rewrites `docs/cost_model_inputs.csv`, `docs/cost_model_comparison.csv`, and `docs/cost_model.csv`.
3. If you need an Excel workbook locally, install `openpyxl` (`pip install openpyxl`) and pass `--xlsx` to also emit `docs/cost_model.xlsx`. Avoid committing the binary workbook; rely on the CSV artifacts for review and CI.

## Using the CSV export
The CSV includes the same cost breakdown used in the `Comparison` sheet with columns: `scenario`, `inference_compute`, `dal_traffic`, `hot_updates`, `overhead`, and `total`. Values are pre-evaluated so CI can ingest the figures without Excel formula parsing.
