"""
Derived ids of the guided launch: one milestone per business and kind, one
setup state and one current apply per business.
"""

from uuid import UUID, uuid5

from app.schemas.constants.setup import ActivationEventKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.setup.prefixed_id import (
    ActivationEventId,
    AssistantApplyId,
    SetupStateId,
)

# Fixed namespaces of the derived ids (never change them: stored ids and the
# once-only milestones depend on them).
ACTIVATION_EVENT_NAMESPACE: UUID = UUID("3b6f7a52-8c1e-4d2b-9f40-1e7c5a9d2b61")
SETUP_STATE_NAMESPACE: UUID = UUID("9d2e4c71-5a3b-4f18-8e6d-2c7b1a4f9e30")
ASSISTANT_APPLY_NAMESPACE: UUID = UUID("c4a81e3f-6b2d-4a97-b5e1-7f3d9c2a6b48")


def derive_activation_event_id(
    business_id: BusinessId,
    kind: ActivationEventKind,
) -> ActivationEventId:
    """The same milestone of the same business: the same id."""

    return ActivationEventId(
        uuid5(ACTIVATION_EVENT_NAMESPACE, f"{business_id}|{kind.value}")
    )


def derive_setup_state_id(business_id: BusinessId) -> SetupStateId:
    return SetupStateId(uuid5(SETUP_STATE_NAMESPACE, str(business_id)))


def derive_assistant_apply_id(business_id: BusinessId) -> AssistantApplyId:
    return AssistantApplyId(uuid5(ASSISTANT_APPLY_NAMESPACE, str(business_id)))
