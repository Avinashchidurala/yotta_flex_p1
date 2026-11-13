"""
Automated Negative Tests for YottaFlex Return Management System (RMS)
Verifies that all invariant violations, invalid states, and financial overflows are strictly blocked.
"""

import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from src.engines.eligibility import EligibilityEngine
from src.engines.refund import RefundEngine
from src.engines.inspection import InspectionEngine
from src.engines.disposition import DispositionEngine


class TestNegativeScenarios(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.delivery_dt = self.now - timedelta(days=5)

    def test_non_delivered_order_rejected(self):
        """Returns against non-delivered orders must be strictly REJECTED."""
        for invalid_status in ["SHIPPED", "CANCELLED", "PENDING"]:
            res = EligibilityEngine.evaluate_line_eligibility(
                order_status=invalid_status,
                delivery_date=None,
                request_date=self.now,
                category="APPAREL",
                is_final_sale=False,
                customer_tier="STANDARD",
                purchased_quantity=1,
                previously_returned_quantity=0,
                requested_quantity=1
            )
            self.assertFalse(res.is_eligible)
            self.assertEqual(res.decision, "REJECTED")
            self.assertEqual(res.rejection_reason, "ORDER_NOT_DELIVERED")

    def test_perishable_category_rejected(self):
        """Perishable food/beverage items must be non-returnable."""
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=self.delivery_dt,
            request_date=self.now,
            category="PERISHABLE",
            is_final_sale=True,
            customer_tier="STANDARD",
            purchased_quantity=2,
            previously_returned_quantity=0,
            requested_quantity=1
        )
        self.assertFalse(res.is_eligible)
        self.assertEqual(res.decision, "REJECTED")
        self.assertIn("CATEGORY_NON_RETURNABLE", res.rejection_reason)

    def test_excess_refund_raises_strict_value_error(self):
        """Under normal execution, net refund exceeding order paid amount raises ValueError."""
        order = {
            "subtotal_amount": "100.00",
            "discount_amount": "0.00",
            "tax_amount": "8.00",
            "shipping_fee": "0.00",
            "total_paid_amount": "50.00"  # Artificially low paid amount to test invariant
        }
        lines = [{
            "approved_quantity": 1,
            "unit_price": "100.00",
            "category": "APPAREL",
            "return_reason": "DEFECTIVE"
        }]

        with self.assertRaises(ValueError) as ctx:
            RefundEngine.calculate_refund(
                refund_id="REF-2026-TEST",
                rma_id="RMA-2026-TEST",
                customer_id="CUST-000001",
                refund_date=self.now,
                order=order,
                approved_lines=lines,
                force_excess_anomaly=False
            )
        self.assertIn("Financial reconciliation violation", str(ctx.exception))

    def test_premature_restocking_raises_strict_value_error(self):
        """Disposition before inspection date raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            DispositionEngine.determine_disposition(
                disposition_id="DISP-2026-TEST",
                inspection_id="INS-2026-TEST",
                rma_id="RMA-2026-TEST",
                inspection_date=self.now,
                disposition_date=self.now - timedelta(hours=5),
                item_grade="GRADE_A_NEW",
                unit_price=Decimal("100.00"),
                force_anomaly=False
            )
        self.assertIn("Temporal invariant violation", str(ctx.exception))

    def test_counterfeit_item_quarantined_zero_recovery(self):
        """Counterfeit inspection grades must route to QUARANTINE_FRAUD with $0 recovery."""
        disp = DispositionEngine.determine_disposition(
            disposition_id="DISP-2026-TEST",
            inspection_id="INS-2026-TEST",
            rma_id="RMA-2026-TEST",
            inspection_date=self.now,
            disposition_date=self.now + timedelta(hours=2),
            item_grade="COUNTERFEIT_FRAUD",
            unit_price=Decimal("299.99"),
            force_anomaly=False
        )
        self.assertEqual(disp.disposition_action, "QUARANTINE_FRAUD")
        self.assertEqual(disp.unit_cost_recovery, Decimal("0.00"))
        self.assertEqual(disp.target_bin_location, "BIN-QUARANTINE-Q9")


if __name__ == "__main__":
    unittest.main()

