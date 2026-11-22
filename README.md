# Data Quality Detective

An interactive Streamlit case study for **Artifact 4**. Investigate 1,000 synthetic retail records, compare quality before and after cleaning, and review the release and return-prediction checks. See the [portfolio write-up](PORTFOLIO.md) and [reflection](REFLECTION.md).

## Run and verify

Use Python 3.10 or 3.12. From the project directory:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

The dashboard runs with the bundled CSVs and audit report. To regenerate them, run these commands in order:

```sh
python generate.py
python clean.py
python audit.py
```

## Dataset and decisions

The seed is 42. The generator creates 980 distinct transactions and appends 20 exact copies. The records use a 2025 synthetic calendar, amounts in USD, and a deliberately uneven regional distribution. It injects single-field defects into separate source rows among the first 200 transactions, to simulate an early ingestion incident. The copies use separate source rows. The one-based source row indexes count data records, with the header excluded.

| Injected defect | Rows | Treatment |
| --- | ---: | --- |
| Blank region | 24 | Quarantine |
| Blank unit price | 16 | Quarantine |
| Negative quantity | 12 | Quarantine |
| Impossible calendar date | 10 | Quarantine |
| Unit price of $9,999 | 8 | Quarantine |
| Category casing and padding | 18 | Strip and standardize |
| US-style date string | 15 | Convert to ISO format |
| Exact copy | 20 | Keep the first occurrence, log the extra copy |

Conflicting records with the same transaction ID are quarantined as a group. The pipeline preserves the input file, logs the decision for every source row and exports unresolved rows for review. It avoids inventing values for missing or invalid transaction details.

| Column | Meaning and validation |
| --- | --- |
| transaction_id | Synthetic transaction key matching T plus five digits. Required and unique. |
| order_date | Calendar date in ISO YYYY-MM-DD after cleaning. The generator also injects MM/DD/YYYY strings. |
| region | North, South, East or West. |
| category | Electronics, Home, Grocery or Apparel. |
| quantity | Integer from 1 to 50. |
| unit_price | Numeric USD amount from $0.01 to $500. |
| returned | Binary outcome observed after checkout. |
| refund_amount | Finite nonnegative USD amount observed after a return. Generator assigns zero for other transactions. |

## Verified quality results

| Measure | Raw | Clean |
| --- | ---: | ---: |
| Rows | 1,000 | 910 |
| Rows passing every validation rule | 877 (87.7%) | 910 (100%) |
| Missing required cells | 40 | 0 |
| Extra exact copies | 20 | 0 |
| Invalid unit prices | 8 | 0 |
| Unit-price outliers by 1.5×IQR | 8 | 0 |

The 90 excluded records consist of 70 quarantines and 20 duplicates. The cleaner repaired 33 retained records. Rules are applied to each dataset independently. Blank strings count as missing. A row can violate several rules and still counts once against the pass rate. IQR fences are derived independently from finite prices in each dataset and are descriptive. The $0.01–$500 price rule determines quarantine.

## Files

- `data/retail_raw.csv` and `data/retail_clean.csv` contain the source and retained transactions.
- `data/defect_manifest.csv`, `data/cleaning_log.csv`, and `data/quarantine.csv` document injected defects, source-row decisions, and rejected records.
- `data/audit.json` contains quality, privacy and ML readiness results.
- `generate.py`, `clean.py`, and `audit.py` reproduce the outputs. `app.py` displays the results and provides downloads.
- `tests/test_project.py` verifies generation, cleaning, auditing and dashboard controls.

## Release and deployment

The public app is designed for the bundled synthetic data. It accepts no uploads and requires no secrets. The privacy checks compare columns against the release schema and count cells matching common email, US phone, and SSN patterns. Real releases require review for identifiers, linkage risk, data provenance and approved access.

For [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), select this repository, branch `main`, and entrypoint `app.py`. The root requirements file supplies dependencies. Use Python 3.12 on Community Cloud.
