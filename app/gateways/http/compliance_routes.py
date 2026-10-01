"""Data processing agreement, audit log and visitors' data rights."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.businesses import BusinessQuery
from app.schemas.dto.compliance import (
    AcceptDpaCommand,
    AuditLogEntryView,
    AuditLogQuery,
    ContactDataCommand,
    ContactDataExport,
    ContactErasureResult,
    DpaStatusView,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditLogPageSize
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.users.prefixed_id import UserId


def build_compliance_router(
    get_dpa_status_operator: OperatorContract[BusinessQuery, DpaStatusView],
    accept_dpa_operator: OperatorContract[AcceptDpaCommand, DpaStatusView],
    list_audit_log_operator: OperatorContract[AuditLogQuery, list[AuditLogEntryView]],
    export_contact_data_operator: OperatorContract[
        ContactDataCommand,
        ContactDataExport,
    ],
    delete_contact_data_operator: OperatorContract[
        ContactDataCommand,
        ContactErasureResult,
    ],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (all require a bearer token):
        GET    /v1/businesses/{business_id}/dpa                 agreement status
        POST   /v1/businesses/{business_id}/dpa                 owner accepts (201)
        GET    /v1/businesses/{business_id}/audit-log?limit=N   owner: newest first
        GET    /v1/businesses/{business_id}/contacts/{contact_id}/export
                                                                owner: visitor data
        DELETE /v1/businesses/{business_id}/contacts/{contact_id}
                                                                owner: erase visitor
    """

    router = APIRouter(tags=["compliance"])

    @router.get("/v1/businesses/{business_id}/dpa")
    def get_dpa_status(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> DpaStatusView:
        return get_dpa_status_operator.operate(
            BusinessQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/dpa",
        status_code=status.HTTP_201_CREATED,
    )
    def accept_dpa(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> DpaStatusView:
        return accept_dpa_operator.operate(
            AcceptDpaCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get("/v1/businesses/{business_id}/audit-log")
    def list_audit_log(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
    ) -> list[AuditLogEntryView]:
        parsed_business_id: BusinessId = parse_path_identifier(
            business_id,
            BusinessId,
            "Business",
        )
        if limit is None:
            return list_audit_log_operator.operate(
                AuditLogQuery(user_id=user_id, business_id=parsed_business_id)
            )

        return list_audit_log_operator.operate(
            AuditLogQuery(
                user_id=user_id,
                business_id=parsed_business_id,
                limit=parse_page_size(limit),
            )
        )

    @router.get("/v1/businesses/{business_id}/contacts/{contact_id}/export")
    def export_contact_data(
        request: Request,
        business_id: str,
        contact_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ContactDataExport:
        return export_contact_data_operator.operate(
            build_contact_data_command(request, business_id, contact_id, user_id)
        )

    @router.delete("/v1/businesses/{business_id}/contacts/{contact_id}")
    def delete_contact_data(
        request: Request,
        business_id: str,
        contact_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ContactErasureResult:
        return delete_contact_data_operator.operate(
            build_contact_data_command(request, business_id, contact_id, user_id)
        )

    return router


def build_contact_data_command(
    request: Request,
    business_id: str,
    contact_id: str,
    user_id: UserId,
) -> ContactDataCommand:
    return ContactDataCommand(
        user_id=user_id,
        business_id=parse_path_identifier(business_id, BusinessId, "Business"),
        contact_id=parse_path_identifier(contact_id, ContactId, "Contact"),
        client_ip_address=read_client_ip_address(request),
    )


def parse_page_size(raw_limit: str) -> AuditLogPageSize:
    try:
        return AuditLogPageSize(int(raw_limit))
    except ValueError as error:
        raise ValidationFailedError(
            f"limit must be a whole number from {AuditLogPageSize.ge} "
            f"to {AuditLogPageSize.le}."
        ) from error
