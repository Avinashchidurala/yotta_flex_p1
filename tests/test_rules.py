"""
Unit Tests for Reverse Logistics Business Rules Engines
Updated with Decimal currency precision.
"""

import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from src.engines.eligibility import EligibilityEngine
from src.engines.refund import RefundEngine
from src.engines.disposition import DispositionEngine


class TestEligibilityEngine(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.delivery_date = self.now - timedelta(days=10)

    def test_standard_apparel_return_within_window(self):
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=self.delivery_date,
            request_date=self.now,
            category="APPAREL",
            is_final_sale=False,
            customer_tier="STANDARD",
            purchased_quantity=2,
            previously_returned_quantity=0,
            requested_quantity=1
        )
        self.assertTrue(res.is_eligible)
        self.assertEqual(res.decision, "APPROVED")
        self.assertEqual(res.approved_quantity, 1)

    def test_electronics_outside_14_day_window_rejected(self):
        late_delivery = self.now - timedelta(days=20)
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=late_delivery,
            request_date=self.now,
            category="ELECTRONICS",
            is_final_sale=False,
            customer_tier="STANDARD",
            purchased_quantity=1,
            previously_returned_quantity=0,
            requested_quantity=1
        )
        self.assertFalse(res.is_eligible)
        self.assertEqual(res.decision, "REJECTED")
        self.assertIn("OUTSIDE_RETURN_WINDOW", res.rejection_reason)

    def test_manager_override_allows_outside_window(self):
        late_delivery = self.now - timedelta(days=45)
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=late_delivery,
            request_date=self.now,
            category="ELECTRONICS",
            is_final_sale=False,
            customer_tier="STANDARD",
            purchased_quantity=1,
            previously_returned_quantity=0,
            requested_quantity=1,
            manager_override=True,
            override_reason="Customer goodwill approved by OPS_MANAGER_01"
        )
        self.assertTrue(res.is_eligible)
        self.assertEqual(res.decision, "APPROVED")
        self.assertTrue(res.is_override)

    def test_perishable_is_non_returnable(self):
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=self.delivery_date,
            request_date=self.now,
            category="PERISHABLE",
            is_final_sale=True,
            customer_tier="STANDARD",
            purchased_quantity=1,
            previously_returned_quantity=0,
            requested_quantity=1
        )
        self.assertFalse(res.is_eligible)
        self.assertEqual(res.decision, "REJECTED")


class TestRefundEngine(unittest.TestCase):
    def test_refund_arithmetic_reconciliation(self):
        now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        order = {
            "subtotal_amount": "200.00",
            "discount_amount": "20.00",
            "tax_amount": "14.40",  # 8% tax on 180.00
            "shipping_fee": "0.00",
            "total_paid_amount": "194.40"
        }
        lines = [{
            "approved_quantity": 1,
            "unit_price": "100.00",
            "line_subtotal": "100.00",
            "purchased_quantity": 1,
            "category": "APPAREL",
            "return_reason": "DEFECTIVE"
        }]
        res = RefundEngine.calculate_refund(
            refund_id="REF-2026-000001",
            rma_id="RMA-2026-000001",
            customer_id="CUST-000001",
            refund_date=now,
            order=order,
            approved_lines=lines
        )
        self.assertEqual(res.gross_item_amount, Decimal("100.00"))
        self.assertEqual(res.prorated_discount, Decimal("10.00"))
        self.assertEqual(res.tax_refund_amount, Decimal("7.20"))
        self.assertEqual(res.restocking_fee, Decimal("0.00"))
        self.assertEqual(res.net_refund_amount, Decimal("97.20"))
        self.assertLessEqual(res.net_refund_amount, Decimal(order["total_paid_amount"]))


class TestDispositionEngine(unittest.TestCase):
    def test_disposition_grade_mapping(self):
        now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        res = DispositionEngine.determine_disposition(
            disposition_id="DISP-2026-000001",
            inspection_id="INS-2026-000001",
            rma_id="RMA-2026-000001",
            inspection_date=now,
            disposition_date=now + timedelta(hours=2),
            item_grade="GRADE_A_NEW",
            unit_price=Decimal("100.00")
        )
        self.assertEqual(res.disposition_action, "RESTOCK_PRIMARY")
        self.assertEqual(res.unit_cost_recovery, Decimal("100.00"))
        self.assertFalse(res.is_temporal_anomaly)

    def test_temporal_violation_raises_error(self):
        now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            DispositionEngine.determine_disposition(
                disposition_id="DISP-2026-000002",
                inspection_id="INS-2026-000002",
                rma_id="RMA-2026-000001",
                inspection_date=now,
                disposition_date=now - timedelta(hours=2),
                item_grade="GRADE_A_NEW",
                unit_price=Decimal("100.00"),
                force_anomaly=False
            )


if __name__ == "__main__":
    unittest.main()
