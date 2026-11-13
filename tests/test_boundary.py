"""
Automated Boundary Tests for YottaFlex Return Management System (RMS)
Tests exact policy window boundaries and quantity threshold boundaries.
"""

import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from src.engines.eligibility import EligibilityEngine


class TestReturnWindowBoundaries(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_electronics_day_14_boundary_approved(self):
        """Electronics on exact 14th calendar day must be APPROVED."""
        delivery_dt = self.now - timedelta(days=14)
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=delivery_dt,
            request_date=self.now,
            category="ELECTRONICS",
            is_final_sale=False,
            customer_tier="STANDARD",
            purchased_quantity=1,
            previously_returned_quantity=0,
            requested_quantity=1
        )
        self.assertTrue(res.is_eligible)
        self.assertEqual(res.decision, "APPROVED")
        self.assertEqual(res.applied_return_window_days, 14)

    def test_electronics_day_15_boundary_rejected(self):
        """Electronics on 15th calendar day must be REJECTED."""
        delivery_dt = self.now - timedelta(days=15)
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=delivery_dt,
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

    def test_apparel_day_30_boundary_approved(self):
        """Apparel on exact 30th calendar day must be APPROVED."""
        delivery_dt = self.now - timedelta(days=30)
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=delivery_dt,
            request_date=self.now,
            category="APPAREL",
            is_final_sale=False,
            customer_tier="STANDARD",
            purchased_quantity=2,
            previously_returned_quantity=0,
            requested_quantity=2
        )
        self.assertTrue(res.is_eligible)
        self.assertEqual(res.decision, "APPROVED")

    def test_apparel_day_31_boundary_rejected(self):
        """Apparel on 31st calendar day must be REJECTED."""
        delivery_dt = self.now - timedelta(days=31)
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=delivery_dt,
            request_date=self.now,
            category="APPAREL",
            is_final_sale=False,
            customer_tier="STANDARD",
            purchased_quantity=2,
            previously_returned_quantity=0,
            requested_quantity=2
        )
        self.assertFalse(res.is_eligible)
        self.assertEqual(res.decision, "REJECTED")

    def test_vip_tier_day_60_boundary_approved(self):
        """VIP Customer Tier gets 60-day window: Day 60 must be APPROVED."""
        delivery_dt = self.now - timedelta(days=60)
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=delivery_dt,
            request_date=self.now,
            category="HOME_GOODS",
            is_final_sale=False,
            customer_tier="VIP",
            purchased_quantity=1,
            previously_returned_quantity=0,
            requested_quantity=1
        )
        self.assertTrue(res.is_eligible)
        self.assertEqual(res.decision, "APPROVED")
        self.assertEqual(res.applied_return_window_days, 60)

    def test_vip_tier_day_61_boundary_rejected(self):
        """VIP Customer Tier on Day 61 must be REJECTED."""
        delivery_dt = self.now - timedelta(days=61)
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=delivery_dt,
            request_date=self.now,
            category="HOME_GOODS",
            is_final_sale=False,
            customer_tier="VIP",
            purchased_quantity=1,
            previously_returned_quantity=0,
            requested_quantity=1
        )
        self.assertFalse(res.is_eligible)
        self.assertEqual(res.decision, "REJECTED")


class TestQuantityBoundaries(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.delivery_dt = self.now - timedelta(days=5)

    def test_exact_purchased_quantity_approved(self):
        """Requested qty equal to purchased qty is APPROVED."""
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=self.delivery_dt,
            request_date=self.now,
            category="APPAREL",
            is_final_sale=False,
            customer_tier="STANDARD",
            purchased_quantity=3,
            previously_returned_quantity=0,
            requested_quantity=3
        )
        self.assertTrue(res.is_eligible)
        self.assertEqual(res.approved_quantity, 3)

    def test_requested_quantity_plus_one_rejected(self):
        """Requested qty equal to purchased qty + 1 is REJECTED."""
        res = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=self.delivery_dt,
            request_date=self.now,
            category="APPAREL",
            is_final_sale=False,
            customer_tier="STANDARD",
            purchased_quantity=3,
            previously_returned_quantity=0,
            requested_quantity=4
        )
        self.assertFalse(res.is_eligible)
        self.assertEqual(res.decision, "REJECTED")
        self.assertIn("REQUESTED_QTY_EXCEEDS_PURCHASED", res.rejection_reason)


if __name__ == "__main__":
    unittest.main()

