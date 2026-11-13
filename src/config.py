"""
Global Configuration and Constants for YottaFlex Return Management System (RMS)
Deterministic Seed: 20261022
Scaled: +25% over baseline (Orders: 37,500, Requests: 6,250, Return Lines: 10,000)
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any
from decimal import Decimal

# Root Directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"
ANOMALIES_DIR = DATA_DIR / "anomalies"
EXPORTS_DIR = DATA_DIR / "exports"
DOCS_DIR = BASE_DIR / "docs"
DATABASE_PATH = DATA_DIR / "reverse_logistics.db"

# Seed & Reproducibility
RANDOM_SEED = 20261022

# Scale Configurations (+25% Exact Target for Full Scale)
@dataclass(frozen=True)
class ScaleConfig:
    name: str
    num_orders: int
    num_return_requests: int
    num_return_lines: int
    num_customers: int
    anomaly_rate: float = 0.05

SCALE_CONFIGS: Dict[str, ScaleConfig] = {
    "starter": ScaleConfig(
        name="starter",
        num_orders=375,
        num_return_requests=63,
        num_return_lines=100,
        num_customers=150,
        anomaly_rate=0.08
    ),
    "medium": ScaleConfig(
        name="medium",
        num_orders=3750,
        num_return_requests=625,
        num_return_lines=1000,
        num_customers=1500,
        anomaly_rate=0.05
    ),
    "full": ScaleConfig(
        name="full",
        num_orders=37500,           # 30,000 -> 37,500 (+25%)
        num_return_requests=6250,    # 5,000  -> 6,250  (+25%)
        num_return_lines=10000,      # 8,000  -> 10,000 (+25%)
        num_customers=15000,         # 12,000 -> 15,000 (+25%)
        anomaly_rate=0.05
    )
}

# Category Return Windows & Exclusions
CATEGORY_RETURN_WINDOWS: Dict[str, int] = {
    "ELECTRONICS": 14,
    "APPAREL": 30,
    "FOOTWEAR": 30,
    "HOME_GOODS": 30,
    "PERISHABLE": 0,    # Strictly non-returnable
    "FINAL_SALE": 0     # Strictly non-returnable
}

CUSTOMER_TIER_OVERRIDE_WINDOWS: Dict[str, int] = {
    "VIP": 60,
    "PLATINUM": 90,
    "STANDARD": 30,
    "EMPLOYEE": 45
}

# Standard Restocking Fees (Decimal Representation)
RESTOCKING_FEE_RATES: Dict[str, Decimal] = {
    "ELECTRONICS": Decimal("0.15"),  # 15% fee on opened electronics unless defective
    "APPAREL": Decimal("0.00"),
    "FOOTWEAR": Decimal("0.00"),
    "HOME_GOODS": Decimal("0.05"),
    "PERISHABLE": Decimal("0.00"),
    "FINAL_SALE": Decimal("0.00")
}

# Value recovery percentage by inspection grade (Decimal)
DISPOSITION_VALUE_RECOVERY: Dict[str, Decimal] = {
    "GRADE_A_NEW": Decimal("1.00"),
    "GRADE_B_OPEN_BOX": Decimal("0.80"),
    "GRADE_C_REFURBISHABLE": Decimal("0.50"),
    "GRADE_D_DAMAGED": Decimal("0.00"),
    "COUNTERFEIT_FRAUD": Decimal("0.00")
}

# Canonical Master Products Catalog (16 Distinct SKUs across 6 categories)
CANONICAL_PRODUCTS: List[Dict[str, Any]] = [
    {"sku": "SKU-ELEC-01", "product_name": "Wireless Noise-Canceling Headphones", "category": "ELECTRONICS", "unit_price": Decimal("199.99"), "is_returnable": True, "return_window_days": 14, "restock_fee_rate": Decimal("0.15")},
    {"sku": "SKU-ELEC-02", "product_name": "4K Ultra HD Action Camera", "category": "ELECTRONICS", "unit_price": Decimal("299.99"), "is_returnable": True, "return_window_days": 14, "restock_fee_rate": Decimal("0.15")},
    {"sku": "SKU-ELEC-03", "product_name": "Smart Fitness Watch V2", "category": "ELECTRONICS", "unit_price": Decimal("149.50"), "is_returnable": True, "return_window_days": 14, "restock_fee_rate": Decimal("0.15")},
    {"sku": "SKU-ELEC-04", "product_name": "Portable Bluetooth Speaker Pro", "category": "ELECTRONICS", "unit_price": Decimal("89.95"), "is_returnable": True, "return_window_days": 14, "restock_fee_rate": Decimal("0.15")},
    {"sku": "SKU-APPR-01", "product_name": "Merino Wool Crewneck Sweater", "category": "APPAREL", "unit_price": Decimal("89.00"), "is_returnable": True, "return_window_days": 30, "restock_fee_rate": Decimal("0.00")},
    {"sku": "SKU-APPR-02", "product_name": "Tailored Stretch Chino Pants", "category": "APPAREL", "unit_price": Decimal("68.00"), "is_returnable": True, "return_window_days": 30, "restock_fee_rate": Decimal("0.00")},
    {"sku": "SKU-APPR-03", "product_name": "Waterproof Outdoor Jacket", "category": "APPAREL", "unit_price": Decimal("125.00"), "is_returnable": True, "return_window_days": 30, "restock_fee_rate": Decimal("0.00")},
    {"sku": "SKU-APPR-04", "product_name": "Classic Oxford Cotton Shirt", "category": "APPAREL", "unit_price": Decimal("55.00"), "is_returnable": True, "return_window_days": 30, "restock_fee_rate": Decimal("0.00")},
    {"sku": "SKU-FOOT-01", "product_name": "Performance Trail Running Shoes", "category": "FOOTWEAR", "unit_price": Decimal("139.99"), "is_returnable": True, "return_window_days": 30, "restock_fee_rate": Decimal("0.00")},
    {"sku": "SKU-FOOT-02", "product_name": "Leather Oxford Dress Shoes", "category": "FOOTWEAR", "unit_price": Decimal("175.00"), "is_returnable": True, "return_window_days": 30, "restock_fee_rate": Decimal("0.00")},
    {"sku": "SKU-HOME-01", "product_name": "Cast Iron Dutch Oven 6qt", "category": "HOME_GOODS", "unit_price": Decimal("79.99"), "is_returnable": True, "return_window_days": 30, "restock_fee_rate": Decimal("0.05")},
    {"sku": "SKU-HOME-02", "product_name": "Ergonomic Memory Foam Pillow", "category": "HOME_GOODS", "unit_price": Decimal("49.99"), "is_returnable": True, "return_window_days": 30, "restock_fee_rate": Decimal("0.05")},
    {"sku": "SKU-HOME-03", "product_name": "Stainless Steel Cookware Set 10pc", "category": "HOME_GOODS", "unit_price": Decimal("249.00"), "is_returnable": True, "return_window_days": 30, "restock_fee_rate": Decimal("0.05")},
    {"sku": "SKU-PERS-01", "product_name": "Organic Roast Coffee Beans 2lb", "category": "PERISHABLE", "unit_price": Decimal("28.50"), "is_returnable": False, "return_window_days": 0, "restock_fee_rate": Decimal("0.00")},
    {"sku": "SKU-PERS-02", "product_name": "Artisan Loose Leaf Tea Selection", "category": "PERISHABLE", "unit_price": Decimal("22.00"), "is_returnable": False, "return_window_days": 0, "restock_fee_rate": Decimal("0.00")},
    {"sku": "SKU-FSLE-01", "product_name": "Clearance Graphic T-Shirt", "category": "FINAL_SALE", "unit_price": Decimal("15.00"), "is_returnable": False, "return_window_days": 0, "restock_fee_rate": Decimal("0.00")}
]

# State Enums
CUSTOMER_TIERS = ["STANDARD", "VIP", "PLATINUM", "EMPLOYEE"]
ORDER_STATUSES = ["DELIVERED", "SHIPPED", "CANCELLED"]
PAYMENT_METHODS = ["CREDIT_CARD", "DEBIT_CARD", "PAYPAL", "APPLE_PAY", "STORE_CREDIT"]

RETURN_REASONS = [
    "DEFECTIVE",
    "WRONG_ITEM",
    "DOES_NOT_FIT",
    "CHANGED_MIND",
    "NOT_AS_DESCRIBED",
    "ARRIVED_LATE",
    "EXCHANGE_REQUESTED"
]

ITEM_CONDITIONS = [
    "UNOPENED",
    "OPENED_UNUSED",
    "USED",
    "DAMAGED_TRANSIT",
    "DEFECTIVE"
]

RMA_STATUSES = ["APPROVED", "PARTIALLY_APPROVED", "REJECTED", "EXPIRED", "CANCELLED"]
SHIPMENT_STATUSES = ["LABEL_CREATED", "IN_TRANSIT", "DELIVERED", "EXCEPTION_LOST", "RETURNED_TO_SENDER"]
CARRIERS = ["UPS", "FEDEX", "USPS", "DHL"]
WAREHOUSES = ["WH-EAST-01", "WH-WEST-01", "WH-CENTRAL-01"]

ITEM_GRADES = [
    "GRADE_A_NEW",
    "GRADE_B_OPEN_BOX",
    "GRADE_C_REFURBISHABLE",
    "GRADE_D_DAMAGED",
    "COUNTERFEIT_FRAUD"
]

DISPOSITION_ACTIONS = [
    "RESTOCK_PRIMARY",
    "RESTOCK_OUTLET",
    "SEND_TO_REFURBISH",
    "QUARANTINE_FRAUD",
    "SCRAP_RECYCLE"
]

REFUND_STATUSES = ["COMPLETED", "PENDING_CLEARANCE", "BLOCKED_FRAUD", "REVERSED"]
REFUND_METHODS = ["ORIGINAL_PAYMENT", "STORE_CREDIT", "CHECK"]

# The 5 Required Anomaly Types (Edge Cases)
ANOMALY_TYPES = [
    "QTY_EXCEEDS_PURCHASED",       # Return quantity > purchased quantity
    "REFUND_EXCEEDS_PAID",         # Refund amount > order total paid
    "RESTOCK_BEFORE_INSPECTION",   # Disposition timestamp < inspection timestamp
    "RETURN_PAST_POLICY_WINDOW",   # Request after delivery + window without override
    "DUPLICATE_REFUND_ATTEMPT"     # Multiple refunds for same RMA ID
]
