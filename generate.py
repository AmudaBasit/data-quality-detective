"""Generate reproducible synthetic retail transactions and an injection manifest."""
from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd

ROOT = Path(__file__).resolve().parent
REGIONS = ("North", "South", "East", "West")
CATEGORIES = ("Electronics", "Home", "Grocery", "Apparel")


def generate(seed=42):
    rng = random.Random(seed)
    rows = []
    for i in range(980):
        region = rng.choices(REGIONS, weights=[50, 27, 17, 6])[0]
        category = rng.choice(CATEGORIES)
        quantity = rng.randint(1, 8)
        price = round(rng.uniform(5, 180), 2)
        returned = rng.random() < (0.22 if region == "West" else 0.10)
        rows.append({
            "transaction_id": f"T{i+1:05d}",
            "order_date": (date(2025, 1, 1) + timedelta(days=i // 4)).isoformat(),
            "region": region,
            "category": category,
            "quantity": quantity,
            "unit_price": price,
            "returned": int(returned),
            "refund_amount": round(quantity * price, 2) if returned else 0.0,
        })

    raw = pd.DataFrame(rows).astype({"unit_price": object})
    manifest = []
    injections = [
        ("region", 24, None, "missing region"),
        ("unit_price", 16, None, "missing unit price"),
        ("quantity", 12, -3, "negative quantity"),
        ("order_date", 10, "2025-02-30", "invalid calendar date"),
        ("unit_price", 8, 9999.0, "price exceeds domain maximum"),
        ("category", 18, lambda value: f" {value.lower()} ", "category label variant"),
        ("order_date", 15, lambda value: date.fromisoformat(value).strftime("%m/%d/%Y"),
         "alternate date format"),
    ]
    locations = iter(rng.sample(range(200), sum(item[1] for item in injections)))
    for field, count, replacement, defect in injections:
        for _ in range(count):
            index = next(locations)
            prior = raw.at[index, field]
            value = replacement(prior) if callable(replacement) else replacement
            raw.at[index, field] = value
            manifest.append((index + 1, raw.at[index, "transaction_id"], field, defect))

    copies = raw.iloc[200:220]
    for i, transaction_id in enumerate(copies.transaction_id, start=981):
        manifest.append((i, transaction_id, "*", "exact duplicate"))
    raw = pd.concat([raw, copies], ignore_index=True)
    return raw, pd.DataFrame(manifest, columns=["source_row", "transaction_id", "field", "defect"])


if __name__ == "__main__":
    data = ROOT / "data"
    data.mkdir(exist_ok=True)
    raw, manifest = generate()
    raw.to_csv(data / "retail_raw.csv", index=False)
    manifest.to_csv(data / "defect_manifest.csv", index=False)
