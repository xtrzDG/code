"""An activation nudge on its way to a business's owners."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.nudges import NudgeCode, NudgeTopic
from app.schemas.typings.businesses.prefixed_id import BusinessId


class NudgeMessage(ImmutableDTO):
    """One due nudge of a business and what it asks the owners to do."""

    business_id: BusinessId
    code: NudgeCode
    topic: NudgeTopic
