"""
Warehouse Inspection Engine
Handles physical merchandise receipt, condition verification, grading, and discrepancy detection.
"""

from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class InspectionResult:
    inspection_id: str
    rma_id: str
    return_line_id: str
    shipment_id: str
    inspection_date: datetime
    inspector_id: str
    received_quantity: int
    inspected_sku: str
    item_grade: str
    packaging_intact: bool
    serial_number_verified: bool
    discrepancy_flag: bool
    inspection_notes: Optional[str] = None


class InspectionEngine:
    @staticmethod
    def inspect_item(
        inspection_id: str,
        rma_id: str,
        return_line_id: str,
        shipment_id: str,
        shipment_received_date: datetime,
        inspection_date: datetime,
        inspector_id: str,
        approved_quantity: int,
        received_quantity: int,
        expected_sku: str,
        actual_sku: str,
        reported_condition: str,
        packaging_intact: bool,
        serial_verified: bool,
        is_counterfeit: bool = False
    ) -> InspectionResult:
        """
        Executes physical receiving inspection and assigns quality grade.
        Enforces temporal invariant: inspection_date >= shipment_received_date.
        """
        if isinstance(shipment_received_date, str):
            shipment_received_date = datetime.fromisoformat(shipment_received_date)
        if isinstance(inspection_date, str):
            inspection_date = datetime.fromisoformat(inspection_date)

        if inspection_date < shipment_received_date:
            raise ValueError(f"Temporal violation: inspection_date {inspection_date} cannot precede shipment received_date {shipment_received_date}")

        # Check for discrepancies
        has_qty_discrepancy = (received_quantity != approved_quantity)
        has_sku_discrepancy = (actual_sku != expected_sku)
        discrepancy_flag = has_qty_discrepancy or has_sku_discrepancy or is_counterfeit or not serial_verified

        # Assign Grade based on physical properties
        if is_counterfeit:
            item_grade = "COUNTERFEIT_FRAUD"
            notes = "Counterfeit item detected; serial number failed verification."
        elif not packaging_intact or reported_condition in ["DAMAGED_TRANSIT", "DEFECTIVE"]:
            item_grade = "GRADE_D_DAMAGED"
            notes = "Significant packaging damage or functional defect observed."
        elif reported_condition == "USED":
            item_grade = "GRADE_C_REFURBISHABLE"
            notes = "Item exhibits signs of normal wear; eligible for refurbishment."
        elif reported_condition == "OPENED_UNUSED":
            item_grade = "GRADE_B_OPEN_BOX"
            notes = "Packaging opened but merchandise pristine with all original tags/accessories."
        else:
            item_grade = "GRADE_A_NEW"
            notes = "Factory sealed, unopened, like-new inventory."

        if has_sku_discrepancy:
            notes += f" WARNING: Expected SKU {expected_sku}, received {actual_sku}."

        return InspectionResult(
            inspection_id=inspection_id,
            rma_id=rma_id,
            return_line_id=return_line_id,
            shipment_id=shipment_id,
            inspection_date=inspection_date,
            inspector_id=inspector_id,
            received_quantity=received_quantity,
            inspected_sku=actual_sku,
            item_grade=item_grade,
            packaging_intact=packaging_intact,
            serial_number_verified=serial_verified,
            discrepancy_flag=discrepancy_flag,
            inspection_notes=notes
        )
