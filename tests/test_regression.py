"""
Automated Regression Tests for YottaFlex Return Management System (RMS)
Verifies prevention of known past defects, specifically penny-drift rounding errors and multi-step partial returns.
"""

import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from src.engines.refund import RefundEngine
from src.engines.eligibility import EligibilityEngine


class TestRefundReconciliationRegression(unittest.TestCase):
    def test_two_identical_lines_penny_rounding_drift_prevented(self):
        """
        Regression Test for Bug #1:
        Order: subtotal 178.00, discount 8.90, tax 13.53, total_paid 182.63.
        Returning two lines of 89.00 each previously caused tax to round up to 6.77 each,
        yielding 13.54 tax and 182.64 net refund (exceeding total_paid 182.63).
        With Decimal aggregate proration, net refund must equal total_paid exactly.
        """
        now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        order = {
            "order_id": "ORD-2026-REGRESS-01",
            "subtotal_amount": "178.00",
            "discount_amount": "8.90",
            "tax_amount": "13.53",
            "shipping_fee": "0.00",
            "total_paid_amount": "182.63"
        }
        lines = [
            {
                "return_line_id": "RMAL-REGRESS-01",
                "approved_quantity": 1,
                "purchased_quantity": 1,
                "line_subtotal": "89.00",
                "unit_price": "89.00",
                "category": "APPAREL",
                "return_reason": "ARRIVED_LATE"
            },
            {
                "return_line_id": "RMAL-REGRESS-02",
                "approved_quantity": 1,
                "purchased_quantity": 1,
                "line_subtotal": "89.00",
                "unit_price": "89.00",
                "category": "APPAREL",
                "return_reason": "ARRIVED_LATE"
            }
        ]

        result = RefundEngine.calculate_refund(
            refund_id="REF-2026-REGRESS",
            rma_id="RMA-2026-REGRESS",
            customer_id="CUST-000001",
            refund_date=now,
            order=order,
            approved_lines=lines,
            force_excess_anomaly=False
        )

        self.assertEqual(result.gross_item_amount, Decimal("178.00"))
        self.assertEqual(result.prorated_discount, Decimal("8.90"))
        self.assertEqual(result.tax_refund_amount, Decimal("13.53"))
        self.assertEqual(result.restocking_fee, Decimal("0.00"))
        self.assertEqual(result.net_refund_amount, Decimal("182.63"))
        self.assertEqual(result.net_refund_amount, Decimal(order["total_paid_amount"]))

    def test_non_refundable_shipping_fee_preserved(self):
        """
        When customer returns all items on an order with a shipping fee,
        the refund must equal subtotal - discount + tax, NOT including shipping fee.
        """
        now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        order = {
            "order_id": "ORD-2026-REGRESS-02",
            "subtotal_amount": "50.00",
            "discount_amount": "0.00",
            "tax_amount": "4.00",
            "shipping_fee": "9.99",
            "total_paid_amount": "63.99"
        }
        lines = [{
            "return_line_id": "RMAL-REGRESS-03",
            "approved_quantity": 1,
            "purchased_quantity": 1,
            "line_subtotal": "50.00",
            "unit_price": "50.00",
            "category": "APPAREL",
            "return_reason": "DOES_NOT_FIT"
        }]

        result = RefundEngine.calculate_refund(
            refund_id="REF-2026-REGRESS-02",
            rma_id="RMA-2026-REGRESS-02",
            customer_id="CUST-000001",
            refund_date=now,
            order=order,
            approved_lines=lines,
            force_excess_anomaly=False
        )

        # Net refund must be 54.00 (50 subtotal + 4 tax), strictly less than total paid 63.99
        self.assertEqual(result.net_refund_amount, Decimal("54.00"))
        self.assertLess(result.net_refund_amount, Decimal(order["total_paid_amount"]))


class TestMultiStepPartialReturnsRegression(unittest.TestCase):
    def test_multi_step_partial_returns_deplete_purchased_quantity(self):
        """
        Order Line: purchased quantity = 3.
        Step 1: Return 1 unit -> approved.
        Step 2: Return 2 units -> approved.
        Step 3: Return 1 unit -> rejected because remaining returnable quantity is 0.
        """
        now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        delivery_dt = now - timedelta(days=5)

        # Step 1
        res1 = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=delivery_dt,
            request_date=now,
            category="APPAREL",
            is_final_sale=False,
            customer_tier="STANDARD",
            purchased_quantity=3,
            previously_returned_quantity=0,
            requested_quantity=1
        )
        self.assertTrue(res1.is_eligible)
        self.assertEqual(res1.approved_quantity, 1)

        # Step 2
        res2 = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=delivery_dt,
            request_date=now,
            category="APPAREL",
            is_final_sale=False,
            customer_tier="STANDARD",
            purchased_quantity=3,
            previously_returned_quantity=1,
            requested_quantity=2
        )
        self.assertTrue(res2.is_eligible)
        self.assertEqual(res2.approved_quantity, 2)

        # Step 3
        res3 = EligibilityEngine.evaluate_line_eligibility(
            order_status="DELIVERED",
            delivery_date=delivery_dt,
            request_date=now,
            category="APPAREL",
            is_final_sale=False,
            customer_tier="STANDARD",
            purchased_quantity=3,
            previously_returned_quantity=3,
            requested_quantity=1
        )
        self.assertFalse(res3.is_eligible)
        self.assertEqual(res3.decision, "REJECTED")
        self.assertIn("REQUESTED_QTY_EXCEEDS_PURCHASED", res3.rejection_reason)


if __name__ == "__main__":
    unittest.main()

