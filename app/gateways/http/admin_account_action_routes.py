"""
Platform admin: actions on a client's account (R13), each with the admin's
reason and an ADMIN_* entry in the client's audit log. They need a role
that manages billing (SUPER or BILLING; support gets 403) and a recent
sign-in (step-up).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.admin_actions import (
    AdminActionReceipt,
    AdminReasonBody,
    ExtendTrialBody,
    ExtendTrialCommand,
    GiveDiscountBody,
    GiveDiscountCommand,
    GrantCreditBody,
    GrantCreditCommand,
    MarkInvoicePaidBody,
    MarkInvoicePaidCommand,
    OverridePlanBody,
    OverridePlanCommand,
    WaiveSetupFeeCommand,
)
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_trial_body = build_json_body_dependency(ExtendTrialBody)
read_discount_body = build_json_body_dependency(GiveDiscountBody)
read_credit_body = build_json_body_dependency(GrantCreditBody)
read_reason_body = build_json_body_dependency(AdminReasonBody)
read_payment_body = build_json_body_dependency(MarkInvoicePaidBody)
read_plan_body = build_json_body_dependency(OverridePlanBody)

type ActionOperator[Command] = OperatorContract[Command, AdminActionReceipt]
CLIENT_PATH: str = "/v1/admin/clients/{business_id}"


def client_id(raw: str) -> BusinessId:
    return parse_path_identifier(raw, BusinessId, "Business")


def build_admin_account_action_router(
    extend_trial_operator: ActionOperator[ExtendTrialCommand],
    give_discount_operator: ActionOperator[GiveDiscountCommand],
    grant_credit_operator: ActionOperator[GrantCreditCommand],
    waive_setup_fee_operator: ActionOperator[WaiveSetupFeeCommand],
    mark_invoice_paid_operator: ActionOperator[MarkInvoicePaidCommand],
    override_plan_operator: ActionOperator[OverridePlanCommand],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token of a SUPER or BILLING platform admin, step-up):
        POST …/trial-extension      {"days", "reason"}
        POST …/discount             {"percent", "last_day", "reason"}
        POST …/credits              {"amount_minor", "reason"}
        POST …/setup-fee-waiver     {"reason"}
        POST …/invoices/{invoice_id}/manual-payment
                                    {"method", "reference", "reason"}
        POST …/plan                 {"plan_key", "billing_period"?, "reason"}
    (… is /v1/admin/clients/{business_id}); each answers what the audit log
    recorded.
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.post(
        f"{CLIENT_PATH}/trial-extension",
        openapi_extra=describe_json_body(ExtendTrialBody),
    )
    def extend_trial(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ExtendTrialBody, Depends(read_trial_body)],
    ) -> AdminActionReceipt:
        return extend_trial_operator.operate(
            ExtendTrialCommand(
                user_id=user_id,
                business_id=client_id(business_id),
                body=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        f"{CLIENT_PATH}/discount", openapi_extra=describe_json_body(GiveDiscountBody)
    )
    def give_discount(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[GiveDiscountBody, Depends(read_discount_body)],
    ) -> AdminActionReceipt:
        return give_discount_operator.operate(
            GiveDiscountCommand(
                user_id=user_id,
                business_id=client_id(business_id),
                body=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        f"{CLIENT_PATH}/credits", openapi_extra=describe_json_body(GrantCreditBody)
    )
    def grant_credit(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[GrantCreditBody, Depends(read_credit_body)],
    ) -> AdminActionReceipt:
        return grant_credit_operator.operate(
            GrantCreditCommand(
                user_id=user_id,
                business_id=client_id(business_id),
                body=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        f"{CLIENT_PATH}/setup-fee-waiver",
        openapi_extra=describe_json_body(AdminReasonBody),
    )
    def waive_setup_fee(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AdminReasonBody, Depends(read_reason_body)],
    ) -> AdminActionReceipt:
        return waive_setup_fee_operator.operate(
            WaiveSetupFeeCommand(
                user_id=user_id,
                business_id=client_id(business_id),
                body=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        f"{CLIENT_PATH}/invoices/{{invoice_id}}/manual-payment",
        openapi_extra=describe_json_body(MarkInvoicePaidBody),
    )
    def mark_invoice_paid(
        request: Request,
        business_id: str,
        invoice_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[MarkInvoicePaidBody, Depends(read_payment_body)],
    ) -> AdminActionReceipt:
        return mark_invoice_paid_operator.operate(
            MarkInvoicePaidCommand(
                user_id=user_id,
                business_id=client_id(business_id),
                invoice_id=parse_path_identifier(invoice_id, InvoiceId, "Invoice"),
                body=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        f"{CLIENT_PATH}/plan", openapi_extra=describe_json_body(OverridePlanBody)
    )
    def override_plan(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[OverridePlanBody, Depends(read_plan_body)],
    ) -> AdminActionReceipt:
        return override_plan_operator.operate(
            OverridePlanCommand(
                user_id=user_id,
                business_id=client_id(business_id),
                body=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
