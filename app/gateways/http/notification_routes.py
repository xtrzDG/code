"""Cabinet Settings → Notifications: contacts, my preferences and devices, links."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.notifications.notification_settings import (
    ContactCheckCommand,
    MyNotificationSettingsView,
    NotificationCheckResult,
    NotificationContactList,
    NotificationContactsQuery,
    NotificationPreferencesRequest,
    NotificationSettingsQuery,
    PushDeviceCommand,
    PushDeviceView,
    PushSubscriptionRequest,
    SubscribePushCommand,
    UpdateNotificationPreferencesCommand,
)
from app.schemas.dto.notifications.staff_links import StaffLinkQuery, StaffLinkView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.notifications.constrained_strings import (
    NotificationContactKey,
    StaffLinkToken,
)
from app.schemas.typings.notifications.prefixed_id import PushSubscriptionId
from app.schemas.typings.users.prefixed_id import UserId

B: str = "/v1/businesses/{business_id}"

read_preferences_body = build_json_body_dependency(NotificationPreferencesRequest)
read_subscription_body = build_json_body_dependency(PushSubscriptionRequest)


def build_notification_router(
    *,
    current_user: CurrentUserDependency,
    list_contacts: OperatorContract[NotificationContactsQuery, NotificationContactList],
    check_contact: OperatorContract[ContactCheckCommand, NotificationCheckResult],
    get_settings: OperatorContract[
        NotificationSettingsQuery, MyNotificationSettingsView
    ],
    update_preferences: OperatorContract[
        UpdateNotificationPreferencesCommand, MyNotificationSettingsView
    ],
    subscribe_push: OperatorContract[SubscribePushCommand, PushDeviceView],
    unsubscribe_push: OperatorContract[PushDeviceCommand, None],
    check_device: OperatorContract[PushDeviceCommand, NotificationCheckResult],
    resolve_link: OperatorContract[StaffLinkQuery, StaffLinkView],
) -> APIRouter:
    """
    Routes (Bearer auth; owners and staff unless marked):
        GET    {B}/notification-contacts                 contacts and delivery
        POST   {B}/notification-contacts/{key}/test      owner: test one contact
        GET    {B}/notification-preferences              my events, hours, devices
        PUT    {B}/notification-preferences              my events and quiet hours
        POST   {B}/push-subscriptions                    turn this device on
        DELETE {B}/push-subscriptions/{id}               turn my device off
        POST   {B}/push-subscriptions/{id}/test          test my device
        GET    {B}/notification-links/{token}            where a link leads
    """

    router = APIRouter(tags=["notifications"], responses=standard_error_responses())

    def business(raw_id: str) -> BusinessId:
        return parse_path_identifier(raw_id, BusinessId, "Business")

    @router.get(f"{B}/notification-contacts")
    def list_notification_contacts(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> NotificationContactList:
        return list_contacts.operate(
            NotificationContactsQuery(
                user_id=user_id, business_id=business(business_id)
            )
        )

    @router.post(f"{B}/notification-contacts/{{contact_key}}/test")
    def check_notification_contact(
        request: Request,
        business_id: str,
        contact_key: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> NotificationCheckResult:
        return check_contact.operate(
            ContactCheckCommand(
                user_id=user_id,
                business_id=business(business_id),
                contact_key=parse_path_identifier(
                    contact_key, NotificationContactKey, "Notification contact"
                ),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(f"{B}/notification-preferences")
    def get_notification_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> MyNotificationSettingsView:
        return get_settings.operate(
            NotificationSettingsQuery(
                user_id=user_id, business_id=business(business_id)
            )
        )

    @router.put(
        f"{B}/notification-preferences",
        openapi_extra=describe_json_body(NotificationPreferencesRequest),
    )
    def update_notification_preferences(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[NotificationPreferencesRequest, Depends(read_preferences_body)],
    ) -> MyNotificationSettingsView:
        return update_preferences.operate(
            UpdateNotificationPreferencesCommand(
                user_id=user_id, business_id=business(business_id), request=body
            )
        )

    @router.post(
        f"{B}/push-subscriptions",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(PushSubscriptionRequest),
    )
    def subscribe_push_device(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[PushSubscriptionRequest, Depends(read_subscription_body)],
    ) -> PushDeviceView:
        return subscribe_push.operate(
            SubscribePushCommand(
                user_id=user_id, business_id=business(business_id), request=body
            )
        )

    @router.delete(
        f"{B}/push-subscriptions/{{subscription_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def unsubscribe_push_device(
        business_id: str,
        subscription_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        unsubscribe_push.operate(device(user_id, business_id, subscription_id))

    @router.post(f"{B}/push-subscriptions/{{subscription_id}}/test")
    def check_push_device(
        business_id: str,
        subscription_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> NotificationCheckResult:
        return check_device.operate(device(user_id, business_id, subscription_id))

    @router.get(f"{B}/notification-links/{{token}}")
    def resolve_notification_link(
        business_id: str,
        token: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> StaffLinkView:
        return resolve_link.operate(
            StaffLinkQuery(
                user_id=user_id,
                business_id=business(business_id),
                token=parse_path_identifier(token, StaffLinkToken, "Link"),
            )
        )

    def device(user_id: UserId, business_id: str, raw_id: str) -> PushDeviceCommand:
        return PushDeviceCommand(
            user_id=user_id,
            business_id=business(business_id),
            subscription_id=parse_path_identifier(raw_id, PushSubscriptionId, "Device"),
        )

    return router
