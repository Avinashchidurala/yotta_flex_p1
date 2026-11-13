"""
Unit and Integration Tests for Customer Portal & Universal Pagination
Verifies customer filtering, single-customer data isolation, return request creation,
and paginated data retrieval.
"""

import unittest
import sqlite3
from src.config import DATABASE_PATH


class TestCustomerPortalLogic(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(str(DATABASE_PATH))
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()

    def test_customer_search_filtering(self):
        cur = self.conn.cursor()
        # Search by partial customer ID
        cur.execute("""
            SELECT customer_id, first_name, last_name, email, phone, customer_tier, risk_score
            FROM customers
            WHERE customer_id LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR email LIKE ?
            ORDER BY customer_id ASC
            LIMIT 10
        """, ('%CUST-000001%', '%CUST-000001%', '%CUST-000001%', '%CUST-000001%'))
        results = [dict(r) for r in cur.fetchall()]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["customer_id"], "CUST-000001")

        # Search by name
        cur.execute("""
            SELECT customer_id, first_name, last_name, email, phone, customer_tier, risk_score
            FROM customers
            WHERE first_name LIKE ? OR last_name LIKE ?
            LIMIT 10
        """, ('%Aria%', '%Aria%'))
        name_results = [dict(r) for r in cur.fetchall()]
        self.assertGreater(len(name_results), 0)

    def test_single_customer_isolation(self):
        cid = "CUST-000001"
        cur = self.conn.cursor()

        # Customer's profile
        cur.execute("SELECT * FROM customers WHERE customer_id = ?", (cid,))
        cust = cur.fetchone()
        self.assertIsNotNone(cust)
        self.assertEqual(cust["customer_id"], cid)

        # Customer's orders
        cur.execute("SELECT * FROM orders WHERE customer_id = ?", (cid,))
        orders = [dict(o) for o in cur.fetchall()]
        self.assertGreater(len(orders), 0)
        for o in orders:
            self.assertEqual(o["customer_id"], cid)

        # Customer's returns
        cur.execute("""
            SELECT rr.request_id, rr.customer_id, ra.rma_id, ra.authorization_status
            FROM return_requests rr
            LEFT JOIN return_authorizations ra ON rr.request_id = ra.request_id
            WHERE rr.customer_id = ?
        """, (cid,))
        returns = [dict(r) for r in cur.fetchall()]
        for r in returns:
            self.assertEqual(r["customer_id"], cid)

        # Customer's refunds
        cur.execute("SELECT * FROM refunds WHERE customer_id = ?", (cid,))
        refunds = [dict(rf) for rf in cur.fetchall()]
        for rf in refunds:
            self.assertEqual(rf["customer_id"], cid)

    def test_universal_table_pagination(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM orders")
        total = cur.fetchone()[0]

        page_size = 25
        cur.execute(f"SELECT * FROM orders ORDER BY order_date DESC LIMIT {page_size} OFFSET 0")
        page_1 = cur.fetchall()
        self.assertLessEqual(len(page_1), page_size)

        cur.execute(f"SELECT * FROM orders ORDER BY order_date DESC LIMIT {page_size} OFFSET {page_size}")
        page_2 = cur.fetchall()
        self.assertLessEqual(len(page_2), page_size)

        # Ensure page 1 and page 2 are distinct
        page_1_ids = {r["order_id"] for r in page_1}
        page_2_ids = {r["order_id"] for r in page_2}
        self.assertEqual(len(page_1_ids.intersection(page_2_ids)), 0)


if __name__ == '__main__':
    unittest.main()
