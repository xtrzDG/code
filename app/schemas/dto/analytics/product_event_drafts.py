from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.analytics import ProductEventName, ProductEventSource
from app.schemas.domain.product_events import ProductEventProperties
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId


class ProductEventDraft(ImmutableDTO):
    """
    A product event as a use case reports it: the step, who and which
    business, its typed facts and, when it happened earlier than now (a
    milestone noticed later), when. The facilitator gives it its id (derived
    for a once-only step) and the time.
    """

    name: ProductEventName
    user_id: UserId | None = None
    business_id: BusinessId | None = None
    properties: ProductEventProperties = Field(default_factory=ProductEventProperties)
    occurred_at: Microseconds | None = None
    source: ProductEventSource = ProductEventSource.SERVER
