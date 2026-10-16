"""Derived ids of customer memory: one assistant settings document per business."""

from uuid import UUID, uuid5

from app.schemas.typings.assistants.prefixed_id import AssistantSettingsId
from app.schemas.typings.businesses.prefixed_id import BusinessId

# Fixed namespace of the derived id (never change it: stored ids depend on it).
ASSISTANT_SETTINGS_NAMESPACE: UUID = UUID("3c9e7a51-6d24-4b8f-a0e3-58f1c2d9b746")


def derive_assistant_settings_id(business_id: BusinessId) -> AssistantSettingsId:
    return AssistantSettingsId(uuid5(ASSISTANT_SETTINGS_NAMESPACE, str(business_id)))
