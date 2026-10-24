"""The language of a customer message, and what the contact remembers of it."""

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LanguageDetectorContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.language_detection import DetectedLanguage
from app.schemas.typings.conversations.strings import MessageText


def detect_turn_language(
    language_detector: LanguageDetectorContract,
    customer_text: MessageText,
    version: AssistantVersionDocument,
    conversation: ConversationDocument,
    contact: ContactDocument,
) -> DetectedLanguage:
    """
    Any language the customer writes in; a message that tells too little
    keeps the conversation's language, then the contact's, then the
    version default.
    """

    return language_detector.detect_any(
        customer_text,
        list(version.languages),
        version.default_language,
        conversation.language,
        contact.language,
    )


def remember_contact_language(
    contact_repo: ContactRepoContract,
    contact: ContactDocument,
    detected: DetectedLanguage,
    now: Microseconds,
) -> None:
    """
    The contact's language becomes the one their message was read in (and
    the first one ever known): reminders, review requests and the next
    conversation start in it.
    """

    if contact.language == detected.language:
        return

    if contact.language is not None and not detected.is_read_from_text:
        return

    contact.language = detected.language
    contact.updated_at = now
    contact_repo.save(contact)
