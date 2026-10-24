"""What a change of the phone line writes: the channel and the audit log."""

from typed_time_provider import Microseconds

from app.contracts.phone_numbers import PhoneNumberRepoContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.storage import StorageScopeContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.dto.phone_numbers.phone_line import RentPhoneNumberCommand
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.channels.phone_numbers.rented_line_channel import (
    connect_rented_line,
)

PHONE_NUMBER_ENTITY: AuditEntityName = AuditEntityName("phone_number")
CHANNEL_ENTITY: AuditEntityName = AuditEntityName("channel")


class PhoneLineRecords:
    """
    The storage a phone line change touches, built by the use cases from
    their injected contracts: the rented numbers, the phone channel, the
    published version's voice agent and the audit log.
    """

    def __init__(
        self,
        phone_number_repo: PhoneNumberRepoContract,
        channel_repo: ChannelRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        audit_log_repo: AuditLogRepoContract,
        storage_scope: StorageScopeContract,
        app_settings: AppSettings,
    ) -> None:
        self.phone_number_repo: PhoneNumberRepoContract = phone_number_repo
        self.channel_repo: ChannelRepoContract = channel_repo
        self.assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self.audit_log_repo: AuditLogRepoContract = audit_log_repo
        self.storage_scope: StorageScopeContract = storage_scope
        self.app_settings: AppSettings = app_settings

    def record_rental(
        self,
        business_id: BusinessId,
        number: PhoneNumberDocument,
        command: RentPhoneNumberCommand,
        now: Microseconds,
    ) -> ChannelDocument:
        """Connect the phone channel with the number; audit both."""

        channel, is_new = connect_rented_line(
            self.channel_repo, business_id, number.phone_number, now
        )
        for entity, reference, action in (
            (PHONE_NUMBER_ENTITY, str(number.id), AuditAction.CREATE),
            (
                CHANNEL_ENTITY,
                str(channel.id),
                AuditAction.CREATE if is_new else AuditAction.UPDATE,
            ),
        ):
            self.audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business_id,
                    actor_id=command.user_id,
                    action=action,
                    entity=entity,
                    entity_id=AuditEntityReference(reference),
                    ip_address=command.client_ip_address,
                    created_at=now,
                    updated_at=now,
                )
            )

        return channel
