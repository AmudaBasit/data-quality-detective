"""Measure data quality, release checks, and return-model readiness."""
import json
from pathlib import Path

import pandas as pd

from generate import CATEGORIES, REGIONS

ROOT = Path(__file__).resolve().parent
FIELDS = ("transaction_id", "order_date", "region", "category", "quantity",
          "unit_price", "returned", "refund_amount")
LABEL = "returned"
FEATURES = ("region", "category", "quantity", "unit_price")
RELEASE_FIELDS = frozenset(FIELDS)


def load(path):
    return pd.read_csv(path, dtype="string", keep_default_na=False)


def normalized(frame):
    return frame.astype("string").apply(lambda column: column.str.strip().replace("", pd.NA))


def dates(values):
    iso = pd.to_datetime(values, format="%Y-%m-%d", errors="coerce")
    alternate = pd.to_datetime(values, format="%m/%d/%Y", errors="coerce")
    return iso.fillna(alternate)


def problems(frame):
    clean = normalized(frame)
    price = pd.to_numeric(clean.unit_price, errors="coerce")
    quantity = pd.to_numeric(clean.quantity, errors="coerce")
    refunds = pd.to_numeric(clean.refund_amount, errors="coerce")
    ordered = dates(clean.order_date)
    return pd.DataFrame({
        "Extra exact copies": frame.duplicated(),
        "Extra transaction IDs": clean.transaction_id.notna() & clean.transaction_id.duplicated(),
        "Missing required values": clean[list(FIELDS)].isna().any(axis=1),
        "Invalid transaction ID": clean.transaction_id.notna()
        & ~clean.transaction_id.str.fullmatch(r"T[0-9]{5}", na=False),
        "Invalid date": clean.order_date.notna() & ordered.isna(),
        "Non-ISO date": ordered.notna() & frame.order_date.ne(ordered.dt.strftime("%Y-%m-%d")),
        "Noncanonical category": clean.category.notna() & ~frame.category.isin(CATEGORIES),
        "Invalid region": clean.region.notna() & ~frame.region.isin(REGIONS),
        "Invalid quantity": clean.quantity.notna()
        & ~(quantity.between(1, 50) & quantity.mod(1).eq(0)).fillna(False),
        "Invalid unit price": clean.unit_price.notna() & ~price.between(0.01, 500).fillna(False),
        "Invalid return flag": clean.returned.notna() & ~clean.returned.isin(["0", "1"]),
        "Invalid refund amount": clean.refund_amount.notna()
        & ~(refunds.ge(0) & refunds.lt(float("inf"))).fillna(False),
    }).fillna(False).astype(bool)


def metrics(frame):
    flags = problems(frame)
    missing = normalized(frame)[list(FIELDS)].isna()
    price = pd.to_numeric(frame.unit_price, errors="coerce")
    finite = price[price.abs().lt(float("inf"))]
    q1, q3 = finite.quantile([0.25, 0.75])
    low, high = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
    return {
        "rows": len(frame),
        "passing_rows": int((~flags.any(axis=1)).sum()),
        "passing_pct": round(100 * (~flags.any(axis=1)).mean(), 2) if len(frame) else None,
        "missing_cells": missing.sum().astype(int).to_dict(),
        "rule_counts": flags.sum().astype(int).to_dict(),
        "price_iqr_outliers": int((finite.lt(low) | finite.gt(high)).sum()),
    }


def privacy(frame):
    strings = frame.astype("string")
    patterns = {
        "Email-like cells": r"(?i)[\w.+-]+@[\w.-]+\.[a-z]{2,}",
        "US phone-like cells": r"(?<!\d)(?:\+1[- .]?)?(?:\(\d{3}\)|\d{3})[- .]\d{3}[- .]\d{4}(?!\d)",
        "US SSN-like cells": r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)",
    }
    return {
        "Unexpected columns": len(set(frame.columns) - RELEASE_FIELDS),
        **{name: int(strings.apply(lambda col: col.str.contains(pattern, na=False)).sum().sum())
           for name, pattern in patterns.items()},
    }


def readiness(frame):
    target = pd.to_numeric(frame[LABEL], errors="coerce")
    grouped = frame.assign(positive=target).groupby("region", dropna=False).positive
    regions = grouped.agg(records="size", returned="sum", return_rate="mean")
    regions["share"] = regions.records / len(frame)
    regions["under_10_pct"] = regions.share.lt(0.10)
    dated = dates(frame.order_date).sort_values()
    cutoff = dated.iloc[int(len(dated) * 0.8)]
    train = frame.loc[dates(frame.order_date).lt(cutoff)]
    holdout = frame.loc[dates(frame.order_date).ge(cutoff)]
    refund_positive = pd.to_numeric(frame.refund_amount, errors="coerce").gt(0)
    return regions, {
        "target": LABEL,
        "recommended_features": list(FEATURES),
        "positive_labels": int(target.eq(1).sum()),
        "positive_rate": round(float(target.mean()), 4),
        "refund_signal_agreement": round(float(refund_positive.eq(target.eq(1)).mean()), 4),
        "cutoff_date": cutoff.date().isoformat(),
        "train_rows": len(train),
        "holdout_rows": len(holdout),
        "shared_transaction_ids": len(set(train.transaction_id) & set(holdout.transaction_id)),
    }


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    raw = load(args.data_dir / "retail_raw.csv")
    cleaned = load(args.data_dir / "retail_clean.csv")
    regions, ml = readiness(cleaned)
    report = {"raw": metrics(raw), "clean": metrics(cleaned),
              "privacy": {"raw": privacy(raw), "clean": privacy(cleaned)},
              "ml": ml, "regions": regions.reset_index().to_dict("records")}
    output = json.dumps(report, indent=2, allow_nan=False)
    (args.data_dir / "audit.json").write_text(output + "\n", encoding="utf-8")
    print(output)
