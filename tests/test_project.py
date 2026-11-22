from pathlib import Path
import json
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

from audit import load, metrics, privacy, readiness
from clean import clean
from generate import generate

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.raw = load(DATA / "retail_raw.csv")
        self.cleaned = load(DATA / "retail_clean.csv")

    def test_generation_and_defect_counts(self):
        generated, manifest = generate()
        self.assertEqual(generated.to_csv(index=False, lineterminator="\n"), (DATA / "retail_raw.csv").read_text())
        self.assertEqual(manifest.to_csv(index=False, lineterminator="\n"), (DATA / "defect_manifest.csv").read_text())
        self.assertEqual(len(generated), 1000)
        self.assertEqual(len(manifest), 123)
        raw = metrics(self.raw)
        self.assertEqual(raw["passing_rows"], 877)
        self.assertEqual(raw["price_iqr_outliers"], 8)

    def test_cleaning_and_audit_reconcile(self):
        result, log = clean(self.raw)
        pd.testing.assert_frame_equal(result, self.cleaned)
        self.assertEqual(log.action.value_counts().to_dict(), {
            "retained": 877, "quarantined": 70, "standardized": 33, "removed duplicate": 20
        })
        pd.testing.assert_frame_equal(clean(result)[0], result)
        report = json.loads((DATA / "audit.json").read_text())
        self.assertEqual(report["raw"], metrics(self.raw))
        self.assertEqual(report["clean"], metrics(result))
        self.assertEqual(report["clean"]["passing_rows"], 910)
        self.assertEqual(len(load(DATA / "quarantine.csv")), 70)

    def test_conflicting_ids_are_quarantined(self):
        sample = self.cleaned.iloc[[0, 0]].reset_index(drop=True)
        sample.loc[1, "quantity"] = "9"
        result, log = clean(sample)
        self.assertTrue(result.empty)
        self.assertEqual(log.action.tolist(), ["quarantined", "quarantined"])

    def test_privacy_and_model_checks(self):
        self.assertEqual(set(privacy(self.cleaned).values()), {0})
        augmented = self.cleaned.assign(email="person@example.com")
        self.assertEqual(privacy(augmented)["Email-like cells"], 910)
        self.assertEqual(privacy(augmented)["Unexpected columns"], 1)
        regions, checks = readiness(self.cleaned)
        self.assertAlmostEqual(regions.share.sum(), 1.0)
        self.assertEqual(checks["refund_signal_agreement"], 1.0)
        self.assertNotIn("refund_amount", checks["recommended_features"])
        self.assertEqual(checks["shared_transaction_ids"], 0)
        self.assertEqual(checks["train_rows"] + checks["holdout_rows"], 910)

    def test_streamlit_widgets(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Data Quality Detective")
        self.assertEqual(len(app.tabs), 4)
        self.assertEqual(len(app.get("download_button")), 6)
        app.selectbox[0].select("Extra exact copies").run()
        self.assertFalse(app.exception)
        self.assertTrue(any(c.value == "20 matching records" for c in app.caption))
        app.radio[0].set_value("Clean").run()
        self.assertFalse(app.exception)
        self.assertTrue(any(c.value == "0 matching records" for c in app.caption))
        app.selectbox[0].select("All rows").run()
        app.text_input[0].set_value("T00980").run()
        self.assertTrue(any(c.value == "1 matching records" for c in app.caption))


if __name__ == "__main__":
    unittest.main()
