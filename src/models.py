"""
Domain Models and SQLite Relational Schema
Includes Pydantic v2 schemas and SQLite DDL with strict FKs, products, and return_events tables.
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
import sqlite3
from pathlib import Path


# ---------------------------------------------------------
# 1. Pydantic v2 Domain Models
# ---------------------------------------------------------

class ProductModel(BaseModel):
    sku: str = Field(..., pattern=r"^SKU-[A-Z]{4}-\d{2}$")
    product_name: str
    category: str
    unit_price: Decimal = Field(..., gt=Decimal("0.00"))
    is_returnable: bool
    return_window_days: int = Field(..., ge=0)
    restock_fee_rate: Decimal = Field(..., ge=Decimal("0.00"), le=Decimal("1.00"))
    created_at: datetime


class CustomerModel(BaseModel):
    customer_id: str = Field(..., pattern=r"^CUST-\d{6}$")
    first_name: str
    last_name: str
    email: str
    phone: str
    customer_tier: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    created_at: datetime


class OrderModel(BaseModel):
    order_id: str = Field(..., pattern=r"^ORD-2026-\d{6}$")
    customer_id: str
    order_date: datetime
    currency: str = "USD"
    subtotal_amount: Decimal = Field(..., ge=Decimal("0.00"))
    discount_amount: Decimal = Field(Decimal("0.00"), ge=Decimal("0.00"))
    tax_amount: Decimal = Field(..., ge=Decimal("0.00"))
    shipping_fee: Decimal = Field(Decimal("0.00"), ge=Decimal("0.00"))
    total_paid_amount: Decimal = Field(..., ge=Decimal("0.00"))
    payment_method: str
    order_status: str
    delivery_date: Optional[datetime] = None


class OrderLineModel(BaseModel):
    order_line_id: str
    order_id: str
    line_number: int
    sku: str
    product_name: str
    category: str
    unit_price: Decimal = Field(..., gt=Decimal("0.00"))
    quantity: int = Field(..., ge=1)
    line_discount: Decimal = Field(Decimal("0.00"), ge=Decimal("0.00"))
    line_subtotal: Decimal = Field(..., gt=Decimal("0.00"))
    return_window_days: int = Field(..., ge=0)
    is_final_sale: bool = False


class ReturnRequestModel(BaseModel):
    request_id: str = Field(..., pattern=r"^REQ-2026-\d{6}$")
    order_id: str
    customer_id: str
    request_date: datetime
    request_channel: str
    request_status: str
    customer_notes: Optional[str] = None


class ReturnLineModel(BaseModel):
    return_line_id: str
    request_id: str
    order_line_id: str
    requested_quantity: int = Field(..., ge=1)
    return_reason: str
    item_condition_reported: str


class ReturnAuthorizationModel(BaseModel):
    rma_id: str = Field(..., pattern=r"^RMA-2026-\d{6}$")
    request_id: str
    authorization_date: datetime
    authorization_status: str
    total_approved_quantity: int = Field(..., ge=0)
    policy_override_applied: bool = False
    override_reason: Optional[str] = None
    authorized_by: str
    rma_expiration_date: datetime


class ReturnShipmentModel(BaseModel):
    shipment_id: str = Field(..., pattern=r"^RTS-2026-\d{6}$")
    rma_id: str
    tracking_number: str
    carrier: str
    shipped_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    shipment_status: str
    origin_zip: str
    destination_warehouse: str


class InspectionModel(BaseModel):
    inspection_id: str = Field(..., pattern=r"^INS-2026-\d{6}$")
    rma_id: str
    return_line_id: str
    shipment_id: str
    inspection_date: datetime
    inspector_id: str
    received_quantity: int = Field(..., ge=0)
    inspected_sku: str
    item_grade: str
    packaging_intact: bool
    serial_number_verified: bool
    discrepancy_flag: bool
    inspection_notes: Optional[str] = None


class InventoryDispositionModel(BaseModel):
    disposition_id: str = Field(..., pattern=r"^DISP-2026-\d{6}$")
    inspection_id: str
    rma_id: str
    disposition_date: datetime
    disposition_action: str
    target_bin_location: str
    unit_cost_recovery: Decimal = Field(..., ge=Decimal("0.00"))
    operator_id: str


class RefundModel(BaseModel):
    refund_id: str = Field(..., pattern=r"^REF-2026-\d{6}$")
    rma_id: str
    customer_id: str
    refund_date: datetime
    gross_item_amount: Decimal = Field(..., ge=Decimal("0.00"))
    prorated_discount: Decimal = Field(Decimal("0.00"), ge=Decimal("0.00"))
    tax_refund_amount: Decimal = Field(..., ge=Decimal("0.00"))
    restocking_fee: Decimal = Field(Decimal("0.00"), ge=Decimal("0.00"))
    net_refund_amount: Decimal = Field(..., ge=Decimal("0.00"))
    refund_method: str
    refund_status: str
    idempotency_key: str


class ReturnEventModel(BaseModel):
    event_id: str = Field(..., pattern=r"^EVT-2026-\d{6}$")
    rma_id: Optional[str] = None
    request_id: str
    event_type: str
    from_status: Optional[str] = None
    to_status: str
    actor_role: str
    actor_id: str
    timestamp: datetime
    details: Optional[str] = None


class GroundTruthAnomalyModel(BaseModel):
    anomaly_id: str
    entity_name: str
    entity_id: str
    parent_entity_id: Optional[str] = None
    issue_type: str
    expected_decision: str
    actual_injected_behavior: str
    created_at: datetime


# ---------------------------------------------------------
# 2. SQLite DDL Schema Definition (Strict FKs & Constraints)
# ---------------------------------------------------------

SQLITE_SCHEMA_DDL = """
-- Master Products Catalog
CREATE TABLE IF NOT EXISTS products (
    sku TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price REAL NOT NULL CHECK(unit_price > 0.0),
    is_returnable INTEGER NOT NULL CHECK(is_returnable IN (0, 1)),
    return_window_days INTEGER NOT NULL CHECK(return_window_days >= 0),
    restock_fee_rate REAL NOT NULL CHECK(restock_fee_rate >= 0.0 AND restock_fee_rate <= 1.0),
    created_at TEXT NOT NULL
);

