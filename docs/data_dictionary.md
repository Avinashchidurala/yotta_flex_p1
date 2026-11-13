# YottaFlex Return Management System (RMS) — Master Data Dictionary

**Version**: 2.0.0 (Audited & Expanded +25%)  
**Target Scale**: 37,500 Orders, 6,250 Return Requests, 10,000 Return Lines, 15,000 Customers  
**Deterministic Random Seed**: `20261022`  
**Storage Engine**: SQLite in WAL mode with strict foreign keys (`PRAGMA foreign_keys = ON;`)  
**Currency Standard**: ISO 4217 `USD` evaluated via `Decimal` (ROUND_HALF_UP, 2 decimal places)

---

## 1. Master Catalog & Customer Entities

### 1.1 Product Catalog (`products`)
Primary catalog defining SKU master data, standard pricing, return windows, and restocking fee rates.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Invariants |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `sku` | String | Required | `SKU-[A-Z]{4}-\d{2}` | None | **Primary Key** | Unique immutable SKU identifier. |
| `product_name` | String | Required | 1–100 characters | None | Non-unique | Descriptive catalog item title. |
| `category` | String | Required | `ELECTRONICS`, `APPAREL`, `FOOTWEAR`, `HOME_GOODS`, `PERISHABLE`, `FINAL_SALE` | None | Non-unique | Dictates return policy window and fee rate. |
| `unit_price` | Decimal | Required | $> 0.00$ | USD ($) | Non-unique | Base retail price before discounts. |
| `is_returnable` | Boolean | Required | `1` (True), `0` (False) | Flag | Non-unique | `0` for Perishables and Final Sale clearance items. |
| `return_window_days` | Integer | Required | `0, 14, 30` | Days | Non-unique | Electronics = 14, Apparel/Footwear/Home = 30, Final/Perishable = 0. |
| `restock_fee_rate` | Decimal | Required | `0.00` to `0.25` | Rate | Non-unique | 0.15 for Electronics, 0.05 for Home Goods, 0.00 for Apparel. |
| `created_at` | DateTime | Required | ISO 8601 UTC string | UTC | Non-unique | Catalog entry creation timestamp. |

---

### 1.2 Customer Profiles (`customers`)
Purchasing entities initiating orders and return requests.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Invariants |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `customer_id` | String | Required | `CUST-\d{6}` | None | **Primary Key** | Sequential customer ID format. |
| `first_name` | String | Required | Alphabetic | None | Non-unique | Customer given name. |
| `last_name` | String | Required | Alphabetic | None | Non-unique | Customer family name. |
| `email` | String | Required | RFC 5322 Email format | None | **Unique** | Canonical contact email. |
| `phone` | String | Required | E.164 phone string | None | Non-unique | Contact telephone number. |
| `customer_tier` | String | Required | `STANDARD`, `VIP`, `PLATINUM`, `EMPLOYEE` | None | Non-unique | VIP extends return window to 60 days; Platinum to 90 days. |
| `risk_score` | Float | Required | `0.00` to `1.00` | Score | Non-unique | Statistical fraud risk propensity score. |
| `created_at` | DateTime | Required | ISO 8601 UTC string | UTC | Non-unique | Customer registration date. Must precede order dates. |

---

## 2. Order Transaction Entities

