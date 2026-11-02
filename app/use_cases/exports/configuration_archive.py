"""
The business's configuration in a full export (Data Act art. 26: switching
to another provider takes the setup along, not only the records): what
the owner told the setup (business_profile.json), every version of the
assistant with its instructions, tools, languages and facts
(assistant_versions.json), the call settings and the privacy settings,
the connected channels without their credentials (channels.json: the
encrypted token and the WhatsApp numbers' PINs never leave), and the
consent ledger (consent_records.json), each a JSON array like every
collection of the archive.
"""

from dataclasses import dataclass

from app.contracts.repositories.business_document_pages import (
    BusinessDocumentPagesContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.call_follow_up_repositories import (
    CallSettingsRepoContract,
)
from app.contracts.repositories.consent_repositories import ConsentRecordRepoContract
from app.contracts.repositories.retention_repositories import (
    BusinessPrivacySettingsRepoContract,
)
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.use_cases.exports.archive_pages import DocumentPages, single_page
from app.use_cases.shared.document_pages import pages_in_write_order


def without_credentials(channel: ChannelDocument) -> ChannelDocument:
    """The channel as exported: its credentials and PINs left out."""

    return channel.model_copy(
        update={"encrypted_secret": None, "whatsapp_registration_pins": []}
    )


@dataclass(frozen=True)
class ConfigurationArchive:
    profile_repo: BusinessProfileRepoContract
    # Every version, a page at a time (each holds a whole instruction).
    assistant_version_repo: BusinessDocumentPagesContract[AssistantVersionDocument]
    call_settings_repo: CallSettingsRepoContract
    privacy_settings_repo: BusinessPrivacySettingsRepoContract
    channel_repo: ChannelRepoContract
    consent_record_repo: ConsentRecordRepoContract

    def pages(self, business: BusinessDocument) -> dict[str, DocumentPages]:
        """Each configuration file's documents (none: an empty array)."""

        business_id = business.id
        profile: BusinessProfileDocument | None = self.profile_repo.get_by_business(
            business_id
        )
        call_settings: CallSettingsDocument | None = (
            self.call_settings_repo.get_by_business(business_id)
        )
        return {
            "business_profile": single_page([] if profile is None else [profile]),
            "assistant_versions": pages_in_write_order(
                self.assistant_version_repo, business_id, lambda item: str(item.id)
            ),
            "call_settings": single_page(
                [] if call_settings is None else [call_settings]
            ),
            "privacy_settings": single_page(
                [self.privacy_settings_repo.get_or_default(business)]
            ),
            "channels": single_page(
                [
                    without_credentials(channel)
                    for channel in self.channel_repo.list_by_business(business_id)
                ]
            ),
            "consent_records": pages_in_write_order(
                self.consent_record_repo, business_id, lambda entry: str(entry.id)
            ),
        }
