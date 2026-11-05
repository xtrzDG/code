from app.contracts.repositories.notification_repositories import (
    StaffDeliveryStateRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.staff_deliveries import StaffDeliveryStateDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.notifications.notification_settings import (
    NotificationContactList,
    NotificationContactsQuery,
)
from app.schemas.typings.notifications.prefixed_id import StaffDeliveryStateId
from app.use_cases.notifications.notification_views import (
    contact_view,
    delivery_state_id_of,
)


class ListNotificationContactsUseCase(
    UseCaseContract[NotificationContactsQuery, NotificationContactList]
):
    """
    The staff contacts of a business for Settings → Notifications (owners
    and staff): each with its preferences, whether this server can deliver
    by its channel, and how its latest notification went.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        staff_delivery_state_repo: StaffDeliveryStateRepoContract,
        app_settings: AppSettings,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._staff_delivery_state_repo: StaffDeliveryStateRepoContract = (
            staff_delivery_state_repo
        )
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: NotificationContactsQuery) -> NotificationContactList:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        states: dict[StaffDeliveryStateId, StaffDeliveryStateDocument] = {
            state.id: state
            for state in self._staff_delivery_state_repo.list_by_business(business.id)
        }
        return NotificationContactList(
            business_id=business.id,
            items=[
                contact_view(
                    business,
                    contact,
                    states.get(delivery_state_id_of(business, contact)),
                    self._app_settings,
                )
                for contact in business.manager_contacts
            ],
        )
