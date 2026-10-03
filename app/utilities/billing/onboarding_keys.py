"""The derived id of a business's done-for-you setup request (one per business)."""

from uuid import UUID, uuid5

from app.schemas.typings.billing.prefixed_id import OnboardingRequestId
from app.schemas.typings.businesses.prefixed_id import BusinessId

# Fixed namespace of the derived ids (never change it: stored ids depend on it).
ONBOARDING_REQUEST_NAMESPACE: UUID = UUID("a7c3e9d1-4b58-4f2a-9e16-8d0b5c7f2e43")


def derive_onboarding_request_id(business_id: BusinessId) -> OnboardingRequestId:
    return OnboardingRequestId(uuid5(ONBOARDING_REQUEST_NAMESPACE, str(business_id)))