### 2.1 Sales Order (`orders`)
Commercial purchase transactions.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Invariants |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `order_id` | String | Required | `ORD-2026-\d{6}` | None | **Primary Key** | Sequential immutable order ID. |
| `customer_id` | String | Required | Valid `customer_id` | None | **Foreign Key** | References `customers(customer_id)`. |
| `order_date` | DateTime | Required | ISO 8601 UTC string | UTC | Non-unique | Purchase timestamp. Must be $\ge$ `customer.created_at`. |
| `currency` | String | Required | `USD` | ISO 4217 | Non-unique | Fixed to USD. |
| `subtotal_amount` | Decimal | Required | $\ge 0.00$ | USD ($) | Non-unique | Reconciled: $\sum(\text{order\_lines.line\_subtotal})$. |
| `discount_amount` | Decimal | Required | $\ge 0.00$ | USD ($) | Non-unique | Order-level promotional discount. Cannot exceed subtotal. |
| `tax_amount` | Decimal | Required | $\ge 0.00$ | USD ($) | Non-unique | Reconciled: `round((subtotal - discount) * 0.08, 2)`. |
| `shipping_fee` | Decimal | Required | `0.00` or `9.99` | USD ($) | Non-unique | Non-refundable logistics fee. ($0 if subtotal $\ge \$75$). |
| `total_paid_amount`| Decimal | Required | $\ge 0.00$ | USD ($) | Non-unique | Reconciled: `subtotal - discount + tax + shipping_fee`. |
| `payment_method` | String | Required | `CREDIT_CARD`, `DEBIT_CARD`, `PAYPAL`, `APPLE_PAY`, `STORE_CREDIT` | None | Non-unique | Payment instrument. |
| `order_status` | String | Required | `DELIVERED`, `SHIPPED`, `CANCELLED` | None | Non-unique | Only `DELIVERED` orders are eligible for return. |
| `delivery_date` | DateTime | Optional | ISO 8601 UTC string | UTC | Non-unique | Required for `DELIVERED`. Basis for return window calculation. |

---

### 2.2 Order Line Items (`order_lines`)
Individual product purchase items within an order.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Invariants |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `order_line_id` | String | Required | `ORDL-ORD-2026-\d{6}-\d{2}` | None | **Primary Key** | Composite line identifier. |
| `order_id` | String | Required | Valid `order_id` | None | **Foreign Key** | References `orders(order_id)`. |
| `line_number` | Integer | Required | `1` to `99` | Number | Non-unique | Sequential line position. |
| `sku` | String | Required | Valid `sku` | None | **Foreign Key** | References `products(sku)`. |
| `product_name` | String | Required | 1–100 characters | None | Non-unique | Copied snapshot product name. |
| `category` | String | Required | Valid category | None | Non-unique | Item classification. |
| `unit_price` | Decimal | Required | $> 0.00$ | USD ($) | Non-unique | Catalog unit price at purchase time. |
| `quantity` | Integer | Required | $\ge 1$ | Units | Non-unique | Units purchased. |
| `line_discount` | Decimal | Required | $\ge 0.00$ | USD ($) | Non-unique | Line-specific promotional discount. |
| `line_subtotal` | Decimal | Required | $> 0.00$ | USD ($) | Non-unique | Reconciled: `(unit_price * quantity) - line_discount`. |
| `return_window_days`| Integer| Required | `0, 14, 30` | Days | Non-unique | Allowed calendar window for return submission. |
| `is_final_sale` | Boolean | Required | `1` (True), `0` (False) | Flag | Non-unique | Final sale items cannot be returned. |

---

## 3. Transactional Returns & Event Log

### 3.1 Return Request (`return_requests`)
Customer return submission.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Invariants |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `request_id` | String | Required | `REQ-2026-\d{6}` | None | **Primary Key** | Sequential request identifier. |
| `order_id` | String | Required | Valid `order_id` | None | **Foreign Key** | References `orders(order_id)`. |
| `customer_id` | String | Required | Valid `customer_id` | None | **Foreign Key** | References `customers(customer_id)`. |
| `request_date` | DateTime | Required | ISO 8601 UTC string | UTC | Non-unique | Submission timestamp. Must be $\ge$ `delivery_date`. |
| `request_channel` | String | Required | `WEB_PORTAL`, `MOBILE_APP`, `CUSTOMER_SERVICE` | None | Non-unique | Originating channel. |
| `request_status` | String | Required | `SUBMITTED`, `APPROVED`, `PARTIALLY_APPROVED`, `REJECTED`, `CANCELLED` | None | Non-unique | Authorization status. |
| `customer_notes` | String | Optional | Up to 500 characters | None | Non-unique | Customer explanation. |

---

