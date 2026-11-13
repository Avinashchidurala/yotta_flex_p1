"""
Inventory Disposition Engine
Determines warehouse bin routing, cost recovery, and restocking authorization based on inspection grades.
Uses Decimal fixed-point arithmetic for asset valuation.
"""

from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any
from decimal import Decimal, ROUND_HALF_UP
from src.config import DISPOSITION_VALUE_RECOVERY

TWOPLACES = Decimal("0.01")


@dataclass
class DispositionResult:
    disposition_id: str
    inspection_id: str
    rma_id: str
    disposition_date: datetime
    disposition_action: str
    target_bin_location: str
    unit_cost_recovery: Decimal
    operator_id: str
    is_temporal_anomaly: bool = False


class DispositionEngine:
    @staticmethod
    def determine_disposition(
        disposition_id: str,
        inspection_id: str,
        rma_id: str,
        inspection_date: datetime,
        disposition_date: datetime,
        item_grade: str,
        unit_price: Any,
        operator_id: str = "OP-WH-01",
        force_anomaly: bool = False
    ) -> DispositionResult:
        """
        Calculates disposition action, warehouse bin location, and asset recovery.
        Checks invariant: disposition_date >= inspection_date.
        """
        if isinstance(inspection_date, str):
            inspection_date = datetime.fromisoformat(inspection_date)
        if isinstance(disposition_date, str):
            disposition_date = datetime.fromisoformat(disposition_date)

        is_anomaly = False
        if disposition_date < inspection_date:
            if not force_anomaly:
                raise ValueError(
                    f"Temporal invariant violation: disposition_date ({disposition_date}) "
                    f"cannot occur before inspection_date ({inspection_date})"
                )
            is_anomaly = True

        recovery_rate = DISPOSITION_VALUE_RECOVERY.get(item_grade, Decimal("0.00"))
        unit_dec = Decimal(str(unit_price))
        unit_cost_recovery = (unit_dec * recovery_rate).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

        if item_grade == "GRADE_A_NEW":
            action = "RESTOCK_PRIMARY"
            bin_loc = "BIN-PRIMARY-A1"
        elif item_grade == "GRADE_B_OPEN_BOX":
            action = "RESTOCK_OUTLET"
            bin_loc = "BIN-OUTLET-B2"
        elif item_grade == "GRADE_C_REFURBISHABLE":
            action = "SEND_TO_REFURBISH"
            bin_loc = "BIN-REFURB-C3"
        elif item_grade == "GRADE_D_DAMAGED":
            action = "SCRAP_RECYCLE"
            bin_loc = "BIN-SCRAP-D4"
        elif item_grade == "COUNTERFEIT_FRAUD":
            action = "QUARANTINE_FRAUD"
            bin_loc = "BIN-QUARANTINE-Q9"
        else:
            action = "SCRAP_RECYCLE"
            bin_loc = "BIN-SCRAP-D4"

        return DispositionResult(
            disposition_id=disposition_id,
            inspection_id=inspection_id,
            rma_id=rma_id,
            disposition_date=disposition_date,
            disposition_action=action,
            target_bin_location=bin_loc,
            unit_cost_recovery=unit_cost_recovery,
            operator_id=operator_id,
            is_temporal_anomaly=is_anomaly
        )
