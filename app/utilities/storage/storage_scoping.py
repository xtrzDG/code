"""Which business an operation works for, to scope storage to it."""

from app.schemas.typings.businesses.prefixed_id import BusinessId

BUSINESS_ID_ATTRIBUTE: str = "business_id"


def find_operation_business_id(input_data: object) -> BusinessId | None:
    """
    The business named by an operation's input (its `business_id`), or None
    for platform-level operations (sign-in, webhooks resolved later, admin
    lists, jobs over every business).
    """

    business_id: object = getattr(input_data, BUSINESS_ID_ATTRIBUTE, None)
    if isinstance(business_id, BusinessId):
        return business_id

    return None
