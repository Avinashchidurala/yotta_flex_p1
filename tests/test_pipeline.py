"""
Integration Tests for Synthetic Generation Pipeline and Validation Suite
Updated with 12 canonical entities and 5 dedicated anomaly datasets.
"""

import unittest
from pathlib import Path
import shutil
from src.config import DATABASE_PATH, GROUND_TRUTH_DIR
from src.generator.synthetic_data import SyntheticDataGenerator
from src.validation.validator import AuditValidator, compute_dataset_checksum


class TestPipelineIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = Path("data/test_integration.db")
        cls.test_gt_dir = Path("data/test_gt")
        cls.test_raw_dir = Path("data/test_raw")
        cls.test_anom_dir = Path("data/test_anom")

        if cls.test_db.exists():
            cls.test_db.unlink()

        cls.gen = SyntheticDataGenerator(scale="starter", seed=20261022)
        cls.counts = cls.gen.generate_all()
        cls.gen.persist_to_database(cls.test_db)
        cls.gen.export_csv_and_json(cls.test_raw_dir, cls.test_gt_dir, cls.test_anom_dir)

    @classmethod
    def tearDownClass(cls):
        if cls.test_db.exists():
            cls.test_db.unlink()
        if cls.test_raw_dir.exists():
            shutil.rmtree(cls.test_raw_dir, ignore_errors=True)
        if cls.test_gt_dir.exists():
            shutil.rmtree(cls.test_gt_dir, ignore_errors=True)
        if cls.test_anom_dir.exists():
            shutil.rmtree(cls.test_anom_dir, ignore_errors=True)

    def test_row_counts_generated(self):
        self.assertEqual(self.counts["orders"], 375)
        self.assertEqual(self.counts["return_requests"], 63)
        self.assertGreaterEqual(self.counts["return_lines"], 90)
        self.assertEqual(self.counts["products"], 16)
        self.assertGreater(self.counts["return_events"], 100)

    def test_audit_validation_passes(self):
        validator = AuditValidator(self.test_db, self.test_gt_dir / "ground_truth.json")
        report = validator.run_full_audit()
        validator.close()

        self.assertEqual(report["checks_failed"], 0)
        self.assertGreater(report["checks_passed"], 40)

        # Assert 100% recall on injected anomalies
        evals = report["anomaly_evaluation"]
        for anomaly_type, metrics in evals.items():
            self.assertEqual(metrics["recall"], 1.0, f"Recall was less than 1.0 for {anomaly_type}")
            self.assertEqual(metrics["precision"], 1.0, f"Precision was less than 1.0 for {anomaly_type}")

    def test_seed_reproducibility(self):
        db2 = Path("data/test_repro.db")
        if db2.exists():
            db2.unlink()

        gen2 = SyntheticDataGenerator(scale="starter", seed=20261022)
        counts2 = gen2.generate_all()
        gen2.persist_to_database(db2)

        chk1 = compute_dataset_checksum(self.test_db)
        chk2 = compute_dataset_checksum(db2)

        self.assertEqual(self.counts, counts2)
        self.assertEqual(chk1, chk2)

        db2.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
