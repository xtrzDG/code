from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.notifications.prefixed_id import StaffDeliveryStateId


class StaffDeliveryStateDocument(BaseDocument):
    """
    How notifications to one staff contact went: the state of the latest
    one (sending, delivered, failed with its reason) and when one last
    arrived. The id derives from the contact's channel and address, which
    are not stored here: a removed contact leaves no address behind.
    """

    id: StaffDeliveryStateId
    business_id: BusinessId
    status: OutboundMessageStatus
    last_error: DeliveryErrorText | None = None
    attempted_at: Microseconds
    delivered_at: Microseconds | None = None
