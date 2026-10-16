"""Deposits: the owner's payment pages and policies, "Paid", and the report."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.deposits.deposit_report import DepositReport, DepositReportQuery
from app.schemas.dto.deposits.deposit_settings import (
    AddPaymentLinkCommand,
    DepositPolicyRequest,
    DepositSettingsQuery,
    DepositSettingsRequest,
    DepositSettingsView,
    PaymentLinkInput,
    RemovePaymentLinkCommand,
    SetDepositPolicyCommand,
    UpdateDepositSettingsCommand,
)
from app.schemas.dto.deposits.deposit_views import (
    DepositRequestQuery,
    DepositRequestView,
    MarkDepositPaidCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deposits.constrained_integers import DepositReportDays
from app.schemas.typings.deposits.prefixed_id import DepositRequestId, PaymentLinkId
from app.schemas.typings.users.prefixed_id import UserId

read_settings_body = build_json_body_dependency(DepositSettingsRequest)
read_link_body = build_json_body_dependency(PaymentLinkInput)
read_policy_body = build_json_body_dependency(DepositPolicyRequest)
B: str = "/v1/businesses/{business_id}"
DEFAULT_REPORT_DAYS: DepositReportDays = DepositReportDays(90)


def business(raw_id: str) -> BusinessId:
    return parse_path_identifier(raw_id, BusinessId, "Business")


def deposit(raw_id: str) -> DepositRequestId:
    return parse_path_identifier(raw_id, DepositRequestId, "Deposit")


def report_days(raw_days: str) -> DepositReportDays:
    return DepositReportDays(int(raw_days))


def build_deposit_router(
    current_user: CurrentUserDependency,
    get_settings: OperatorContract[DepositSettingsQuery, DepositSettingsView],
    update_settings: OperatorContract[
        UpdateDepositSettingsCommand, DepositSettingsView
    ],
    add_link: OperatorContract[AddPaymentLinkCommand, DepositSettingsView],
    remove_link: OperatorContract[RemovePaymentLinkCommand, DepositSettingsView],
    set_policy: OperatorContract[SetDepositPolicyCommand, DepositSettingsView],
    get_deposit: OperatorContract[DepositRequestQuery, DepositRequestView],
    mark_paid: OperatorContract[MarkDepositPaidCommand, DepositRequestView],
    get_report: OperatorContract[DepositReportQuery, DepositReport],
) -> APIRouter:
    """
    Routes (all require a bearer token):
        GET    /v1/businesses/{business_id}/deposit-settings
                    deposits on or off, the hold, the refund cutoff, the
                    payment pages and the policies (owners and staff)
        PUT    /v1/businesses/{business_id}/deposit-settings
                    {is_enabled, hold_minutes 15-1440, refund_cutoff_hours
                    0-720, default_payment_link_id} (owners; audited)
        POST   /v1/businesses/{business_id}/deposit-settings/payment-links
                    {label, kind static|template, address https} (owners;
                    audited; a page that carries a key is sealed); 201
        DELETE /v1/businesses/{business_id}/deposit-settings/payment-links/{id}
                    (owners; audited); 204
        PUT    /v1/businesses/{business_id}/deposit-settings/policies
                    {target, resource_id | service_item_id, policy | null}
                    the deposit of a resource, a service or the banquets
                    (owners; audited)
        GET    /v1/businesses/{business_id}/deposits/{deposit_id}
                    one deposit: amount, reference, state (owners and staff)
        POST   /v1/businesses/{business_id}/deposits/{deposit_id}/paid
                    staff saw the money: PAID, the booking confirmed
                    (owners and staff; audited; 409 status_changed once the
                    hold ran out)
        GET    /v1/businesses/{business_id}/deposit-report?days=7-366
                    deposits collected and the no-show rate with and
                    without a deposit (owners)
    """

    router = APIRouter(tags=["deposits"], responses=standard_error_responses())

    @router.get(f"{B}/deposit-settings")
    def get_deposit_settings(
        business_id: str, user_id: Annotated[UserId, Depends(current_user)]
    ) -> DepositSettingsView:
        return get_settings.operate(
            DepositSettingsQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.put(
        f"{B}/deposit-settings",
        openapi_extra=describe_json_body(DepositSettingsRequest),
    )
    def update_deposit_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[DepositSettingsRequest, Depends(read_settings_body)],
    ) -> DepositSettingsView:
        return update_settings.operate(
            UpdateDepositSettingsCommand(
                user_id=user_id, business_id=business(business_id), request=body
            )
        )

    @router.post(
        f"{B}/deposit-settings/payment-links",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(PaymentLinkInput),
    )
    def add_payment_link(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[PaymentLinkInput, Depends(read_link_body)],
    ) -> DepositSettingsView:
        return add_link.operate(
            AddPaymentLinkCommand(
                user_id=user_id, business_id=business(business_id), link=body
            )
        )

    @router.delete(
        f"{B}/deposit-settings/payment-links/{{link_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def remove_payment_link(
        business_id: str,
        link_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        remove_link.operate(
            RemovePaymentLinkCommand(
                user_id=user_id,
                business_id=business(business_id),
                link_id=parse_path_identifier(link_id, PaymentLinkId, "Payment link"),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(
        f"{B}/deposit-settings/policies",
        openapi_extra=describe_json_body(DepositPolicyRequest),
    )
    def set_deposit_policy(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[DepositPolicyRequest, Depends(read_policy_body)],
    ) -> DepositSettingsView:
        return set_policy.operate(
            SetDepositPolicyCommand(
                user_id=user_id, business_id=business(business_id), request=body
            )
        )

    @router.get(f"{B}/deposits/{{deposit_id}}")
    def get_booking_deposit(
        business_id: str,
        deposit_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> DepositRequestView:
        return get_deposit.operate(
            DepositRequestQuery(
                user_id=user_id,
                business_id=business(business_id),
                request_id=deposit(deposit_id),
            )
        )

    @router.post(f"{B}/deposits/{{deposit_id}}/paid")
    def mark_deposit_paid(
        business_id: str,
        deposit_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> DepositRequestView:
        return mark_paid.operate(
            MarkDepositPaidCommand(
                user_id=user_id,
                business_id=business(business_id),
                request_id=deposit(deposit_id),
            )
        )

    @router.get(f"{B}/deposit-report")
    def get_deposit_report(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        days: Annotated[str | None, Query()] = None,
    ) -> DepositReport:
        return get_report.operate(
            DepositReportQuery(
                user_id=user_id,
                business_id=business(business_id),
                days=parse_optional(days, report_days, "days") or DEFAULT_REPORT_DAYS,
            )
        )

    return router
