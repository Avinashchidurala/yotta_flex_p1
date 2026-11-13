"""
Deterministic Synthetic Data Pipeline & Anomaly Injector
Fixed Seed: 20261022
Scaled: +25% over baseline (Orders: 37,500, Requests: 6,250, Return Lines: 10,000, Customers: 15,000)
Outputs 12 canonical entities + 5 dedicated anomaly datasets + unified ground truth.
"""

import random
import csv
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP

from src.config import (
    BASE_DIR, DATA_DIR, RAW_DATA_DIR, GROUND_TRUTH_DIR, ANOMALIES_DIR,
    DATABASE_PATH, RANDOM_SEED, SCALE_CONFIGS, CATEGORY_RETURN_WINDOWS,
    CUSTOMER_TIERS, PAYMENT_METHODS, ORDER_STATUSES, RETURN_REASONS,
    ITEM_CONDITIONS, WAREHOUSES, CARRIERS, ITEM_GRADES, CANONICAL_PRODUCTS
)
from src.models import init_database
from src.engines.eligibility import EligibilityEngine
from src.engines.authorization import AuthorizationEngine
from src.engines.inspection import InspectionEngine
from src.engines.disposition import DispositionEngine
from src.engines.refund import RefundEngine, quantize_money, to_decimal

FIRST_NAMES = [
    "Liam", "Olivia", "Noah", "Emma", "Oliver", "Charlotte", "Elijah", "Amelia", "James", "Sophia",
    "William", "Isabella", "Benjamin", "Mia", "Lucas", "Evelyn", "Henry", "Harper", "Alexander", "Camila",
    "Daniel", "Aria", "Matthew", "Scarlett", "Jackson", "Victoria", "Sebastian", "Madison", "Jack", "Luna"
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"
]


