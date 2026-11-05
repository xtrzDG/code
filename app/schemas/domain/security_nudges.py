"""The owner's answer to the reminder to protect customers' data (migration 1201)."""

from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.security_nudges.constrained_integers import TeamMemberCount
from app.schemas.typings.security_nudges.prefixed_id import SecurityNudgeId
from app.schemas.typings.users.prefixed_id import UserId


class SecurityNudgeDocument(BaseDocument):
    """
    One owner put the "turn on a second factor" reminder of one business
    away (`dismissed_at`), when the team had `team_size_at_dismissal`
    people. The reminder stays away until the team grows past one person
    if it was put away by someone working alone; it never comes back once
    the owner has a second factor. Stored under an id derived from the
    business and the person.
    """

    id: SecurityNudgeId
    business_id: BusinessId
    user_id: UserId
    dismissed_at: Microseconds
    team_size_at_dismissal: TeamMemberCount
