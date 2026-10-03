"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class NotificationPreferencesId(BasePrefixedTypedId):
    """
    Identifier of one user's notification preferences in one business.

    Derived (UUID v5) from the business and the user, so a user has one
    preferences document per business.
    """

    prefix = "notification_preferences"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class PushSubscriptionId(BasePrefixedTypedId):
    """
    Identifier of one browser (device) that receives Web Push
    notifications of a business for a user.

    Derived (UUID v5) from the business, the user and the push endpoint, so
    subscribing the same browser again keeps one subscription.
    """

    prefix = "push_subscription"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class StaffDeliveryStateId(BasePrefixedTypedId):
    """
    Identifier of the delivery state of one staff contact (its last
    notification and when one last arrived).

    Derived (UUID v5) from the business and the contact's recipient key, so
    the state is found from the contact without storing its address twice.
    """

    prefix = "staff_delivery"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
