"""
What opens the first reply of a chat conversation: the AI disclosure in
the customer's language (EU AI Act Art. 50(1)) and, in a messenger, a line
that links the business's privacy notice (its own, else the platform's
notice of its chat), since a messenger has no page footer to show it.
"""

from dataclasses import dataclass

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.utilities.conversations.assistant_texts.ai_disclosure_texts import (
    AI_DISCLOSURE,
)
from app.utilities.conversations.assistant_texts.business_name_placeholder import (
    fill_business_name,
)
from app.utilities.conversations.assistant_texts.privacy_notice_texts import (
    PRIVACY_NOTICE_LINE,
    fill_privacy_url,
)
from app.utilities.deliveries.holding_replies import derive_holding_message_id
from app.utilities.sharing.share_links import choose_privacy_url

MESSENGER_CHANNELS: frozenset[ChannelKind] = frozenset(
    {
        ChannelKind.WHATSAPP,
        ChannelKind.TELEGRAM,
        ChannelKind.INSTAGRAM,
        ChannelKind.MESSENGER,
        ChannelKind.VIBER,
    }
)


@dataclass(frozen=True)
class ReplyOpening:
    """What opens a reply (technical record): the disclosure, the notice line."""

    disclosure: MessageText | None = None
    privacy_line: MessageText | None = None


class ReplyDisclosure:
    """
    The opening of a reply: the disclosure, unless the turn's "one moment"
    already said it (that message carried it), and the privacy line of a
    messenger's first reply (the "one moment" does not carry it).
    """

    def __init__(
        self,
        message_repo: MessageRepoContract,
        localized_text_resolver: LocalizedTextResolverContract,
        business_profile_repo: BusinessProfileRepoContract | None = None,
        cabinet_base_url: CabinetBaseUrl | None = None,
    ) -> None:
        self._message_repo: MessageRepoContract = message_repo
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )
        self._business_profile_repo: BusinessProfileRepoContract | None = (
            business_profile_repo
        )
        self._cabinet_base_url: CabinetBaseUrl | None = cabinet_base_url

    def open(self, turn: PreparedTurn, text: MessageText | None) -> ReplyOpening:
        if (
            text is None
            or not turn.is_first_reply
            or turn.conversation.channel is ChannelKind.PHONE
        ):
            return ReplyOpening()

        return ReplyOpening(
            disclosure=(
                None if self._holding_spoke_first(turn) else self._disclosure(turn)
            ),
            privacy_line=self._privacy_line(turn),
        )

    def _disclosure(self, turn: PreparedTurn) -> MessageText:
        return MessageText(
            fill_business_name(
                self._localized_text_resolver.resolve(
                    AI_DISCLOSURE, turn.reply_language
                ),
                str(turn.business.name),
            )
        )

    def _privacy_line(self, turn: PreparedTurn) -> MessageText | None:
        """The notice's line in a real messenger chat; None without an address."""

        if (
            turn.conversation.channel not in MESSENGER_CHANNELS
            or turn.conversation.is_sandbox
            or self._business_profile_repo is None
        ):
            return None

        url: WebLink | None = choose_privacy_url(
            turn.business,
            self._business_profile_repo.get_by_business(turn.business.id),
            self._cabinet_base_url,
        )
        if url is None:
            return None

        return MessageText(
            fill_privacy_url(
                self._localized_text_resolver.resolve(
                    PRIVACY_NOTICE_LINE, turn.reply_language
                ),
                str(url),
            )
        )

    def _holding_spoke_first(self, turn: PreparedTurn) -> bool:
        return (
            turn.reply_message_id is not None
            and self._message_repo.get(
                turn.business.id, derive_holding_message_id(turn.reply_message_id)
            )
            is not None
        )
