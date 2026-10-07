"""
Where a demo business's customers came from and what they asked about:
sources on its conversations, as links, QR codes, ads and the phone line
would have tagged them, and the topics a night's grouping would store
(grouped by the rehearsal, as with LLM_PROVIDER=scripted).
"""

from collections.abc import Sequence
from itertools import cycle

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversation_topics import (
    ConversationTopicsDocument,
    TopicLanguageGroup,
)
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag
from app.utilities.llm_rehearsal.rehearsal_topics import rehearse_topics
from app.utilities.sharing.acquisition_sources import called_number_source
from app.utilities.value.topic_answers import read_grouped_topics
from app.utilities.value.topic_batches import (
    FirstMessage,
    language_batches,
    to_group,
)
from app.utilities.value.topic_grouping import build_topic_request_text
from app.utilities.value.topic_labels import label_languages
from app.utilities.value.value_keys import conversation_topics_id_of

# The tags each channel's conversations take in turn (None: no tag): the
# places of the cabinet's share card, and a click-to-chat ad.
SOURCE_CYCLES: dict[ChannelKind, tuple[str | None, ...]] = {
    ChannelKind.WHATSAPP: ("table", None, "google", "table", None),
    ChannelKind.TELEGRAM: ("flyer", None),
    ChannelKind.INSTAGRAM: ("instagram", "ad-120208"),
    ChannelKind.MESSENGER: ("ad-120208", None),
    ChannelKind.WEB_CHAT: ("website", None, "table"),
}
TOPICS_WINDOW_MICROSECONDS: int = 30 * 24 * 60 * 60 * 1_000_000


def tag_demo_sources(
    conversations: Sequence[ConversationDocument],
    calls: Sequence[CallDocument],
) -> None:
    """Tags in creation order per channel; a call's conversation, its line."""

    lines: dict[ConversationId, AcquisitionSourceTag] = {
        call.conversation_id: source
        for call in calls
        if call.conversation_id is not None
        and (source := called_number_source(call.to_phone_number)) is not None
    }
    turns = {channel: cycle(tags) for channel, tags in SOURCE_CYCLES.items()}
    for conversation in sorted(conversations, key=lambda item: int(item.created_at)):
        if conversation.is_sandbox:
            continue

        if conversation.id in lines:
            conversation.acquisition_source = lines[conversation.id]
        elif conversation.channel in turns:
            tag: str | None = next(turns[conversation.channel])
            conversation.acquisition_source = (
                None if tag is None else AcquisitionSourceTag(tag)
            )


def build_demo_topics(
    business: BusinessDocument,
    conversations: Sequence[ConversationDocument],
    messages: Sequence[MessageDocument],
    questions: Sequence[UnansweredQuestionDocument],
    now: Microseconds,
) -> ConversationTopicsDocument:
    """The topics of the last 30 days, as the nightly job stores them."""

    start: int = int(now) - TOPICS_WINDOW_MICROSECONDS
    first_texts: dict[ConversationId, str] = {}
    for message in sorted(messages, key=lambda item: int(item.created_at)):
        if message.author is MessageAuthor.CUSTOMER and str(message.text).strip():
            first_texts.setdefault(message.conversation_id, str(message.text))

    firsts: list[FirstMessage] = [
        FirstMessage(conversation.language, first_texts[conversation.id])
        for conversation in sorted(conversations, key=lambda item: int(item.created_at))
        if not conversation.is_sandbox
        and int(conversation.created_at) >= start
        and conversation.id in first_texts
    ]
    groups: list[TopicLanguageGroup] = []
    languages: list[str] = label_languages(business.owner_language)
    for batch in language_batches(
        firsts, [question for question in questions if not question.is_sandbox]
    ):
        answer: str = rehearse_topics(
            build_topic_request_text(
                languages,
                str(business.name),
                [],
                batch.first_messages,
                batch.open_questions,
            )
        )
        topics = read_grouped_topics(
            answer, len(batch.first_messages), len(batch.open_questions), languages
        )
        groups.append(to_group(batch, topics or [], business.owner_language))

    return ConversationTopicsDocument(
        id=conversation_topics_id_of(business.id),
        business_id=business.id,
        label_language=business.owner_language,
        window_from=Microseconds(start),
        window_to=now,
        groups=groups,
        created_at=now,
        updated_at=now,
    )
