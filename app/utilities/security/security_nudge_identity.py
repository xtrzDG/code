"""
The id of an owner's answer to the second-factor reminder: one per business
and person. The namespace is fixed: stored ids depend on it.
"""

from uuid import UUID, uuid5

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.security_nudges.prefixed_id import SecurityNudgeId
from app.schemas.typings.users.prefixed_id import UserId

SECURITY_NUDGE_NAMESPACE: UUID = UUID("3f6b0d52-8e41-4c27-a9d3-5b17c2e8f094")


def security_nudge_id_for(business_id: BusinessId, user_id: UserId) -> SecurityNudgeId:
    return SecurityNudgeId(uuid5(SECURITY_NUDGE_NAMESPACE, f"{business_id}:{user_id}"))
