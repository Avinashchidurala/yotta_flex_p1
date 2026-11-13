# YottaFlex RMS — Automated Validation & Integrity Audit Report

**Execution Timestamp**: 2026-11-13T02:51:04.172791

- **Total Checks Passed**: 44
- **Total Checks Failed**: 0

## 1. Audit Check Categories

| Category | Description | Status |
| :--- | :--- | :--- |
| **Primary Key Uniqueness** | 12 / 12 Tables checked with 0 duplicates | **PASSED (100%)** |
| **Foreign Key Integrity** | 17 Referential joins checked with 0 orphaned records | **PASSED (100%)** |
| **Missing / Null Values** | Mandatory fields checked with 0 nulls | **PASSED (100%)** |
| **Financial Reconciliation** | Subtotals, discounts, taxes, and net refunds reconciled using Decimal | **PASSED (100%)** |
| **Date Chronology** | Order $\le$ Delivery $\le$ Request $\le$ Auth $\le$ Ship $\le$ Inspection $\le$ Disp/Refund | **PASSED (100%)** |

## 2. Ground Truth Anomaly Recall & Precision

```json
{
  "QTY_EXCEEDS_PURCHASED": {
    "expected_count": 62,
    "detected_count": 62,
    "precision": 1.0,
    "recall": 1.0
  },
  "REFUND_EXCEEDS_PAID": {
    "expected_count": 62,
    "detected_count": 62,
    "precision": 1.0,
    "recall": 1.0
  },
  "RESTOCK_BEFORE_INSPECTION": {
    "expected_count": 62,
    "detected_count": 62,
    "precision": 1.0,
    "recall": 1.0
  },
  "RETURN_PAST_POLICY_WINDOW": {
    "expected_count": 62,
    "detected_count": 62,
    "precision": 1.0,
    "recall": 1.0
  },
  "DUPLICATE_REFUND_ATTEMPT": {
    "expected_count": 62,
    "detected_count": 62,
    "precision": 1.0,
    "recall": 1.0
  }
}
```
