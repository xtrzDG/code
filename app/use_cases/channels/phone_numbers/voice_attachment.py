"""
Keep a rented number answering with the business's voice agent, and its
call fallback pointing at the platform.
"""

import logging

from typed_time_provider import Microseconds

from app.contracts.phone_numbers import (
    PhoneNumberProvisionerAdapterContract,
    PhoneNumberRepoContract,
)
from app.schemas.constants.phone_numbers import PhoneNumberStatus
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.dto.phone_numbers.provisioning import VoicePlatformImport
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.telephony.constrained_strings import (
    PhoneNumberLabel,
    VoiceFallbackUrl,
)
from app.schemas.typings.telephony.strings import VoicePlatformPhoneNumberId

logger: logging.Logger = logging.getLogger(__name__)


def attach_to_agent(
    provisioner: PhoneNumberProvisionerAdapterContract,
    phone_number_repo: PhoneNumberRepoContract,
    number: PhoneNumberDocument,
    agent_id: VoiceAgentId | None,
    label: PhoneNumberLabel,
    now: Microseconds,
) -> PhoneNumberDocument:
    """
    Import the number into the voice platform when it is not there yet
    (assigned to `agent_id`), or assign `agent_id` when another agent (or
    none) answers it. A refusal is logged and left for the maintenance job
    to try again; the stored number says how far it got.
    """

    if number.status is not PhoneNumberStatus.ACTIVE:
        return number

    try:
        if number.voice_platform_number_id is None:
            voice_id: VoicePlatformPhoneNumberId = provisioner.import_number(
                VoicePlatformImport(
                    phone_number=number.phone_number, label=label, agent_id=agent_id
                )
            )
        elif number.attached_agent_id != agent_id:
            voice_id = number.voice_platform_number_id
            provisioner.assign_agent(voice_id, agent_id)
        else:
            return number
    except ExternalServiceError as error:
        logger.warning(
            "Rented number %s of business %s is not attached to its voice "
            "agent yet: %s",
            number.id,
            number.business_id,
            error,
        )
        return number

    def record(stored: PhoneNumberDocument) -> PhoneNumberDocument | None:
        if stored.status is not PhoneNumberStatus.ACTIVE:
            return None

        return stored.model_copy(
            update={
                "voice_platform_number_id": voice_id,
                "attached_agent_id": agent_id,
                "updated_at": now,
            }
        )

    return phone_number_repo.modify(number.business_id, number.id, record) or number


def needs_fallback(number: PhoneNumberDocument, url: VoiceFallbackUrl | None) -> bool:
    """
    Whether an active, imported number's call fallback is not (or no
    longer) the platform's address `url`.
    """

    return (
        url is not None
        and number.status is PhoneNumberStatus.ACTIVE
        and number.voice_platform_number_id is not None
        and number.voice_fallback_url != url
    )


def route_to_fallback(
    provisioner: PhoneNumberProvisionerAdapterContract,
    phone_number_repo: PhoneNumberRepoContract,
    number: PhoneNumberDocument,
    now: Microseconds,
) -> PhoneNumberDocument:
    """
    Point the carrier's call fallback of an imported number at the
    platform, so a call the voice platform cannot take is put through to
    the staff mobile; set once the voice platform has the number (its
    import sets the number's voice webhook) and again when the address
    changes. A refusal is logged and left for the maintenance job.
    """

    url: VoiceFallbackUrl | None = provisioner.voice_fallback_url_of(number.business_id)
    if url is None or not needs_fallback(number, url):
        return number

    try:
        provisioner.route_voice_fallback(number.provider_number_id, url)
    except ExternalServiceError as error:
        logger.warning(
            "Rented number %s of business %s has no call fallback yet: %s",
            number.id,
            number.business_id,
            error,
        )
        return number

    def record(stored: PhoneNumberDocument) -> PhoneNumberDocument | None:
        if stored.status is not PhoneNumberStatus.ACTIVE:
            return None

        return stored.model_copy(update={"voice_fallback_url": url, "updated_at": now})

    return phone_number_repo.modify(number.business_id, number.id, record) or number
