# Reverse Logistics State Machine & Lifecycle Matrix

This document defines the formal state transitions, invariants, and guard conditions across the returns lifecycle.

---

## 1. End-to-End Lifecycle State Diagram

```mermaid
stateDiagram-v2
    [*] --> OrderDelivered: Customer Receives Delivery
    
    OrderDelivered --> ReturnSubmitted: Customer / Store Initiates Request
    
    ReturnSubmitted --> RMA_Approved: Policy Passed (Eligible Qty, Category, Window)
    ReturnSubmitted --> RMA_PartiallyApproved: Partial Line Items Eligible
    ReturnSubmitted --> RMA_Rejected: Ineligible (Window Expired / Final Sale)
    RMA_Rejected --> RMA_Approved: Manager Policy Override Applied
    
    RMA_Approved --> InboundLabelCreated: Generate RTS Tracking
    InboundLabelCreated --> InTransit: Carrier Scan
    InTransit --> DeliveredToWarehouse: Facility Intake
    InTransit --> ShipmentLost: Transit Exception
    
    DeliveredToWarehouse --> Inspected: Physical Receiving & Grading
    
    state Inspected {
        [*] --> GradeA: Sealed / New
        [*] --> GradeB: Open Box
        [*] --> GradeC: Used / Refurbishable
        [*] --> GradeD: Damaged / Broken
        [*] --> GradeFraud: Counterfeit / Wrong Item
    }
    
    GradeA --> RestockPrimary: 100% Recovery (BIN-PRIMARY-A1)
    GradeB --> RestockOutlet: 80% Recovery (BIN-OUTLET-B2)
    GradeC --> SendToRefurbish: 50% Recovery (BIN-REFURB-C3)
    GradeD --> ScrapRecycle: 0% Recovery (BIN-SCRAP-D4)
    GradeFraud --> QuarantineFraud: 0% Recovery (BIN-QUAR-Q9)
    
    Inspected --> RefundIssued: Net Refund Calculated (Prorated Discount, Tax, Fee)
    GradeFraud --> RefundBlocked: Fraud Quarantine Stops Financial Payout
    
    RefundIssued --> [*]
    RefundBlocked --> [*]
    ShipmentLost --> [*]
```

---

## 2. Entity State Transition Matrices

### 2.1 ReturnRequest (`return_requests`)
* Initial State: `SUBMITTED`
* Possible States: `SUBMITTED`, `UNDER_REVIEW`, `APPROVED`, `PARTIALLY_APPROVED`, `REJECTED`, `CANCELLED`

| From State | Event / Trigger | Guard Conditions | To State |
| :--- | :--- | :--- | :--- |
| `SUBMITTED` | Policy Evaluation | All lines eligible and within return window | `APPROVED` |
| `SUBMITTED` | Policy Evaluation | Subset of lines eligible | `PARTIALLY_APPROVED` |
| `SUBMITTED` | Policy Evaluation | All lines exceed window, final sale, or excess qty | `REJECTED` |
| `REJECTED` | Manager Review | `manager_override = TRUE` with logged reason | `APPROVED` |
| Any | Customer Cancel | Return shipment not yet created | `CANCELLED` |

---

### 2.2 ReturnShipment (`return_shipments`)
* Initial State: `LABEL_CREATED`
* Possible States: `LABEL_CREATED`, `IN_TRANSIT`, `DELIVERED`, `EXCEPTION_LOST`, `RETURNED_TO_SENDER`

| From State | Event / Trigger | Guard Conditions | To State |
| :--- | :--- | :--- | :--- |
| `LABEL_CREATED` | Carrier Origin Scan | Carrier receives parcel | `IN_TRANSIT` |
| `IN_TRANSIT` | Facility Destination Scan | Arrives at assigned warehouse dock | `DELIVERED` |
| `IN_TRANSIT` | Carrier Tracking Stalled | No movement for > 14 business days | `EXCEPTION_LOST` |
| `IN_TRANSIT` | Address/Label Undeliverable | Customer package unreturnable | `RETURNED_TO_SENDER` |

---

### 2.3 InventoryDisposition (`inventory_dispositions`)
* Prerequisite Guard: **`disposition_date >= inspection_date`**

| Item Grade | Physical Condition | Target Action | Warehouse Bin Location | Asset Value Recovery |
| :--- | :--- | :--- | :--- | :--- |
| `GRADE_A_NEW` | Factory sealed, perfect condition | `RESTOCK_PRIMARY` | `BIN-PRIMARY-A1` | 100% of purchase unit price |
| `GRADE_B_OPEN_BOX` | Opened packaging, pristine merchandise | `RESTOCK_OUTLET` | `BIN-OUTLET-B2` | 80% of purchase unit price |
| `GRADE_C_REFURBISHABLE` | Minor cosmetic wear, all parts present | `SEND_TO_REFURBISH` | `BIN-REFURB-C3` | 50% of purchase unit price |
| `GRADE_D_DAMAGED` | Crushed, broken, water damage | `SCRAP_RECYCLE` | `BIN-SCRAP-D4` | 0% (Scrapped & recycled) |
| `COUNTERFEIT_FRAUD` | Serial number mismatch, bootleg goods | `QUARANTINE_FRAUD` | `BIN-QUARANTINE-Q9`| 0% (Evidence locker) |

---

### 2.4 Refund (`refunds`)
* Guard: **`net_refund_amount <= order.total_paid_amount`**
* Guard: **`UNIQUE (rma_id)`** (Idempotency enforcement)

$$\text{Net Refund} = (\text{Approved Qty} \times \text{Unit Price}) - \text{Prorated Discount} + \text{Prorated Tax} - \text{Restocking Fee}$$

* Restocking Fee Waived when Return Reason $\in \{\text{DEFECTIVE}, \text{WRONG\_ITEM}\}$.
* 15% Restocking Fee applied to `ELECTRONICS` if Return Reason is `CHANGED_MIND`.

