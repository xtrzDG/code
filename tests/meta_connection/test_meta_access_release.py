"""
Switching a Meta channel off gives the platform app's access back at Meta
before the token is erased: the page or the business's own WhatsApp
account is unsubscribed (a page another channel of the business still
uses keeps its subscription), and a refusal never stops the switch-off.
"""

from app.contracts.channel_clients import ProviderToken
from app.contracts.channel_deprovisioning import MetaSubscriptionClientContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.dto.channels.channel_settings import DisableChannelCommand
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.channels.disable_channel_use_case import DisableChannelUseCase
from app.use_cases.channels.meta_connection.meta_access_release import (
    MetaAccessRelease,
)
from tests.channels.channels_fakes import RecordingVoiceAgentRemoval
from tests.channels.testbed import ChannelsTestbed

PAGE_TOKEN: str = "page-token-of-the-business"  # gitleaks:allow
BUSINESS_TOKEN: str = "whatsapp-token-of-the-business"  # gitleaks:allow


class RecordingSubscriptions(MetaSubscriptionClientContract):
    def __init__(self, fails: bool = False) -> None:
        self.fails: bool = fails
        self.pages: list[str] = []
        self.accounts: list[tuple[str, str]] = []

    def unsubscribe_page(self, page_token: ProviderToken) -> None:
        if self.fails:
            raise ExternalServiceError("Meta is not reachable.")
        self.pages.append(str(page_token))

    def unsubscribe_whatsapp_business_account(
        self,
        access_token: ProviderToken,
        business_account_id: WhatsAppBusinessAccountId,
    ) -> None:
        self.accounts.append((str(access_token), str(business_account_id)))


def disable(
    testbed: ChannelsTestbed,
    owner_id: UserId,
    business_id: BusinessId,
    kind: ChannelKind,
    subscriptions: RecordingSubscriptions,
) -> None:
    use_case = DisableChannelUseCase(
        testbed.authorize_business_access,
        testbed.channel_repo,
        testbed.secret_cipher,
        testbed.telegram_client,
        testbed.audit_log_repo,
        testbed.wall_clock,
        RecordingVoiceAgentRemoval(testbed.voice_agent_removals),
        meta_access=MetaAccessRelease(testbed.secret_cipher, subscriptions),
    )
    use_case.run(
        DisableChannelCommand(
            user_id=owner_id,
            business_id=business_id,
            channel=kind,
        )
    )


def test_switching_messenger_off_unsubscribes_the_page_and_erases_the_token() -> None:
    testbed = ChannelsTestbed()
    owner_id = UserId()
    business = testbed.add_business(owner_id)
    channel = testbed.add_channel(
        business.id, ChannelKind.MESSENGER, "1029", PAGE_TOKEN
    )
    subscriptions = RecordingSubscriptions()

    disable(testbed, owner_id, business.id, ChannelKind.MESSENGER, subscriptions)

    assert subscriptions.pages == [PAGE_TOKEN]
    stored = testbed.channel_repo.get(channel.id)
    assert stored is not None
    assert stored.status is ChannelStatus.DISABLED
    assert stored.encrypted_secret is None


def test_a_page_the_business_still_uses_keeps_its_subscription() -> None:
    testbed = ChannelsTestbed()
    owner_id = UserId()
    business = testbed.add_business(owner_id)
    testbed.add_channel(business.id, ChannelKind.MESSENGER, "1029", PAGE_TOKEN)
    testbed.add_channel(business.id, ChannelKind.INSTAGRAM, "1784", PAGE_TOKEN)
    subscriptions = RecordingSubscriptions()

    disable(testbed, owner_id, business.id, ChannelKind.MESSENGER, subscriptions)
    assert subscriptions.pages == []

    disable(testbed, owner_id, business.id, ChannelKind.INSTAGRAM, subscriptions)
    assert subscriptions.pages == [PAGE_TOKEN]


def test_whatsapp_of_embedded_signup_unsubscribes_its_own_account_only() -> None:
    testbed = ChannelsTestbed()
    owner_id = UserId()
    business = testbed.add_business(owner_id)
    channel = testbed.add_channel(
        business.id, ChannelKind.WHATSAPP, "5511", BUSINESS_TOKEN
    )
    channel.whatsapp_business_account_id = WhatsAppBusinessAccountId("88123")
    testbed.channel_repo.save(channel)
    subscriptions = RecordingSubscriptions()

    disable(testbed, owner_id, business.id, ChannelKind.WHATSAPP, subscriptions)

    assert subscriptions.accounts == [(BUSINESS_TOKEN, "88123")]

    other = ChannelsTestbed()
    other_owner = UserId()
    shared = other.add_business(other_owner)
    other.add_channel(shared.id, ChannelKind.WHATSAPP, "5512", None)
    on_platform_account = RecordingSubscriptions()
    disable(other, other_owner, shared.id, ChannelKind.WHATSAPP, on_platform_account)
    assert on_platform_account.accounts == []


def test_an_unreachable_meta_never_stops_the_switch_off() -> None:
    testbed = ChannelsTestbed()
    owner_id = UserId()
    business = testbed.add_business(owner_id)
    channel = testbed.add_channel(
        business.id, ChannelKind.MESSENGER, "1029", PAGE_TOKEN
    )

    disable(
        testbed,
        owner_id,
        business.id,
        ChannelKind.MESSENGER,
        RecordingSubscriptions(True),
    )

    stored = testbed.channel_repo.get(channel.id)
    assert stored is not None
    assert stored.status is ChannelStatus.DISABLED
    assert stored.encrypted_secret is None