-- Master Customer Profiles
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT NOT NULL,
    customer_tier TEXT NOT NULL,
    risk_score REAL NOT NULL CHECK(risk_score >= 0.0 AND risk_score <= 1.0),
    created_at TEXT NOT NULL
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    subtotal_amount REAL NOT NULL CHECK(subtotal_amount >= 0.0),
    discount_amount REAL NOT NULL DEFAULT 0.0 CHECK(discount_amount >= 0.0),
    tax_amount REAL NOT NULL CHECK(tax_amount >= 0.0),
    shipping_fee REAL NOT NULL DEFAULT 0.0 CHECK(shipping_fee >= 0.0),
    total_paid_amount REAL NOT NULL CHECK(total_paid_amount >= 0.0),
    payment_method TEXT NOT NULL,
    order_status TEXT NOT NULL,
    delivery_date TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Order Line Items
CREATE TABLE IF NOT EXISTS order_lines (
    order_line_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    sku TEXT NOT NULL,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price REAL NOT NULL CHECK(unit_price > 0.0),
    quantity INTEGER NOT NULL CHECK(quantity >= 1),
    line_discount REAL NOT NULL DEFAULT 0.0 CHECK(line_discount >= 0.0),
    line_subtotal REAL NOT NULL CHECK(line_subtotal > 0.0),
    return_window_days INTEGER NOT NULL CHECK(return_window_days >= 0),
    is_final_sale INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (sku) REFERENCES products(sku)
);