### 3.2 Return Line Items (`return_lines`)
Specific lines and quantities requested for return.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Invariants |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `return_line_id` | String | Required | `RMAL-RMA-2026-\d{6}-\d{2}` | None | **Primary Key** | Sequential RMA line identifier. |
| `request_id` | String | Required | Valid `request_id` | None | **Foreign Key** | References `return_requests(request_id)`. |
| `order_line_id` | String | Required | Valid `order_line_id` | None | **Foreign Key** | References `order_lines(order_line_id)`. |
| `requested_quantity`| Integer| Required | $\ge 1$ | Units | Non-unique | Invariant: $\le$ `order_lines.quantity` minus previously returned quantity. |
| `return_reason` | String | Required | `DEFECTIVE`, `WRONG_ITEM`, `DOES_NOT_FIT`, `CHANGED_MIND`, `NOT_AS_DESCRIBED`, `ARRIVED_LATE`, `EXCHANGE_REQUESTED` | None | Non-unique | Reason for return. |
| `item_condition_reported`| String| Required | `UNOPENED`, `OPENED_UNUSED`, `USED`, `DAMAGED_TRANSIT`, `DEFECTIVE` | None | Non-unique | Stated condition. |

---

### 3.3 Return Merchandise Authorization (`return_authorizations`)
Official RMA approval records.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Invariants |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rma_id` | String | Required | `RMA-2026-\d{6}` | None | **Primary Key** | Sequential RMA identifier. |
| `request_id` | String | Required | Valid `request_id` | None | **Foreign Key, Unique**| 1:1 with `return_requests`. |
| `authorization_date`| DateTime| Required | ISO 8601 UTC string | UTC | Non-unique | Must be $\ge$ `return_requests.request_date`. |
| `authorization_status`| String| Required | `APPROVED`, `PARTIALLY_APPROVED`, `REJECTED`, `EXPIRED`, `CANCELLED` | None | Non-unique | Overall RMA state. |
| `total_approved_quantity`| Integer| Required | $\ge 0$ | Units | Non-unique | Sum of approved line quantities. |
| `policy_override_applied`| Boolean| Required | `1` (True), `0` (False) | Flag | Non-unique | Indicates if manager exception was granted. |
| `override_reason`| String | Optional | 1–255 characters | None | Non-unique | Required if override applied. |
| `authorized_by` | String | Required | `SYSTEM_AUTO`, `OPS_MANAGER_01`, `OPS_MANAGER_02` | None | Non-unique | Authorizing agent. |
| `rma_expiration_date`| DateTime| Required | ISO 8601 UTC string | UTC | Non-unique | Standard: `authorization_date + 30 days`. |

---

### 3.4 Inbound Return Shipment (`return_shipments`)
Inbound parcel tracking.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Invariants |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shipment_id` | String | Required | `RTS-2026-\d{6}` | None | **Primary Key** | Sequential inbound shipment identifier. |
| `rma_id` | String | Required | Valid `rma_id` | None | **Foreign Key** | References `return_authorizations(rma_id)`. |
| `tracking_number` | String | Required | `TRK-[A-Z]+-\d{8}` | None | **Unique** | Carrier tracking number. |
| `carrier` | String | Required | `UPS`, `FEDEX`, `USPS`, `DHL` | None | Non-unique | Logistics provider. |
| `shipped_date` | DateTime | Optional | ISO 8601 UTC string | UTC | Non-unique | Must be $\ge$ `authorization_date`. |
| `received_date` | DateTime | Optional | ISO 8601 UTC string | UTC | Non-unique | Required for `DELIVERED`. Must be $\ge$ `shipped_date`. |
| `shipment_status` | String | Required | `LABEL_CREATED`, `IN_TRANSIT`, `DELIVERED`, `EXCEPTION_LOST`, `RETURNED_TO_SENDER` | None | Non-unique | Carrier transit state. |
| `origin_zip` | String | Required | 5-digit US Zip | None | Non-unique | Origin postal code. |
| `destination_warehouse`| String| Required | `WH-EAST-01`, `WH-WEST-01`, `WH-CENTRAL-01` | None | Non-unique | Destination warehouse dock. |

---

