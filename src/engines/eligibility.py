"""
Return Eligibility and Policy Decision Engine
Evaluates return windows, category restrictions, customer tiers, and purchased quantity invariants.
"""

from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, List, Dict
from src.config import CATEGORY_RETURN_WINDOWS, CUSTOMER_TIER_OVERRIDE_WINDOWS


@dataclass
class EligibilityResult:
    is_eligible: bool
    approved_quantity: int
    requested_quantity: int
    decision: str  # APPROVED, PARTIALLY_APPROVED, REJECTED
    rejection_reason: Optional[str] = None
    applied_return_window_days: int = 30
    days_since_delivery: Optional[int] = None
    is_override: bool = False


class EligibilityEngine:
    @staticmethod
    def evaluate_line_eligibility(
        order_status: str,
        delivery_date: Optional[datetime],
        request_date: datetime,
        category: str,
        is_final_sale: bool,
        customer_tier: str,
        purchased_quantity: int,
        previously_returned_quantity: int,
        requested_quantity: int,
        manager_override: bool = False,
        override_reason: Optional[str] = None
    ) -> EligibilityResult:
        """
        Evaluates return eligibility for an order line item against documented business policies.
        """
        # Rule 1: Order must be DELIVERED
        if order_status != "DELIVERED" or delivery_date is None:
            return EligibilityResult(
                is_eligible=False,
                approved_quantity=0,
                requested_quantity=requested_quantity,
                decision="REJECTED",
                rejection_reason="ORDER_NOT_DELIVERED"
            )

        # Rule 2: Quantity invariant check
        remaining_returnable_qty = purchased_quantity - previously_returned_quantity
        if requested_quantity > remaining_returnable_qty:
            return EligibilityResult(
                is_eligible=False,
                approved_quantity=0,
                requested_quantity=requested_quantity,
                decision="REJECTED",
                rejection_reason=f"REQUESTED_QTY_EXCEEDS_PURCHASED: requested {requested_quantity}, available {remaining_returnable_qty}"
            )

        # Rule 3: Final Sale and Perishable Exclusions
        if is_final_sale or category in ["PERISHABLE", "FINAL_SALE"]:
            if not manager_override:
                return EligibilityResult(
                    is_eligible=False,
                    approved_quantity=0,
                    requested_quantity=requested_quantity,
                    decision="REJECTED",
                    rejection_reason=f"CATEGORY_NON_RETURNABLE: {category} items are final sale"
                )

        # Rule 4: Return Window Calculation
        base_window = CATEGORY_RETURN_WINDOWS.get(category, 30)
        if base_window == 0:
            allowed_window = 0
        elif customer_tier in ["VIP", "PLATINUM"]:
            allowed_window = max(base_window, CUSTOMER_TIER_OVERRIDE_WINDOWS.get(customer_tier, 30))
        else:
            allowed_window = base_window

        # Calculate calendar days since delivery
        delta = request_date - delivery_date
        days_since_delivery = max(0, delta.days)

        if days_since_delivery > allowed_window:
            if not manager_override:
                return EligibilityResult(
                    is_eligible=False,
                    approved_quantity=0,
                    requested_quantity=requested_quantity,
                    decision="REJECTED",
                    rejection_reason=f"OUTSIDE_RETURN_WINDOW: requested at day {days_since_delivery}, window is {allowed_window} days",
                    applied_return_window_days=allowed_window,
                    days_since_delivery=days_since_delivery
                )
            else:
                return EligibilityResult(
                    is_eligible=True,
                    approved_quantity=requested_quantity,
                    requested_quantity=requested_quantity,
                    decision="APPROVED",
                    rejection_reason=f"MANAGER_OVERRIDE_APPLIED: {override_reason or 'Customer goodwill'}",
                    applied_return_window_days=allowed_window,
                    days_since_delivery=days_since_delivery,
                    is_override=True
                )

        # Passed all policy checks
        return EligibilityResult(
            is_eligible=True,
            approved_quantity=requested_quantity,
            requested_quantity=requested_quantity,
            decision="APPROVED",
            applied_return_window_days=allowed_window,
            days_since_delivery=days_since_delivery,
            is_override=False
        )