class SyntheticDataGenerator:
    def __init__(self, scale: str = "starter", seed: int = RANDOM_SEED):
        if scale not in SCALE_CONFIGS:
            raise ValueError(f"Unknown scale: {scale}. Choose from {list(SCALE_CONFIGS.keys())}")
        self.scale_cfg = SCALE_CONFIGS[scale]
        self.seed = seed
        self.rng = random.Random(seed)

        # In-memory datasets for generation
        self.products: List[Dict[str, Any]] = []
        self.customers: List[Dict[str, Any]] = []
        self.orders: List[Dict[str, Any]] = []
        self.order_lines: List[Dict[str, Any]] = []
        self.return_requests: List[Dict[str, Any]] = []
        self.return_lines: List[Dict[str, Any]] = []
        self.return_authorizations: List[Dict[str, Any]] = []
        self.return_shipments: List[Dict[str, Any]] = []
        self.inspections: List[Dict[str, Any]] = []
        self.inventory_dispositions: List[Dict[str, Any]] = []
        self.refunds: List[Dict[str, Any]] = []
        self.return_events: List[Dict[str, Any]] = []
        self.ground_truth_anomalies: List[Dict[str, Any]] = []

    def generate_all(self) -> Dict[str, int]:
        """Runs the complete end-to-end generation sequence."""
        self._init_products()
        self._generate_master_data()
        self._generate_returns_and_events()
        return self.get_summary_counts()

    def _init_products(self):
        """Initializes canonical products master dataset."""
        base_time = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat()
        self.products = []
        for p in CANONICAL_PRODUCTS:
            self.products.append({
                "sku": p["sku"],
                "product_name": p["product_name"],
                "category": p["category"],
                "unit_price": str(quantize_money(p["unit_price"])),
                "is_returnable": 1 if p["is_returnable"] else 0,
                "return_window_days": p["return_window_days"],
                "restock_fee_rate": str(quantize_money(p["restock_fee_rate"])),
                "created_at": base_time
            })

    def _generate_master_data(self):
        """Generates customers, orders, and order lines with exact Decimal arithmetic."""
        num_orders = self.scale_cfg.num_orders
        num_customers = self.scale_cfg.num_customers

        base_start_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        # 1. Customers
        for i in range(1, num_customers + 1):
            c_id = f"CUST-{i:06d}"
            fn = self.rng.choice(FIRST_NAMES)
            ln = self.rng.choice(LAST_NAMES)
            created_at = base_start_time + timedelta(days=self.rng.randint(0, 60))
            self.customers.append({
                "customer_id": c_id,
                "first_name": fn,
                "last_name": ln,
                "email": f"{fn.lower()}.{ln.lower()}{i}@example.com",
                "phone": f"+1555{self.rng.randint(1000000, 9999999)}",
                "customer_tier": self.rng.choices(CUSTOMER_TIERS, weights=[0.70, 0.18, 0.08, 0.04])[0],
                "risk_score": round(self.rng.betavariate(1.5, 8.0), 3),
                "created_at": created_at.isoformat()
            })

        # 2. Orders and Lines
        for i in range(1, num_orders + 1):
            order_id = f"ORD-2026-{i:06d}"
            customer = self.rng.choice(self.customers)
            cust_created = datetime.fromisoformat(customer["created_at"])
            order_date = cust_created + timedelta(days=self.rng.randint(1, 120), hours=self.rng.randint(0, 23))

            status = self.rng.choices(ORDER_STATUSES, weights=[0.88, 0.08, 0.04])[0]
            delivery_date = None
            if status == "DELIVERED":
                delivery_date = (order_date + timedelta(days=self.rng.randint(2, 6))).isoformat()

            num_lines = self.rng.choices([1, 2, 3, 4], weights=[0.55, 0.28, 0.12, 0.05])[0]
            subtotal = Decimal("0.00")

            for line_idx in range(1, num_lines + 1):
                prod = self.rng.choice(CANONICAL_PRODUCTS)
                qty = self.rng.choices([1, 2, 3], weights=[0.80, 0.15, 0.05])[0]
                unit_price = quantize_money(prod["unit_price"])

                # Line discount: 10% coupon on 20% of purchases
                line_discount = quantize_money(unit_price * Decimal(str(qty)) * Decimal("0.10")) if self.rng.random() < 0.20 else Decimal("0.00")
                line_subtotal = quantize_money((unit_price * Decimal(str(qty))) - line_discount)
                subtotal += line_subtotal

                cat = prod["category"]
                win_days = CATEGORY_RETURN_WINDOWS.get(cat, 30)
                is_fs = not prod["is_returnable"]

                line_rec = {
                    "order_line_id": f"ORDL-{order_id}-{line_idx:02d}",
                    "order_id": order_id,
                    "line_number": line_idx,
                    "sku": prod["sku"],
                    "product_name": prod["product_name"],
                    "category": cat,
                    "unit_price": str(unit_price),
                    "quantity": qty,
                    "line_discount": str(line_discount),
                    "line_subtotal": str(line_subtotal),
                    "return_window_days": win_days,
                    "is_final_sale": 1 if is_fs else 0
                }
                self.order_lines.append(line_rec)

            # Order-level cart discount
            cart_discount = quantize_money(subtotal * Decimal("0.05")) if self.rng.random() < 0.15 else Decimal("0.00")
            tax_rate = Decimal("0.08")
            taxable_amount = max(Decimal("0.00"), subtotal - cart_discount)
            tax_amount = quantize_money(taxable_amount * tax_rate)
            shipping_fee = Decimal("0.00") if subtotal >= Decimal("75.00") else Decimal("9.99")
            total_paid = quantize_money(subtotal - cart_discount + tax_amount + shipping_fee)

            self.orders.append({
                "order_id": order_id,
                "customer_id": customer["customer_id"],
                "order_date": order_date.isoformat(),
                "currency": "USD",
                "subtotal_amount": str(subtotal),
                "discount_amount": str(cart_discount),
                "tax_amount": str(tax_amount),
                "shipping_fee": str(shipping_fee),
                "total_paid_amount": str(total_paid),
                "payment_method": self.rng.choice(PAYMENT_METHODS),
                "order_status": status,
                "delivery_date": delivery_date
            })

    def _generate_returns_and_events(self):
        """Generates Return Requests, RMAs, Shipments, Inspections, Dispositions, Refunds & Events."""
        num_requests = self.scale_cfg.num_return_requests
        target_lines = self.scale_cfg.num_return_lines

        delivered_orders = [o for o in self.orders if o["order_status"] == "DELIVERED" and o["delivery_date"] is not None]
        order_to_lines = {}
        for l in self.order_lines:
            order_to_lines.setdefault(l["order_id"], []).append(l)

        # Equal distribution of anomalies (~1% each = 63 per anomaly type for full scale)
        target_anomaly_each = max(2, int(num_requests * 0.01))
        anomaly_targets = {
            "QTY_EXCEEDS_PURCHASED": target_anomaly_each,
            "REFUND_EXCEEDS_PAID": target_anomaly_each,
            "RESTOCK_BEFORE_INSPECTION": target_anomaly_each,
            "RETURN_PAST_POLICY_WINDOW": target_anomaly_each,
            "DUPLICATE_REFUND_ATTEMPT": target_anomaly_each
        }
        anomaly_counts = {k: 0 for k in anomaly_targets}

        # Multi-line order allocation to hit target return lines exactly
        multi_line_orders = [o for o in delivered_orders if len(order_to_lines.get(o["order_id"], [])) >= 2]
        single_line_orders = [o for o in delivered_orders if len(order_to_lines.get(o["order_id"], [])) == 1]

        needed_extra_lines = max(0, target_lines - num_requests)
        needed_multi = min(len(multi_line_orders), needed_extra_lines)
        needed_single = max(0, num_requests - needed_multi)

        selected_multi = self.rng.sample(multi_line_orders, needed_multi) if needed_multi <= len(multi_line_orders) else multi_line_orders
        remaining_pool = [o for o in delivered_orders if o not in selected_multi]
        selected_single = self.rng.sample(remaining_pool, min(needed_single, len(remaining_pool)))
        selected_orders = selected_multi + selected_single
        self.rng.shuffle(selected_orders)

        req_counter = 1
        return_line_counter = 1
        rma_counter = 1
        shipment_counter = 1
        insp_counter = 1
        disp_counter = 1
        refund_counter = 1
        anomaly_counter = 1
        event_counter = 1

        for req_idx, order in enumerate(selected_orders, start=1):
            req_id = f"REQ-2026-{req_counter:06d}"
            rma_id = f"RMA-2026-{rma_counter:06d}"
            req_counter += 1
            rma_counter += 1

            delivery_dt = datetime.fromisoformat(order["delivery_date"])
            order_lines = order_to_lines.get(order["order_id"], [])
            if not order_lines:
                continue

            # Check RETURN_PAST_POLICY_WINDOW anomaly
            inject_late_window = (anomaly_counts["RETURN_PAST_POLICY_WINDOW"] < anomaly_targets["RETURN_PAST_POLICY_WINDOW"] and self.rng.random() < 0.15)
            if inject_late_window:
                request_dt = delivery_dt + timedelta(days=self.rng.randint(65, 95))
                anomaly_counts["RETURN_PAST_POLICY_WINDOW"] += 1
                self.ground_truth_anomalies.append({
                    "anomaly_id": f"ANO-{anomaly_counter:06d}",
                    "entity_name": "return_requests",
                    "entity_id": req_id,
                    "parent_entity_id": order["order_id"],
                    "issue_type": "RETURN_PAST_POLICY_WINDOW",
                    "expected_decision": "REJECTED_OR_OVERRIDE_REQUIRED",
                    "actual_injected_behavior": f"Submitted at day {(request_dt - delivery_dt).days} without override",
                    "created_at": request_dt.isoformat()
                })
                anomaly_counter += 1
            else:
                request_dt = delivery_dt + timedelta(days=self.rng.randint(1, 10))

            req_record = {
                "request_id": req_id,
                "order_id": order["order_id"],
                "customer_id": order["customer_id"],
                "request_date": request_dt.isoformat(),
                "request_channel": self.rng.choice(["WEB_PORTAL", "MOBILE_APP", "CUSTOMER_SERVICE"]),
                "request_status": "SUBMITTED",
                "customer_notes": "Return requested."
            }
            self.return_requests.append(req_record)

            # Log Event: RETURN_REQUEST_SUBMITTED
            self.return_events.append({
                "event_id": f"EVT-2026-{event_counter:06d}",
                "rma_id": None,
                "request_id": req_id,
                "event_type": "RETURN_REQUEST_SUBMITTED",
                "from_status": None,
                "to_status": "SUBMITTED",
                "actor_role": "CUSTOMER",
                "actor_id": order["customer_id"],
                "timestamp": request_dt.isoformat(),
                "details": f"Return initiated via {req_record['request_channel']}"
            })
            event_counter += 1

            # Determine number of lines to sample
            remaining_reqs = len(selected_orders) - (req_idx - 1)
            remaining_lines_needed = max(0, target_lines - len(self.return_lines))
            avg_lines_needed = (remaining_lines_needed / remaining_reqs) if remaining_reqs > 0 else 1.0

            sample_count = 1
            if avg_lines_needed >= 1.5 and len(order_lines) >= 2:
                sample_count = min(len(order_lines), 2 if avg_lines_needed < 2.5 else 3)

            lines_to_return = self.rng.sample(order_lines, min(len(order_lines), sample_count))
            current_rma_lines = []

            for l_idx, ol in enumerate(lines_to_return, start=1):
                ret_line_id = f"RMAL-{rma_id}-{l_idx:02d}"
                return_line_counter += 1

                purchased_qty = ol["quantity"]
                inject_qty_excess = (anomaly_counts["QTY_EXCEEDS_PURCHASED"] < anomaly_targets["QTY_EXCEEDS_PURCHASED"] and self.rng.random() < 0.15)
                if inject_qty_excess:
                    requested_qty = purchased_qty + self.rng.randint(2, 5)
                    anomaly_counts["QTY_EXCEEDS_PURCHASED"] += 1
                    self.ground_truth_anomalies.append({
                        "anomaly_id": f"ANO-{anomaly_counter:06d}",
                        "entity_name": "return_lines",
                        "entity_id": ret_line_id,
                        "parent_entity_id": ol["order_line_id"],
                        "issue_type": "QTY_EXCEEDS_PURCHASED",
                        "expected_decision": "REJECT_QUANTITY_OVERFLOW",
                        "actual_injected_behavior": f"Requested {requested_qty} units on line with purchase qty {purchased_qty}",
                        "created_at": request_dt.isoformat()
                    })
                    anomaly_counter += 1
                else:
                    requested_qty = self.rng.randint(1, purchased_qty)

                reason = self.rng.choice(RETURN_REASONS)
                reported_cond = self.rng.choice(ITEM_CONDITIONS)
                eff_unit_price = quantize_money(to_decimal(ol["line_subtotal"]) / Decimal(str(purchased_qty)))

                r_line = {
                    "return_line_id": ret_line_id,
                    "request_id": req_id,
                    "order_line_id": ol["order_line_id"],
                    "requested_quantity": requested_qty,
                    "return_reason": reason,
                    "item_condition_reported": reported_cond,
                    "unit_price": str(eff_unit_price),
                    "line_subtotal": ol["line_subtotal"],
                    "sku": ol["sku"],
                    "category": ol["category"],
                    "is_final_sale": bool(ol["is_final_sale"]),
                    "purchased_quantity": purchased_qty,
                    "previously_returned_quantity": 0
                }
                self.return_lines.append(r_line)
                current_rma_lines.append(r_line)

            # Process RMA Authorization
            rma_eval = AuthorizationEngine.process_return_request(
                request_id=req_id,
                order=order,
                lines=current_rma_lines,
                request_date=request_dt,
                customer_tier="STANDARD"
            )

            auth_dt = request_dt + timedelta(hours=self.rng.randint(1, 12))
            rma_record = {
                "rma_id": rma_id,
                "request_id": req_id,
                "authorization_date": auth_dt.isoformat(),
                "authorization_status": rma_eval.rma_status,
                "total_approved_quantity": rma_eval.total_approved_quantity,
                "policy_override_applied": 1 if rma_eval.policy_override_applied else 0,
                "override_reason": rma_eval.override_reason,
                "authorized_by": rma_eval.authorized_by,
                "rma_expiration_date": rma_eval.expiration_date.isoformat()
            }
            self.return_authorizations.append(rma_record)
            req_record["request_status"] = rma_eval.rma_status

            # Log Event: RMA_PROCESSED
            self.return_events.append({
                "event_id": f"EVT-2026-{event_counter:06d}",
                "rma_id": rma_id,
                "request_id": req_id,
                "event_type": "RMA_AUTHORIZED",
                "from_status": "SUBMITTED",
                "to_status": rma_eval.rma_status,
                "actor_role": "SYSTEM",
                "actor_id": rma_eval.authorized_by,
                "timestamp": auth_dt.isoformat(),
                "details": f"Approved {rma_eval.total_approved_quantity} units. Status: {rma_eval.rma_status}"
            })
            event_counter += 1

            # If RMA has approved quantities, proceed to Logistics, Inspection, Disposition & Refund
            if rma_eval.total_approved_quantity > 0:
                ship_id = f"RTS-2026-{shipment_counter:06d}"
                shipment_counter += 1
                ship_dt = auth_dt + timedelta(days=self.rng.randint(1, 3))
                received_dt = ship_dt + timedelta(days=self.rng.randint(2, 5))

                ship_status = self.rng.choices(["DELIVERED", "IN_TRANSIT", "EXCEPTION_LOST"], weights=[0.92, 0.05, 0.03])[0]
                self.return_shipments.append({
                    "shipment_id": ship_id,
                    "rma_id": rma_id,
                    "tracking_number": f"TRK-{self.rng.choice(CARRIERS)}-{self.rng.randint(10000000, 99999999)}",
                    "carrier": self.rng.choice(CARRIERS),
                    "shipped_date": ship_dt.isoformat(),
                    "received_date": received_dt.isoformat() if ship_status == "DELIVERED" else None,
                    "shipment_status": ship_status,
                    "origin_zip": f"{self.rng.randint(10001, 99950):05d}",
                    "destination_warehouse": self.rng.choice(WAREHOUSES)
                })

                # Log Event: RETURN_SHIPMENT_DISPATCHED
                self.return_events.append({
                    "event_id": f"EVT-2026-{event_counter:06d}",
                    "rma_id": rma_id,
                    "request_id": req_id,
                    "event_type": "RETURN_SHIPMENT_DISPATCHED",
                    "from_status": rma_eval.rma_status,
                    "to_status": ship_status,
                    "actor_role": "LOGISTICS_CARRIER",
                    "actor_id": "CARRIER",
                    "timestamp": ship_dt.isoformat(),
                    "details": f"Shipment created: {ship_id} ({ship_status})"
                })
                event_counter += 1

                if ship_status == "DELIVERED":
                    insp_dt = received_dt + timedelta(hours=self.rng.randint(4, 24))
                    approved_rma_lines = []

                    for line_eval, raw_line in zip(rma_eval.line_evaluations, current_rma_lines):
                        app_qty = line_eval["approved_quantity"]
                        if app_qty <= 0:
                            continue

                        raw_line["approved_quantity"] = app_qty
                        approved_rma_lines.append(raw_line)

                        insp_id = f"INS-2026-{insp_counter:06d}"
                        insp_counter += 1

                        insp_res = InspectionEngine.inspect_item(
                            inspection_id=insp_id,
                            rma_id=rma_id,
                            return_line_id=raw_line["return_line_id"],
                            shipment_id=ship_id,
                            shipment_received_date=received_dt,
                            inspection_date=insp_dt,
                            inspector_id=f"INSP-OP-{self.rng.randint(1, 5):02d}",
                            approved_quantity=app_qty,
                            received_quantity=app_qty,
                            expected_sku=raw_line.get("sku", "SKU-ELEC-01"),
                            actual_sku=raw_line.get("sku", "SKU-ELEC-01"),
                            reported_condition=raw_line["item_condition_reported"],
                            packaging_intact=True,
                            serial_verified=True
                        )

                        self.inspections.append({
                            "inspection_id": insp_id,
                            "rma_id": rma_id,
                            "return_line_id": raw_line["return_line_id"],
                            "shipment_id": ship_id,
                            "inspection_date": insp_dt.isoformat(),
                            "inspector_id": insp_res.inspector_id,
                            "received_quantity": insp_res.received_quantity,
                            "inspected_sku": insp_res.inspected_sku,
                            "item_grade": insp_res.item_grade,
                            "packaging_intact": 1 if insp_res.packaging_intact else 0,
                            "serial_number_verified": 1 if insp_res.serial_number_verified else 0,
                            "discrepancy_flag": 1 if insp_res.discrepancy_flag else 0,
                            "inspection_notes": insp_res.inspection_notes
                        })

                        # Inventory Disposition
                        disp_id = f"DISP-2026-{disp_counter:06d}"
                        disp_counter += 1

                        inject_restock_early = (anomaly_counts["RESTOCK_BEFORE_INSPECTION"] < anomaly_targets["RESTOCK_BEFORE_INSPECTION"] and self.rng.random() < 0.20)
                        if inject_restock_early:
                            disp_dt = insp_dt - timedelta(hours=self.rng.randint(12, 36))
                            anomaly_counts["RESTOCK_BEFORE_INSPECTION"] += 1
                            self.ground_truth_anomalies.append({
                                "anomaly_id": f"ANO-{anomaly_counter:06d}",
                                "entity_name": "inventory_dispositions",
                                "entity_id": disp_id,
                                "parent_entity_id": insp_id,
                                "issue_type": "RESTOCK_BEFORE_INSPECTION",
                                "expected_decision": "BLOCK_PREMATURE_RESTOCK",
                                "actual_injected_behavior": f"Restocked at {disp_dt.isoformat()}, before inspection {insp_dt.isoformat()}",
                                "created_at": disp_dt.isoformat()
                            })
                            anomaly_counter += 1
                        else:
                            disp_dt = insp_dt + timedelta(hours=self.rng.randint(2, 10))

                        disp_res = DispositionEngine.determine_disposition(
                            disposition_id=disp_id,
                            inspection_id=insp_id,
                            rma_id=rma_id,
                            inspection_date=insp_dt,
                            disposition_date=disp_dt,
                            item_grade=insp_res.item_grade,
                            unit_price=float(raw_line["unit_price"]),
                            force_anomaly=inject_restock_early
                        )

                        self.inventory_dispositions.append({
                            "disposition_id": disp_id,
                            "inspection_id": insp_id,
                            "rma_id": rma_id,
                            "disposition_date": disp_dt.isoformat(),
                            "disposition_action": disp_res.disposition_action,
                            "target_bin_location": disp_res.target_bin_location,
                            "unit_cost_recovery": str(quantize_money(to_decimal(disp_res.unit_cost_recovery))),
                            "operator_id": disp_res.operator_id
                        })

                    # Calculate Refund
                    if approved_rma_lines:
                        ref_id = f"REF-2026-{refund_counter:06d}"
                        refund_counter += 1
                        ref_dt = insp_dt + timedelta(hours=self.rng.randint(1, 6))

                        inject_excess_refund = (anomaly_counts["REFUND_EXCEEDS_PAID"] < anomaly_targets["REFUND_EXCEEDS_PAID"] and self.rng.random() < 0.20)
                        if inject_excess_refund:
                            anomaly_counts["REFUND_EXCEEDS_PAID"] += 1
                            self.ground_truth_anomalies.append({
                                "anomaly_id": f"ANO-{anomaly_counter:06d}",
                                "entity_name": "refunds",
                                "entity_id": ref_id,
                                "parent_entity_id": rma_id,
                                "issue_type": "REFUND_EXCEEDS_PAID",
                                "expected_decision": "BLOCK_EXCESS_PAYOUT",
                                "actual_injected_behavior": f"Refund calculated to exceed order total paid ({order['total_paid_amount']})",
                                "created_at": ref_dt.isoformat()
                            })
                            anomaly_counter += 1

                        refund_calc = RefundEngine.calculate_refund(
                            refund_id=ref_id,
                            rma_id=rma_id,
                            customer_id=order["customer_id"],
                            refund_date=ref_dt,
                            order=order,
                            approved_lines=approved_rma_lines,
                            force_excess_anomaly=inject_excess_refund
                        )

                        refund_rec = {
                            "refund_id": ref_id,
                            "rma_id": rma_id,
                            "customer_id": order["customer_id"],
                            "refund_date": ref_dt.isoformat(),
                            "gross_item_amount": str(refund_calc.gross_item_amount),
                            "prorated_discount": str(refund_calc.prorated_discount),
                            "tax_refund_amount": str(refund_calc.tax_refund_amount),
                            "restocking_fee": str(refund_calc.restocking_fee),
                            "net_refund_amount": str(refund_calc.net_refund_amount),
                            "refund_method": refund_calc.refund_method,
                            "refund_status": refund_calc.refund_status,
                            "idempotency_key": refund_calc.idempotency_key
                        }
                        self.refunds.append(refund_rec)

                        # Log Event: REFUND_ISSUED
                        self.return_events.append({
                            "event_id": f"EVT-2026-{event_counter:06d}",
                            "rma_id": rma_id,
                            "request_id": req_id,
                            "event_type": "REFUND_ISSUED",
                            "from_status": "INSPECTED",
                            "to_status": "REFUNDED",
                            "actor_role": "FINANCE",
                            "actor_id": "AUTO_SETTLEMENT",
                            "timestamp": ref_dt.isoformat(),
                            "details": f"Refund {ref_id} issued: ${refund_calc.net_refund_amount}"
                        })
                        event_counter += 1

                        # Check DUPLICATE_REFUND_ATTEMPT anomaly
                        inject_duplicate_refund = (anomaly_counts["DUPLICATE_REFUND_ATTEMPT"] < anomaly_targets["DUPLICATE_REFUND_ATTEMPT"] and self.rng.random() < 0.20)
                        if inject_duplicate_refund:
                            anomaly_counts["DUPLICATE_REFUND_ATTEMPT"] += 1
                            dup_ref_id = f"REF-2026-{refund_counter:06d}"
                            refund_counter += 1
                            self.ground_truth_anomalies.append({
                                "anomaly_id": f"ANO-{anomaly_counter:06d}",
                                "entity_name": "refunds",
                                "entity_id": dup_ref_id,
                                "parent_entity_id": rma_id,
                                "issue_type": "DUPLICATE_REFUND_ATTEMPT",
                                "expected_decision": "BLOCK_DUPLICATE_REFUND",
                                "actual_injected_behavior": f"Duplicate payout attempted for RMA {rma_id}",
                                "created_at": (ref_dt + timedelta(minutes=5)).isoformat()
                            })
                            anomaly_counter += 1

    def persist_to_database(self, db_path: Path):
        """Inserts all generated records into SQLite with full foreign keys."""
        conn = init_database(db_path)
        cur = conn.cursor()

        cur.executemany("""
            INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [(p["sku"], p["product_name"], p["category"], float(p["unit_price"]),
               p["is_returnable"], p["return_window_days"], float(p["restock_fee_rate"]),
               p["created_at"]) for p in self.products])

        cur.executemany("""
            INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [(c["customer_id"], c["first_name"], c["last_name"], c["email"], c["phone"],
               c["customer_tier"], c["risk_score"], c["created_at"]) for c in self.customers])

        cur.executemany("""
            INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(o["order_id"], o["customer_id"], o["order_date"], o["currency"], float(o["subtotal_amount"]),
               float(o["discount_amount"]), float(o["tax_amount"]), float(o["shipping_fee"]),
               float(o["total_paid_amount"]), o["payment_method"], o["order_status"],
               o["delivery_date"]) for o in self.orders])

        cur.executemany("""
            INSERT INTO order_lines VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(l["order_line_id"], l["order_id"], l["line_number"], l["sku"], l["product_name"],
               l["category"], float(l["unit_price"]), l["quantity"], float(l["line_discount"]),
               float(l["line_subtotal"]), l["return_window_days"], l["is_final_sale"]) for l in self.order_lines])

        cur.executemany("""
            INSERT INTO return_requests VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [(r["request_id"], r["order_id"], r["customer_id"], r["request_date"],
               r["request_channel"], r["request_status"], r["customer_notes"]) for r in self.return_requests])

        cur.executemany("""
            INSERT INTO return_lines VALUES (?, ?, ?, ?, ?, ?)
        """, [(l["return_line_id"], l["request_id"], l["order_line_id"], l["requested_quantity"],
               l["return_reason"], l["item_condition_reported"]) for l in self.return_lines])

        cur.executemany("""
            INSERT INTO return_authorizations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(a["rma_id"], a["request_id"], a["authorization_date"], a["authorization_status"],
               a["total_approved_quantity"], a["policy_override_applied"], a["override_reason"],
               a["authorized_by"], a["rma_expiration_date"]) for a in self.return_authorizations])

        cur.executemany("""
            INSERT INTO return_shipments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(s["shipment_id"], s["rma_id"], s["tracking_number"], s["carrier"],
               s["shipped_date"], s["received_date"], s["shipment_status"],
               s["origin_zip"], s["destination_warehouse"]) for s in self.return_shipments])

        cur.executemany("""
            INSERT INTO inspections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(i["inspection_id"], i["rma_id"], i["return_line_id"], i["shipment_id"],
               i["inspection_date"], i["inspector_id"], i["received_quantity"], i["inspected_sku"],
               i["item_grade"], i["packaging_intact"], i["serial_number_verified"],
               i["discrepancy_flag"], i["inspection_notes"]) for i in self.inspections])

        cur.executemany("""
            INSERT INTO inventory_dispositions VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [(d["disposition_id"], d["inspection_id"], d["rma_id"], d["disposition_date"],
               d["disposition_action"], d["target_bin_location"], float(d["unit_cost_recovery"]),
               d["operator_id"]) for d in self.inventory_dispositions])

        cur.executemany("""
            INSERT INTO refunds VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(f["refund_id"], f["rma_id"], f["customer_id"], f["refund_date"],
               float(f["gross_item_amount"]), float(f["prorated_discount"]), float(f["tax_refund_amount"]),
               float(f["restocking_fee"]), float(f["net_refund_amount"]), f["refund_method"],
               f["refund_status"], f["idempotency_key"]) for f in self.refunds])

        cur.executemany("""
            INSERT INTO return_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(e["event_id"], e["rma_id"], e["request_id"], e["event_type"],
               e["from_status"], e["to_status"], e["actor_role"], e["actor_id"],
               e["timestamp"], e["details"]) for e in self.return_events])

        cur.executemany("""
            INSERT INTO ground_truth_anomalies VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [(a["anomaly_id"], a["entity_name"], a["entity_id"], a["parent_entity_id"],
               a["issue_type"], a["expected_decision"], a["actual_injected_behavior"],
               a["created_at"]) for a in self.ground_truth_anomalies])

        conn.commit()
        conn.close()

    def export_csv_and_json(self, raw_dir: Path, gt_dir: Path, anomalies_dir: Path):
        """Exports raw CSV & JSON for all 12 entities, 5 separate anomaly datasets, and unified ground truth."""
        raw_dir.mkdir(parents=True, exist_ok=True)
        gt_dir.mkdir(parents=True, exist_ok=True)
        anomalies_dir.mkdir(parents=True, exist_ok=True)

        datasets = {
            "products": self.products,
            "customers": self.customers,
            "orders": self.orders,
            "order_lines": self.order_lines,
            "return_requests": self.return_requests,
            "return_lines": self.return_lines,
            "return_authorizations": self.return_authorizations,
            "return_shipments": self.return_shipments,
            "inspections": self.inspections,
            "inventory_dispositions": self.inventory_dispositions,
            "refunds": self.refunds,
            "return_events": self.return_events
        }

        # 1. Export all 12 Canonical Entities as CSV and JSON
        for name, records in datasets.items():
            if not records:
                continue
            csv_path = raw_dir / f"{name}.csv"
            json_path = raw_dir / f"{name}.json"

            keys = list(records[0].keys())
            filtered_keys = [k for k in keys if k not in ["unit_price_eff", "purchased_quantity", "previously_returned_quantity", "approved_quantity"]]

            # CSV
            with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=filtered_keys)
                writer.writeheader()
                for r in records:
                    row = {k: r[k] for k in filtered_keys}
                    writer.writerow(row)

            # JSON
            with open(json_path, mode="w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)

        # 2. Export Unified Master Ground Truth
        if self.ground_truth_anomalies:
            gt_csv = gt_dir / "ground_truth.csv"
            gt_json = gt_dir / "ground_truth.json"
            gt_keys = list(self.ground_truth_anomalies[0].keys())

            with open(gt_csv, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=gt_keys)
                writer.writeheader()
                writer.writerows(self.ground_truth_anomalies)

            with open(gt_json, mode="w", encoding="utf-8") as f:
                json.dump(self.ground_truth_anomalies, f, indent=2)

        # 3. Export 5 Separate Anomaly Datasets (CSV & JSON)
        anomaly_file_map = {
            "QTY_EXCEEDS_PURCHASED": "excess_return_quantity",
            "REFUND_EXCEEDS_PAID": "excess_refund",
            "RESTOCK_BEFORE_INSPECTION": "restocking_before_inspection",
            "RETURN_PAST_POLICY_WINDOW": "expired_return_policy",
            "DUPLICATE_REFUND_ATTEMPT": "duplicate_refund"
        }

        for issue_type, file_slug in anomaly_file_map.items():
            subset = [a for a in self.ground_truth_anomalies if a["issue_type"] == issue_type]
            if subset:
                sub_csv = anomalies_dir / f"{file_slug}.csv"
                sub_json = anomalies_dir / f"{file_slug}.json"
                sub_keys = list(subset[0].keys())

                with open(sub_csv, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=sub_keys)
                    writer.writeheader()
                    writer.writerows(subset)

                with open(sub_json, mode="w", encoding="utf-8") as f:
                    json.dump(subset, f, indent=2)

    def get_summary_counts(self) -> Dict[str, int]:
        return {
            "products": len(self.products),
            "customers": len(self.customers),
            "orders": len(self.orders),
            "order_lines": len(self.order_lines),
            "return_requests": len(self.return_requests),
            "return_lines": len(self.return_lines),
            "return_authorizations": len(self.return_authorizations),
            "return_shipments": len(self.return_shipments),
            "inspections": len(self.inspections),
            "inventory_dispositions": len(self.inventory_dispositions),
            "refunds": len(self.refunds),
            "return_events": len(self.return_events),
            "ground_truth_anomalies": len(self.ground_truth_anomalies)
        }