### 3.5 Physical Inspection (`inspections`)
Warehouse receiving and grading audit.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Invariants |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `inspection_id` | String | Required | `INS-2026-\d{6}` | None | **Primary Key** | Sequential inspection report ID. |
| `rma_id` | String | Required | Valid `rma_id` | None | **Foreign Key** | References `return_authorizations(rma_id)`. |
| `return_line_id` | String | Required | Valid `return_line_id` | None | **Foreign Key** | References `return_lines(return_line_id)`. |
| `shipment_id` | String | Required | Valid `shipment_id` | None | **Foreign Key** | References `return_shipments(shipment_id)`. |
| `inspection_date`| DateTime | Required | ISO 8601 UTC string | UTC | Non-unique | Must be $\ge$ `received_date`. |
| `inspector_id` | String | Required | `INSP-OP-01` to `INSP-OP-05` | None | Non-unique | Operator credential. |
| `received_quantity`| Integer | Required | $\ge 0$ | Units | Non-unique | Physical item count received. |
| `inspected_sku` | String | Required | Valid SKU | None | Non-unique | Physical SKU found. |
| `item_grade` | String | Required | `GRADE_A_NEW`, `GRADE_B_OPEN_BOX`, `GRADE_C_REFURBISHABLE`, `GRADE_D_DAMAGED`, `COUNTERFEIT_FRAUD` | None | Non-unique | Physical condition grade. |
| `packaging_intact` | Boolean| Required | `1` (True), `0` (False) | Flag | Non-unique | Packaging condition. |
| `serial_number_verified`| Boolean| Required | `1` (True), `0` (False) | Flag | Non-unique | Serial authenticity check. |
| `discrepancy_flag`| Boolean | Required | `1` (True), `0` (False) | Flag | Non-unique | Flagged if SKU/serial mismatch or counterfeit. |
| `inspection_notes`| String | Optional | Text | None | Non-unique | Operator physical remarks. |

---

### 3.6 Inventory Disposition (`inventory_dispositions`)
Warehouse bin placement and asset recovery routing.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Invariants |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `disposition_id` | String | Required | `DISP-2026-\d{6}` | None | **Primary Key** | Sequential disposition movement order. |
| `inspection_id` | String | Required | Valid `inspection_id` | None | **Foreign Key, Unique**| 1:1 with `inspections`. |
| `rma_id` | String | Required | Valid `rma_id` | None | **Foreign Key** | References `return_authorizations(rma_id)`. |
| `disposition_date`| DateTime| Required | ISO 8601 UTC string | UTC | Non-unique | **Temporal Invariant**: Must be $\ge$ `inspections.inspection_date`. |
| `disposition_action`| String| Required | `RESTOCK_PRIMARY`, `RESTOCK_OUTLET`, `SEND_TO_REFURBISH`, `QUARANTINE_FRAUD`, `SCRAP_RECYCLE` | None | Non-unique | Inventory movement destination. |
| `target_bin_location`| String| Required | `BIN-PRIMARY-A1`, `BIN-OUTLET-B2`, `BIN-REFURB-C3`, `BIN-SCRAP-D4`, `BIN-QUARANTINE-Q9` | None | Non-unique | Physical staging bin. |
| `unit_cost_recovery`| Decimal| Required | $\ge 0.00$ | USD ($) | Non-unique | Expected recovered inventory value. |
| `operator_id` | String | Required | Operator identifier | None | Non-unique | Staff executing warehouse movement. |

---

