# Artifact 4 · Data Quality Detective

**Project.** An interactive analysis of how bad input data affects retail reporting and return prediction. The dashboard lets a reviewer switch between raw and cleaned transactions, filter by defect, inspect decisions at the transaction level, and download the evidence behind the results.

**Approach.** I built a reproducible 1,000-record synthetic dataset with missing values, duplicates, invalid dates and quantities, extreme prices, and inconsistent formats. I measured violations before cleaning, standardized recoverable values, and recorded every cleaning decision. I used quarantine to preserve questionable source rows for review.

**Result.** The share of records passing all validation rules rose from 87.7% to 100% among retained records. I repaired 33 transactions, removed 20 extra copies, and quarantined 70 records with missing or invalid values. The data and audit report document all 90 exclusions so reviewers can distinguish improvements from changes in coverage.

**Responsible use.** The app uses fictional transactions and screens the release for unexpected fields and common identifier patterns. For a return prediction experiment, the dashboard checks geographic representation, outcome prevalence, and transaction ID overlap across a chronological split. It identifies refund amount as target leakage because that amount is only available after a return.

**Tools and verification.** Python, pandas and Streamlit. Automated checks reproduce the dataset and audit, reconcile cleaning decisions, validate privacy and leakage calculations, and exercise dashboard filters.
