"""Data processing agreement, audit log, customers and their data rights."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from typed_time_provider import Microseconds

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.compliance import AuditAction
from app.schemas.dto.businesses import BusinessQuery
from app.schemas.dto.compliance import (
    AcceptDpaCommand,
    AuditLogPage,
    AuditLogQuery,
    ContactDataCommand,
    ContactDataExport,
    ContactErasureResult,
    DpaDocumentQuery,
    DpaDocumentView,
    DpaStatusView,
)
from app.schemas.dto.contacts import (
    ContactDetailView,
    ContactListQuery,
    ContactPage,
    ContactQuery,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.constrained_strings import ContactSearchText
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.compliance.legal_endpoints import DPA_DOCUMENT_ROUTE
from app.utilities.localization.language_tags import parse_language_tag

type ListContactsOperator = OperatorContract[ContactListQuery, ContactPage]
type GetContactOperator = OperatorContract[ContactQuery, ContactDetailView]
type DpaDocumentOperator = OperatorContract[DpaDocumentQuery, DpaDocumentView]


def build_compliance_router(
    get_dpa_status_operator: OperatorContract[BusinessQuery, DpaStatusView],
    accept_dpa_operator: OperatorContract[AcceptDpaCommand, DpaStatusView],
    list_audit_log_operator: OperatorContract[AuditLogQuery, AuditLogPage],
    export_contact_data_operator: OperatorContract[
        ContactDataCommand,
        ContactDataExport,
    ],
    delete_contact_data_operator: OperatorContract[
        ContactDataCommand,
        ContactErasureResult,
    ],
    list_contacts_operator: ListContactsOperator,
    get_contact_operator: GetContactOperator,
    get_dpa_document_operator: DpaDocumentOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (a bearer token is needed for all but the agreement text):
        GET    /v1/businesses/{business_id}/dpa                 agreement status
        POST   /v1/businesses/{business_id}/dpa                 owner accepts (201)
        GET    /v1/legal/dpa/{version}?language=                agreement text
        GET    /v1/businesses/{business_id}/audit-log           owner: newest first
               ?limit=&cursor=&action=&entity=&actor_id=&since=&until=
        GET    /v1/businesses/{business_id}/contacts?search=&limit=&cursor=
                                                                owner: customers
        GET    /v1/businesses/{business_id}/contacts/{contact_id}
                                                                owner: one customer
        GET    /v1/businesses/{business_id}/contacts/{contact_id}/export
                                                                owner: visitor data
        DELETE /v1/businesses/{business_id}/contacts/{contact_id}
                                                                owner: erase visitor

    Lists are pages `{"items": [...], "next_cursor": ...}`. `since` and
    `until` are UTC microseconds (from inclusive, to exclusive). Reading the
    customers and one customer is audited.
    """

    router = APIRouter(tags=["compliance"])

    @router.get("/v1/businesses/{business_id}/dpa")
    def get_dpa_status(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> DpaStatusView:
        return get_dpa_status_operator.operate(
            BusinessQuery(user_id=user_id, business_id=parse_business_id(business_id))
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
                business_id=parse_business_id(business_id),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(DPA_DOCUMENT_ROUTE)
    def get_dpa_document(
        version: str,
        language: str | None = None,
    ) -> DpaDocumentView:
        return get_dpa_document_operator.operate(
            DpaDocumentQuery(
                version=parse_path_identifier(
                    version,
                    DpaDocumentVersion,
                    "Agreement version",
                ),
                language=parse_optional_language(language),
            )
        )

    @router.get("/v1/businesses/{business_id}/audit-log")
    def list_audit_log(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
        cursor: str | None = None,
        action: str | None = None,
        entity: str | None = None,
        actor_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> AuditLogPage:
        return list_audit_log_operator.operate(
            AuditLogQuery(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                page=parse_page_request(limit, cursor),
                action=parse_optional(action, AuditAction, "action"),
                entity=parse_optional(entity, AuditEntityName, "entity"),
                actor_id=parse_optional(actor_id, UserId, "actor_id"),
                since=parse_optional_moment(since, "since"),
                until=parse_optional_moment(until, "until"),
            )
        )

    @router.get("/v1/businesses/{business_id}/contacts")
    def list_contacts(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        search: str | None = None,
        limit: str | None = None,
        cursor: str | None = None,
    ) -> ContactPage:
        return list_contacts_operator.operate(
            ContactListQuery(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                search=parse_optional(
                    None if search is None else search.strip(),
                    ContactSearchText,
                    "search",
                ),
                page=parse_page_request(limit, cursor),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get("/v1/businesses/{business_id}/contacts/{contact_id}")
    def get_contact(
        request: Request,
        business_id: str,
        contact_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ContactDetailView:
        return get_contact_operator.operate(
            ContactQuery(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                contact_id=parse_path_identifier(contact_id, ContactId, "Contact"),
                client_ip_address=read_client_ip_address(request),
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


def parse_business_id(raw_business_id: str) -> BusinessId:
    return parse_path_identifier(raw_business_id, BusinessId, "Business")


def build_contact_data_command(
    request: Request,
    business_id: str,
    contact_id: str,
    user_id: UserId,
) -> ContactDataCommand:
    return ContactDataCommand(
        user_id=user_id,
        business_id=parse_business_id(business_id),
        contact_id=parse_path_identifier(contact_id, ContactId, "Contact"),
        client_ip_address=read_client_ip_address(request),
    )


def parse_optional_moment(
    raw_value: str | None,
    parameter_name: str,
) -> Microseconds | None:
    """UTC microseconds since the epoch from a query parameter."""

    if raw_value is None or raw_value == "":
        return None

    try:
        moment: int = int(raw_value)
    except ValueError as error:
        raise ValidationFailedError(
            f"{parameter_name} must be UTC microseconds since 1970."
        ) from error

    if moment < 0:
        raise ValidationFailedError(
            f"{parameter_name} must be UTC microseconds since 1970."
        )

    return Microseconds(moment)


def parse_optional_language(raw_language: str | None) -> LanguageTag | None:
    """BCP 47 tag from the query; raises UnsupportedLanguageError (422)."""

    if raw_language is None or raw_language.strip() == "":
        return None

    return parse_language_tag(raw_language)
