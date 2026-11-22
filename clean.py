"""Standardize defensible values and quarantine unresolved transactions."""
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd

from audit import FIELDS, ROOT, dates, load, normalized, problems


def clean(frame):
    source = frame.loc[:, list(FIELDS)].reset_index(drop=True)
    fixed = normalized(source)
    fixed["category"] = fixed.category.str.title()
    fixed["region"] = fixed.region.str.title()
    fixed["order_date"] = dates(fixed.order_date).dt.strftime("%Y-%m-%d").astype("string").fillna(fixed.order_date)
    changes = fixed.fillna("").ne(source.fillna(""))
    rules = problems(fixed)
    copies = source.duplicated()
    unique = fixed.loc[~copies]
    collisions = unique.transaction_id.notna() & unique.transaction_id.duplicated(keep=False)
    rejected = rules.drop(columns=["Extra exact copies", "Extra transaction IDs"]).any(axis=1)
    rejected.loc[unique.index] |= collisions
    log = pd.DataFrame({
        "source_row": source.index + 1,
        "transaction_id": source.transaction_id,
        "action": "retained",
        "standardized_fields": changes.apply(lambda row: ", ".join(row.index[row]), axis=1),
        "reason": rules.drop(columns=["Extra exact copies", "Extra transaction IDs"])
        .apply(lambda row: "; ".join(row.index[row]), axis=1),
    })
    log.loc[collisions[collisions].index, "reason"] = "Conflicting transaction ID. " + log.reason
    log.loc[rejected, "action"] = "quarantined"
    log.loc[copies, ["action", "reason"]] = ["removed duplicate", "Exact copy of earlier source row"]
    kept = ~(copies | rejected)
    log.loc[kept & changes.any(axis=1), "action"] = "standardized"
    return fixed.loc[kept].reset_index(drop=True), log


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    source = load(args.data_dir / "retail_raw.csv")
    cleaned, decisions = clean(source)
    cleaned.to_csv(args.data_dir / "retail_clean.csv", index=False)
    decisions.to_csv(args.data_dir / "cleaning_log.csv", index=False)
    quarantine = source.join(decisions[["source_row", "reason"]])
    quarantine.loc[decisions.action.eq("quarantined")].to_csv(
        args.data_dir / "quarantine.csv", index=False
    )
    print(decisions.action.value_counts().to_string())
