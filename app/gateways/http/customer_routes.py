"""Customers: the team's card on a customer, its standing, the team's settings."""

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
from app.schemas.dto.customers.customer_card import (
    ChangeCustomerBlockingCommand,
    ChangeCustomerCardCommand,
    ContactStandingQuery,
    ContactStandingView,
    CustomerBlockingRequest,
    CustomerCardRequest,
    CustomerCardView,
)
from app.schemas.dto.customers.customer_settings import (
    CustomerSettingsQuery,
    CustomerSettingsRequest,
    CustomerSettingsView,
    UpdateCustomerSettingsCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.users.prefixed_id import UserId

B: str = "/v1/businesses/{business_id}"
C: str = f"{B}/contacts/{{contact_id}}"

read_card_body = build_json_body_dependency(CustomerCardRequest)
read_blocking_body = build_json_body_dependency(CustomerBlockingRequest)
read_settings_body = build_json_body_dependency(CustomerSettingsRequest)


def build_customer_router(
    *,
    current_user: CurrentUserDependency,
    change_card: OperatorContract[ChangeCustomerCardCommand, CustomerCardView],
    change_blocking: OperatorContract[ChangeCustomerBlockingCommand, CustomerCardView],
    get_standing: OperatorContract[ContactStandingQuery, ContactStandingView],
    get_settings: OperatorContract[CustomerSettingsQuery, CustomerSettingsView],
    update_settings: OperatorContract[
        UpdateCustomerSettingsCommand, CustomerSettingsView
    ],
) -> APIRouter:
    """
    Routes (Bearer auth):
        PATCH {C}/card          tags to add or take off, the VIP flag (team)
        PUT   {C}/blocking      block or unblock the customer (owners)
        GET   {C}/standing      "Regular customer · 4 visits" (team)
        GET   {B}/customer-settings   staff see phones? the business's tags
        PUT   {B}/customer-settings   let staff see phones (owners)
    with C = {B}/contacts/{contact_id}.
    """

    router = APIRouter(tags=["customers"], responses=standard_error_responses())

    def business(raw_id: str) -> BusinessId:
        return parse_path_identifier(raw_id, BusinessId, "Business")

    def contact(raw_id: str) -> ContactId:
        return parse_path_identifier(raw_id, ContactId, "Contact")

    @router.patch(f"{C}/card", openapi_extra=describe_json_body(CustomerCardRequest))
    def change_customer_card(
        business_id: str,
        contact_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CustomerCardRequest, Depends(read_card_body)],
    ) -> CustomerCardView:
        return change_card.operate(
            ChangeCustomerCardCommand(
                user_id=user_id,
                business_id=business(business_id),
                contact_id=contact(contact_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.put(
        f"{C}/blocking", openapi_extra=describe_json_body(CustomerBlockingRequest)
    )
    def change_customer_blocking(
        business_id: str,
        contact_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CustomerBlockingRequest, Depends(read_blocking_body)],
    ) -> CustomerCardView:
        return change_blocking.operate(
            ChangeCustomerBlockingCommand(
                user_id=user_id,
                business_id=business(business_id),
                contact_id=contact(contact_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(f"{C}/standing")
    def get_contact_standing(
        business_id: str,
        contact_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ContactStandingView:
        return get_standing.operate(
            ContactStandingQuery(
                user_id=user_id,
                business_id=business(business_id),
                contact_id=contact(contact_id),
            )
        )

    @router.get(f"{B}/customer-settings")
    def get_customer_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> CustomerSettingsView:
        return get_settings.operate(
            CustomerSettingsQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.put(
        f"{B}/customer-settings",
        openapi_extra=describe_json_body(CustomerSettingsRequest),
    )
    def update_customer_settings(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CustomerSettingsRequest, Depends(read_settings_body)],
    ) -> CustomerSettingsView:
        return update_settings.operate(
            UpdateCustomerSettingsCommand(
                user_id=user_id,
                business_id=business(business_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
