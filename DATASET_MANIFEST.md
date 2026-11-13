# YottaFlex Return Management System (RMS) — Dataset Manifest

**Manifest Date**: November 13, 2026  
**Deterministic Random Seed**: `20261022`  
**Dataset SHA-256 Checksum**: `20e52efacd4177b7793653117f174f30d32450181c8a429f99046c0da122d174`  
**Expansion Ratio**: **+25% exactly** over original baseline  

---

## 1. Scale Comparison: Baseline vs Expanded (+25%)

| Dataset / Entity | Original Baseline Count | Target (+25%) | Actual Generated Count | Variance / Delta |
| :--- | :--- | :--- | :--- | :--- |
| **Orders (`orders`)** | 30,000 | **37,500** | **37,500** | **+25.0% (Exact)** |
| **Return Requests (`return_requests`)** | 5,000 | **6,250** | **6,250** | **+25.0% (Exact)** |
| **Return Line Items (`return_lines`)** | 8,000 | **10,000** | **10,000** | **+25.0% (Exact)** |
| **Customer Profiles (`customers`)** | 12,000 | **15,000** | **15,000** | **+25.0% (Exact)** |
| **Order Line Items (`order_lines`)** | 49,776 | 62,220 | **62,784** | **+26.1% (Poisson lines)** |
| **Return Authorizations (`return_authorizations`)**| 5,000 | **6,250** | **6,250** | **+25.0% (Exact)** |
| **Inbound Shipments (`return_shipments`)** | 4,281 | 5,351 | **5,562** | **+29.9%** |
| **Warehouse Inspections (`inspections`)** | 5,570 | 6,962 | **7,297** | **+31.0%** |
| **Inventory Dispositions (`inventory_dispositions`)**| 5,570 | 6,962 | **7,297** | **+31.0%** |
| **Financial Refunds (`refunds`)** | 3,964 | 4,955 | **5,110** | **+28.9%** |
| **Master Products Catalog (`products`)** | *(Unmodeled)* | 16 | **16 SKUs** | **16 Distinct SKUs** |
| **Lifecycle Return Events (`return_events`)** | *(Unmodeled)* | ~20,000 | **23,172 Events** | **Immutable Audit Stream** |
| **Ground Truth Anomalies (`ground_truth_anomalies`)**| 250 | 312 | **310 Anomalies** | **62 per category (5 types)** |

---

## 2. Canonical Entity Files (`data/raw/`)

All 12 entities are exported in both CSV and JSON formats:

| Entity Name | CSV File Path | JSON File Path | Row Count | Primary Key |
| :--- | :--- | :--- | :--- | :--- |
| **Products** | `data/raw/products.csv` | `data/raw/products.json` | 16 | `sku` |
| **Customers** | `data/raw/customers.csv` | `data/raw/customers.json` | 15,000 | `customer_id` |
| **Orders** | `data/raw/orders.csv` | `data/raw/orders.json` | 37,500 | `order_id` |
| **Order Lines** | `data/raw/order_lines.csv` | `data/raw/order_lines.json` | 62,784 | `order_line_id` |
| **Return Requests** | `data/raw/return_requests.csv` | `data/raw/return_requests.json` | 6,250 | `request_id` |
| **Return Lines** | `data/raw/return_lines.csv` | `data/raw/return_lines.json` | 10,000 | `return_line_id` |
| **Authorizations** | `data/raw/return_authorizations.csv` | `data/raw/return_authorizations.json` | 6,250 | `rma_id` |
| **Shipments** | `data/raw/return_shipments.csv` | `data/raw/return_shipments.json` | 5,562 | `shipment_id` |
| **Inspections** | `data/raw/inspections.csv` | `data/raw/inspections.json` | 7,297 | `inspection_id` |
| **Dispositions** | `data/raw/inventory_dispositions.csv` | `data/raw/inventory_dispositions.json` | 7,297 | `disposition_id` |
| **Refunds** | `data/raw/refunds.csv` | `data/raw/refunds.json` | 5,110 | `refund_id` |
| **Return Events** | `data/raw/return_events.csv` | `data/raw/return_events.json` | 23,172 | `event_id` |

---

## 3. Dedicated Anomaly Datasets (`data/anomalies/`)

Exported as isolated CSV and JSON files for targeted model evaluation and rule auditing:

| Anomaly Category | CSV File Path | JSON File Path | Injected Count | Expected Policy Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **Excess Return Quantity** | `data/anomalies/excess_return_quantity.csv` | `...json` | 62 | `REJECT_QUANTITY_OVERFLOW` |
| **Excess Refund** | `data/anomalies/excess_refund.csv` | `...json` | 62 | `BLOCK_EXCESS_PAYOUT` |
| **Restocking Before Inspection** | `data/anomalies/restocking_before_inspection.csv` | `...json` | 62 | `BLOCK_PREMATURE_RESTOCK` |
| **Expired Return Policy** | `data/anomalies/expired_return_policy.csv` | `...json` | 62 | `REJECTED_OR_OVERRIDE_REQUIRED` |
| **Duplicate Refund Attempt** | `data/anomalies/duplicate_refund.csv` | `...json` | 62 | `BLOCK_DUPLICATE_REFUND` |
| **Total Injected Anomalies** | — | — | **310** | **Balanced across 5 types** |

---

## 4. Master Ground Truth Manifest (`data/ground_truth/`)

* `data/ground_truth/ground_truth.csv` (310 records)
* `data/ground_truth/ground_truth.json` (310 records)

**Feature Leakage Protection**: Ground truth files are stored in a dedicated folder and SQLite table (`ground_truth_anomalies`) and are never joined or exposed to operational feature sets.

