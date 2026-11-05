from typing import Self

from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field, model_validator

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.booleans import IsVipOnlySegment
from app.schemas.typings.contacts.constrained_integers import (
    SegmentBookingCount,
    SegmentInactivityDays,
)
from app.schemas.typings.contacts.constrained_strings import CustomerTag, SegmentName
from app.schemas.typings.contacts.prefixed_id import CustomerSegmentId
from app.schemas.typings.users.prefixed_id import UserId


class SegmentRules(PersistentDocument):
    """
    Who belongs to a segment; every rule given must hold, an empty set of
    rules holds for every customer:

    - `tag`: the customer carries this tag;
    - `last_visit_days_ago`: their latest visit (a booking that started and
      was not cancelled, missed or left unconfirmed) was more than this many
      days ago; customers who never visited are left out;
    - `min_bookings` / `max_bookings`: how many bookings they made (any
      status, test chats left out), inclusive;
    - `vip_only`: only customers marked VIP.

    Blocked and erased customers never belong to a segment.
    """

    tag: CustomerTag | None = None
    last_visit_days_ago: SegmentInactivityDays | None = None
    min_bookings: SegmentBookingCount | None = None
    max_bookings: SegmentBookingCount | None = None
    vip_only: IsVipOnlySegment = False

    @model_validator(mode="after")
    def bounds_in_order(self) -> Self:
        if (
            self.min_bookings is not None
            and self.max_bookings is not None
            and int(self.min_bookings) > int(self.max_bookings)
        ):
            raise ValueError("min_bookings must not exceed max_bookings.")

        return self


class CustomerSegmentDocument(BaseDocument):
    """
    A group of customers the owner saved by its rules (Customers →
    Segments), to look at, export as CSV or pick as the audience of a
    campaign. Members are computed from the rules whenever they are read,
    so a segment is never stale.
    """

    id: CustomerSegmentId = Field(default_factory=CustomerSegmentId)
    business_id: BusinessId
    name: SegmentName
    rules: SegmentRules = Field(default_factory=SegmentRules)
    created_by: UserId
