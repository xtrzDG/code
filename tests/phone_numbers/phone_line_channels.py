"""
The channel use cases over the phone world: turning the phone channel off
gives the rented number back; connecting another number is refused while
one is rented. The Telegram and Meta clients answer nothing (a phone line
never calls them).
"""

from app.clients.meta.meta_graph_client import MetaGraphClient
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.voice_platform import VoiceAgentProvisionerAdapterContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.channels.channel_settings import (
    ChannelView,
    ConnectChannelCommand,
    ConnectChannelRequest,
    DisableChannelCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.channels.connection.connect_channel_use_case import (
    ConnectChannelUseCase,
)
from app.use_cases.channels.disable_channel_use_case import DisableChannelUseCase
from app.use_cases.voice.remove_voice_agent_use_case import RemoveVoiceAgentUseCase
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.channels.channels_fakes import FakeSecretCipher, RecordingVoiceAgentRemoval
from tests.channels.recording_transport import RecordingTransport
from tests.foundation.access_support import AllowStepUp
from tests.phone_numbers.phone_world import PhoneWorld


class PhoneLineChannels:
    """Connect and disable over the phone world's storage."""

    def __init__(
        self,
        world: PhoneWorld,
        voice_agents: VoiceAgentProvisionerAdapterContract | None = None,
    ) -> None:
        """With `voice_agents`, switching off removes agents for real."""

        self.world: PhoneWorld = world
        self.voice_agent_removals: list[BusinessId] = []
        remove_voice_agent: UseCaseContract[BusinessId, None] = (
            RecordingVoiceAgentRemoval(self.voice_agent_removals)
            if voice_agents is None
            else RemoveVoiceAgentUseCase(world.assistant_version_repo, voice_agents)
        )
        telegram_client = TelegramBotClient(transport=RecordingTransport().build())
        meta_client = MetaGraphClient(transport=RecordingTransport().build())
        self.connect = ConnectChannelUseCase(
            world.authorize,
            world.channel_repo,
            FakeSecretCipher(),
            telegram_client,
            meta_client,
            world.parser,
            world.audit_log_repo,
            world.settings,
            world.clock.wall_clock,
            StorageScopeContext(),
            product_events=world.product_events,
            step_up=AllowStepUp(),
            phone_number_repo=world.phone_number_repo,
        )
        self.disable = DisableChannelUseCase(
            world.authorize,
            world.channel_repo,
            FakeSecretCipher(),
            telegram_client,
            world.audit_log_repo,
            world.clock.wall_clock,
            remove_voice_agent,
            give_back_phone_number=world.give_back,
        )

    def connect_phone(
        self, owner: UserDocument, business: BusinessDocument, phone_number: str
    ) -> ChannelView:
        return self.connect.run(
            ConnectChannelCommand(
                user_id=owner.id,
                business_id=business.id,
                channel=ChannelKind.PHONE,
                request=ConnectChannelRequest.model_validate(
                    {"phone_number": phone_number}
                ),
            )
        )

    def turn_phone_off(
        self, owner: UserDocument, business: BusinessDocument
    ) -> ChannelView:
        return self.disable.run(
            DisableChannelCommand(
                user_id=owner.id, business_id=business.id, channel=ChannelKind.PHONE
            )
        )
