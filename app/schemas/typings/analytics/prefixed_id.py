"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class ProductEventId(BasePrefixedTypedId):
    """
    Identifier of one product event.

    A step that happens once per subject (signing up, a business created,
    going live, the first booking, the trial) has an id derived (UUID v5)
    from the subject, so it is stored once however often it is recorded,
    also by the daily reconciliation; a repeatable step (a sign-in, a plan
    change) gets a random one (UUID v4).
    """

    prefix = "product_event"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


class WebVitalSampleId(BasePrefixedTypedId):
    """Identifier of one Web Vital measurement a cabinet page reported."""

    prefix = "web_vital_sample"


# Keep abc order for all non example types, if possible.
