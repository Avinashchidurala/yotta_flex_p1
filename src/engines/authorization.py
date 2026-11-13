"""
Return Merchandise Authorization (RMA) Engine
Orchestrates request-level authorizations and creates immutable RMA records.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from src.engines.eligibility import EligibilityEngine, EligibilityResult


@dataclass
class RMAEvaluationResult:
    rma_status: str  # APPROVED, PARTIALLY_APPROVED, REJECTED
    total_approved_quantity: int
    line_evaluations: List[Dict[str, Any]]
    policy_override_applied: bool
    override_reason: Optional[str]
    authorized_by: str
    expiration_date: datetime


class AuthorizationEngine:
    @staticmethod
    def process_return_request(
        request_id: str,
        order: Dict[str, Any],
        lines: List[Dict[str, Any]],
        request_date: datetime,
        customer_tier: str,
        manager_override: bool = False,
        override_reason: Optional[str] = None,
        authorized_by: str = "SYSTEM_AUTO"
    ) -> RMAEvaluationResult:
        """
        Processes all return lines for an order and determines overall RMA status.
        """
        line_evaluations = []
        total_requested = 0
        total_approved = 0
        any_override = False

        order_status = order.get("order_status")
        delivery_date = order.get("delivery_date")
        if isinstance(delivery_date, str):
            delivery_date = datetime.fromisoformat(delivery_date)
        if isinstance(request_date, str):
            request_date = datetime.fromisoformat(request_date)

        for line in lines:
            requested_qty = line["requested_quantity"]
            total_requested += requested_qty

            eval_res = EligibilityEngine.evaluate_line_eligibility(
                order_status=order_status,
                delivery_date=delivery_date,
                request_date=request_date,
                category=line.get("category", "APPAREL"),
                is_final_sale=line.get("is_final_sale", False),
                customer_tier=customer_tier,
                purchased_quantity=line.get("purchased_quantity", requested_qty),
                previously_returned_quantity=line.get("previously_returned_quantity", 0),
                requested_quantity=requested_qty,
                manager_override=manager_override,
                override_reason=override_reason
            )

            total_approved += eval_res.approved_quantity
            if eval_res.is_override:
                any_override = True

            line_evaluations.append({
                "return_line_id": line.get("return_line_id"),
                "order_line_id": line.get("order_line_id"),
                "requested_quantity": requested_qty,
                "approved_quantity": eval_res.approved_quantity,
                "is_eligible": eval_res.is_eligible,
                "decision": eval_res.decision,
                "rejection_reason": eval_res.rejection_reason
            })

        # Determine aggregate RMA Status
        if total_approved == total_requested and total_requested > 0:
            rma_status = "APPROVED"
        elif total_approved > 0:
            rma_status = "PARTIALLY_APPROVED"
        else:
            rma_status = "REJECTED"

        auth_actor = authorized_by
        if any_override and auth_actor == "SYSTEM_AUTO":
            auth_actor = "OPS_MANAGER_01"

        expiration_date = request_date + timedelta(days=30)

        return RMAEvaluationResult(
            rma_status=rma_status,
            total_approved_quantity=total_approved,
            line_evaluations=line_evaluations,
            policy_override_applied=any_override,
            override_reason=override_reason if any_override else None,
            authorized_by=auth_actor,
            expiration_date=expiration_date
        )