### 3.7 Financial Refund Ledger (`refunds`)
Financial settlement transactions.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Invariants |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `refund_id` | String | Required | `REF-2026-\d{6}` | None | **Primary Key** | Sequential refund payment ID. |
| `rma_id` | String | Required | Valid `rma_id` | None | **Foreign Key, Unique**| **Duplicate Protection**: Unique index enforces 1 refund per RMA. |
| `customer_id` | String | Required | Valid `customer_id` | None | **Foreign Key** | References `customers(customer_id)`. |
| `refund_date` | DateTime | Required | ISO 8601 UTC string | UTC | Non-unique | Must be $\ge$ `inspections.inspection_date`. |
| `gross_item_amount`| Decimal| Required | $\ge 0.00$ | USD ($) | Non-unique | Sum of approved item line subtotals. |
| `prorated_discount`| Decimal| Required | $\ge 0.00$ | USD ($) | Non-unique | Prorated order promotional discount reversal. |
| `tax_refund_amount`| Decimal| Required | $\ge 0.00$ | USD ($) | Non-unique | Prorated sales tax refund. |
| `restocking_fee` | Decimal | Required | $\ge 0.00$ | USD ($) | Non-unique | Restocking fee (15% for opened electronics; 0% if defective/wrong item). |
| `net_refund_amount`| Decimal| Required | $\ge 0.00$ | USD ($) | Non-unique | **Financial Invariant**: `gross - discount + tax - fee <= total_paid_amount`. |
| `refund_method` | String | Required | `ORIGINAL_PAYMENT`, `STORE_CREDIT`, `CHECK` | None | Non-unique | Settlement channel. |
| `refund_status` | String | Required | `COMPLETED`, `PENDING_CLEARANCE`, `BLOCKED_FRAUD`, `REVERSED` | None | Non-unique | Payment clearance state. |
| `idempotency_key` | String | Required | SHA-256 Hash string | None | **Unique** | Network idempotency token. |

---

### 3.8 Append-Only Return Lifecycle Events Log (`return_events`)
Immutable audit event-stream capturing all historical state changes.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Invariants |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `event_id` | String | Required | `EVT-2026-\d{6}` | None | **Primary Key** | Sequential event log identifier. |
| `rma_id` | String | Optional | Valid `rma_id` | None | Non-unique | Associated RMA identifier (if authorized). |
| `request_id` | String | Required | Valid `request_id` | None | **Foreign Key** | References `return_requests(request_id)`. |
| `event_type` | String | Required | `RETURN_REQUEST_SUBMITTED`, `RMA_AUTHORIZED`, `RETURN_SHIPMENT_DISPATCHED`, `RETURN_SHIPMENT_DELIVERED`, `WAREHOUSE_INSPECTION_COMPLETED`, `INVENTORY_DISPOSITION_RECORDED`, `REFUND_ISSUED`, `POLICY_OVERRIDE_RECORDED` | None | Non-unique | Domain event type. |
| `from_status` | String | Optional | Lifecycle state string | None | Non-unique | State before transition (NULL for creation). |
| `to_status` | String | Required | Lifecycle state string | None | Non-unique | State after transition. |
| `actor_role` | String | Required | `CUSTOMER`, `LOGISTICS_CARRIER`, `WAREHOUSE_OPERATOR`, `OPS_MANAGER`, `FINANCE`, `SYSTEM` | None | Non-unique | Initiating actor persona. |
| `actor_id` | String | Required | Actor credential identifier | None | Non-unique | Individual or automated service executing action. |
| `timestamp` | DateTime | Required | ISO 8601 UTC string | UTC | Non-unique | Exact chronological event timestamp. |
| `details` | String | Optional | Narrative description | None | Non-unique | Contextual audit notes. |

---

## 4. Isolated Anomaly Manifest (`ground_truth_anomalies`)

Strictly isolated table and CSV/JSON datasets. Never leaked into operational features.

| Field Name | Type | Req/Opt | Allowed Values / Format | Uniqueness | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `anomaly_id` | String | Required | `ANO-\d{6}` | **Primary Key** | Sequential anomaly identifier. |
| `entity_name` | String | Required | Table name string | Non-unique | Affected table. |
| `entity_id` | String | Required | Record ID string | Non-unique | Primary key of affected row. |
| `parent_entity_id`| String| Optional | Parent ID string | Non-unique | Originating parent entity. |
| `issue_type` | String | Required | `QTY_EXCEEDS_PURCHASED`, `REFUND_EXCEEDS_PAID`, `RESTOCK_BEFORE_INSPECTION`, `RETURN_PAST_POLICY_WINDOW`, `DUPLICATE_REFUND_ATTEMPT` | Non-unique | Anomaly category. |
| `expected_decision`| String| Required | Decision string | Non-unique | What a compliant policy engine must decide. |
| `actual_injected_behavior` | String | Required | Text explanation | Non-unique | Detailed description of injected violation. |
| `created_at` | DateTime | Required | ISO 8601 UTC string | Non-unique | Anomaly injection timestamp. |