-- Return Requests
CREATE TABLE IF NOT EXISTS return_requests (
    request_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    request_date TEXT NOT NULL,
    request_channel TEXT NOT NULL,
    request_status TEXT NOT NULL,
    customer_notes TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Return Line Items
CREATE TABLE IF NOT EXISTS return_lines (
    return_line_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    order_line_id TEXT NOT NULL,
    requested_quantity INTEGER NOT NULL CHECK(requested_quantity >= 1),
    return_reason TEXT NOT NULL,
    item_condition_reported TEXT NOT NULL,
    FOREIGN KEY (request_id) REFERENCES return_requests(request_id),
    FOREIGN KEY (order_line_id) REFERENCES order_lines(order_line_id)
);

-- Return Merchandise Authorizations (RMA)
CREATE TABLE IF NOT EXISTS return_authorizations (
    rma_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL UNIQUE,
    authorization_date TEXT NOT NULL,
    authorization_status TEXT NOT NULL,
    total_approved_quantity INTEGER NOT NULL CHECK(total_approved_quantity >= 0),
    policy_override_applied INTEGER NOT NULL DEFAULT 0,
    override_reason TEXT,
    authorized_by TEXT NOT NULL,
    rma_expiration_date TEXT NOT NULL,
    FOREIGN KEY (request_id) REFERENCES return_requests(request_id)
);

-- Inbound Return Shipments
CREATE TABLE IF NOT EXISTS return_shipments (
    shipment_id TEXT PRIMARY KEY,
    rma_id TEXT NOT NULL,
    tracking_number TEXT NOT NULL UNIQUE,
    carrier TEXT NOT NULL,
    shipped_date TEXT,
    received_date TEXT,
    shipment_status TEXT NOT NULL,
    origin_zip TEXT NOT NULL,
    destination_warehouse TEXT NOT NULL,
    FOREIGN KEY (rma_id) REFERENCES return_authorizations(rma_id)
);

-- Warehouse Inspections
CREATE TABLE IF NOT EXISTS inspections (
    inspection_id TEXT PRIMARY KEY,
    rma_id TEXT NOT NULL,
    return_line_id TEXT NOT NULL,
    shipment_id TEXT NOT NULL,
    inspection_date TEXT NOT NULL,
    inspector_id TEXT NOT NULL,
    received_quantity INTEGER NOT NULL CHECK(received_quantity >= 0),
    inspected_sku TEXT NOT NULL,
    item_grade TEXT NOT NULL,
    packaging_intact INTEGER NOT NULL,
    serial_number_verified INTEGER NOT NULL,
    discrepancy_flag INTEGER NOT NULL,
    inspection_notes TEXT,
    FOREIGN KEY (rma_id) REFERENCES return_authorizations(rma_id),
    FOREIGN KEY (return_line_id) REFERENCES return_lines(return_line_id),
    FOREIGN KEY (shipment_id) REFERENCES return_shipments(shipment_id)
);

-- Inventory Dispositions
CREATE TABLE IF NOT EXISTS inventory_dispositions (
    disposition_id TEXT PRIMARY KEY,
    inspection_id TEXT NOT NULL UNIQUE,
    rma_id TEXT NOT NULL,
    disposition_date TEXT NOT NULL,
    disposition_action TEXT NOT NULL,
    target_bin_location TEXT NOT NULL,
    unit_cost_recovery REAL NOT NULL CHECK(unit_cost_recovery >= 0.0),
    operator_id TEXT NOT NULL,
    FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id),
    FOREIGN KEY (rma_id) REFERENCES return_authorizations(rma_id)
);

-- Financial Refunds
CREATE TABLE IF NOT EXISTS refunds (
    refund_id TEXT PRIMARY KEY,
    rma_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    refund_date TEXT NOT NULL,
    gross_item_amount REAL NOT NULL CHECK(gross_item_amount >= 0.0),
    prorated_discount REAL NOT NULL DEFAULT 0.0 CHECK(prorated_discount >= 0.0),
    tax_refund_amount REAL NOT NULL CHECK(tax_refund_amount >= 0.0),
    restocking_fee REAL NOT NULL DEFAULT 0.0 CHECK(restocking_fee >= 0.0),
    net_refund_amount REAL NOT NULL CHECK(net_refund_amount >= 0.0),
    refund_method TEXT NOT NULL,
    refund_status TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    FOREIGN KEY (rma_id) REFERENCES return_authorizations(rma_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Append-Only Lifecycle Return Events Log
CREATE TABLE IF NOT EXISTS return_events (
    event_id TEXT PRIMARY KEY,
    rma_id TEXT,
    request_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    details TEXT,
    FOREIGN KEY (request_id) REFERENCES return_requests(request_id)
);

-- Ground Truth Anomalies (Isolated from production feature views)
CREATE TABLE IF NOT EXISTS ground_truth_anomalies (
    anomaly_id TEXT PRIMARY KEY,
    entity_name TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    parent_entity_id TEXT,
    issue_type TEXT NOT NULL,
    expected_decision TEXT NOT NULL,
    actual_injected_behavior TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Indexes for Query Performance
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_order ON order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_sku ON order_lines(sku);
CREATE INDEX IF NOT EXISTS idx_return_requests_order ON return_requests(order_id);
CREATE INDEX IF NOT EXISTS idx_return_lines_request ON return_lines(request_id);
CREATE INDEX IF NOT EXISTS idx_rma_request ON return_authorizations(request_id);
CREATE INDEX IF NOT EXISTS idx_shipment_rma ON return_shipments(rma_id);
CREATE INDEX IF NOT EXISTS idx_inspection_rma ON inspections(rma_id);
CREATE INDEX IF NOT EXISTS idx_disposition_inspection ON inventory_dispositions(inspection_id);
CREATE INDEX IF NOT EXISTS idx_refund_rma ON refunds(rma_id);
CREATE INDEX IF NOT EXISTS idx_events_request ON return_events(request_id);
CREATE INDEX IF NOT EXISTS idx_events_rma ON return_events(rma_id);
"""


def init_database(db_path: Path) -> sqlite3.Connection:
    """Initialize SQLite database with strict foreign keys and WAL mode."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SQLITE_SCHEMA_DDL)
    conn.commit()
    return conn
