"""Fakes of the accounts slice that record what the use cases asked them to do.

OTP deliveries, voice agent removals, assistant resumptions and recording
deletions are kept so tests can check them (and make some of them fail).
"""

from dataclasses import dataclass

from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingLocation,
    RecordingPart,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode


class RecordingVoiceAgentRemoval:
    """Records the businesses whose voice agent was switched off."""

    def __init__(self) -> None:
        self.business_ids: list[BusinessId] = []

    def run(self, input_data: BusinessId) -> None:
        self.business_ids.append(input_data)


class RecordingAssistantResumption:
    """Resumes a paused business the way re-activation would, and records it."""

    def __init__(self) -> None:
        self.business_ids: list[BusinessId] = []

    def run(self, input_data: BusinessDocument) -> None:
        self.business_ids.append(input_data.id)
        input_data.status = BusinessStatus.LIVE


@dataclass(frozen=True)
class DeliveredOtp:
    delivery_channel: OtpDeliveryChannel
    phone_number: E164PhoneNumber | None
    email: EmailAddress | None
    code: OtpCode
    language_tag: LanguageTag


class RecordingOtpDelivery(OtpDeliveryFacilitatorContract):
    """
    Keeps every delivered code so tests can type it back. Tests narrow the
    configured channels and make single channels (or all) fail.
    """

    def __init__(self) -> None:
        self.deliveries: list[DeliveredOtp] = []
        self.attempted_channels: list[OtpDeliveryChannel] = []
        self.is_failing: bool = False
        self.failing_channels: set[OtpDeliveryChannel] = set()
        self.channels: frozenset[OtpDeliveryChannel] = frozenset(OtpDeliveryChannel)

    def available_channels(self) -> frozenset[OtpDeliveryChannel]:
        return self.channels

    def deliver(
        self,
        delivery_channel: OtpDeliveryChannel,
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        code: OtpCode,
        language_tag: LanguageTag,
    ) -> None:
        self.attempted_channels.append(delivery_channel)
        if self.is_failing or delivery_channel in self.failing_channels:
            raise ExternalServiceError(f"{delivery_channel.value} provider is down.")

        self.deliveries.append(
            DeliveredOtp(
                delivery_channel=delivery_channel,
                phone_number=phone_number,
                email=email,
                code=code,
                language_tag=language_tag,
            )
        )

    def last_code(self) -> OtpCode:
        return self.deliveries[-1].code


class InMemoryRecordingStorage(RecordingStorageAdapterContract):
    def __init__(self) -> None:
        self.deleted_paths: list[RecordingStoragePath] = []
        self.is_failing: bool = False

    def read(
        self,
        location: RecordingLocation,
        wanted: RecordingByteRange | None = None,
    ) -> RecordingPart | None:
        del location, wanted
        return None

    def store(self, location: RecordingLocation, audio: RecordingAudio) -> None:
        del location, audio

    def delete(self, location: RecordingLocation) -> None:
        if self.is_failing:
            raise ExternalServiceError("Recording storage is unavailable.")

        self.deleted_paths.append(location.path)
