"""The platform team's partners: the list, changes, codes and payouts."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.referrals.partner_admin import (
    AddPartnerCodeCommand,
    AddPartnerCodeRequest,
    AdminPartnersQuery,
    CreatePartnerCommand,
    CreatePartnerRequest,
    MarkPayoutPaidCommand,
    MarkPayoutPaidRequest,
    PartnerAdminView,
    PartnerList,
    PayoutReceipt,
    PayoutReportQuery,
    PayoutReportView,
    UpdatePartnerCommand,
    UpdatePartnerRequest,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.referrals.constrained_strings import CommissionMonth
from app.schemas.typings.referrals.prefixed_id import PartnerId
from app.schemas.typings.users.prefixed_id import UserId

read_create_body = build_json_body_dependency(CreatePartnerRequest)
read_update_body = build_json_body_dependency(UpdatePartnerRequest)
read_code_body = build_json_body_dependency(AddPartnerCodeRequest)
read_payout_body = build_json_body_dependency(MarkPayoutPaidRequest)


def build_admin_partner_router(
    *,
    current_user: CurrentUserDependency,
    list_partners: OperatorContract[AdminPartnersQuery, PartnerList],
    create_partner: OperatorContract[CreatePartnerCommand, PartnerAdminView],
    update_partner: OperatorContract[UpdatePartnerCommand, PartnerAdminView],
    add_partner_code: OperatorContract[AddPartnerCodeCommand, PartnerAdminView],
    get_payout_report: OperatorContract[PayoutReportQuery, PayoutReportView],
    mark_payout_paid: OperatorContract[MarkPayoutPaidCommand, PayoutReceipt],
) -> APIRouter:
    """
    Routes (bearer token; platform admins, changes audited):
        GET /v1/admin/partners
            every partner with codes, businesses brought and commissions
        POST /v1/admin/partners (201)
            a new partner: name, sign-in phone or e-mail, rate, first code
        PATCH /v1/admin/partners/{partner_id}
            rename, change the rate, pause or resume
        POST /v1/admin/partners/{partner_id}/codes
            another code for the partner (409 code_taken)
        GET /v1/admin/partners/payouts?month=YYYY-MM
            the month's commissions per partner and currency
        POST /v1/admin/partners/{partner_id}/payouts
            the partner was paid the month's commissions (reference kept)
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get("/v1/admin/partners")
    def get_partners(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> PartnerList:
        return list_partners.operate(AdminPartnersQuery(user_id=user_id))

    @router.post(
        "/v1/admin/partners",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(CreatePartnerRequest),
    )
    def post_partner(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CreatePartnerRequest, Depends(read_create_body)],
    ) -> PartnerAdminView:
        return create_partner.operate(
            CreatePartnerCommand(
                user_id=user_id,
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get("/v1/admin/partners/payouts")
    def get_payouts(
        user_id: Annotated[UserId, Depends(current_user)],
        month: Annotated[str | None, Query()] = None,
    ) -> PayoutReportView:
        parsed: CommissionMonth | None = parse_optional(month, CommissionMonth, "month")
        if parsed is None:
            raise ValidationFailedError("month is required (YYYY-MM).")

        return get_payout_report.operate(
            PayoutReportQuery(user_id=user_id, month=parsed)
        )

    @router.patch(
        "/v1/admin/partners/{partner_id}",
        openapi_extra=describe_json_body(UpdatePartnerRequest),
    )
    def patch_partner(
        partner_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[UpdatePartnerRequest, Depends(read_update_body)],
    ) -> PartnerAdminView:
        return update_partner.operate(
            UpdatePartnerCommand(
                user_id=user_id,
                partner_id=parse_path_identifier(partner_id, PartnerId, "Partner"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        "/v1/admin/partners/{partner_id}/codes",
        openapi_extra=describe_json_body(AddPartnerCodeRequest),
    )
    def post_partner_code(
        partner_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AddPartnerCodeRequest, Depends(read_code_body)],
    ) -> PartnerAdminView:
        return add_partner_code.operate(
            AddPartnerCodeCommand(
                user_id=user_id,
                partner_id=parse_path_identifier(partner_id, PartnerId, "Partner"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        "/v1/admin/partners/{partner_id}/payouts",
        openapi_extra=describe_json_body(MarkPayoutPaidRequest),
    )
    def post_payout(
        partner_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[MarkPayoutPaidRequest, Depends(read_payout_body)],
    ) -> PayoutReceipt:
        return mark_payout_paid.operate(
            MarkPayoutPaidCommand(
                user_id=user_id,
                partner_id=parse_path_identifier(partner_id, PartnerId, "Partner"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
