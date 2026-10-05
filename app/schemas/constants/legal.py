from enum import StrEnum


class LegalDocumentKind(StrEnum):
    """
    The platform's own legal texts for business owners (docs/legal): the
    terms of service, the privacy policy and the cookie statement. The data
    processing agreement has its own versions and acceptance (DPA_*).
    """

    TERMS = "terms"
    PRIVACY = "privacy"
    COOKIES = "cookies"


class SubprocessorChangeKind(StrEnum):
    """What a change of the sub-processor list does (DPA section 8.3)."""

    ADDED = "added"
    REMOVED = "removed"


class ProcessorFlow(StrEnum):
    """
    One flow of personal data from the platform to an outside provider (a
    processor use, `app/registries/legal/processor_use_catalog.py`): the
    assistant's replies, the check of their claims, conversation summaries,
    the judge of automatic checks, the nightly quality sample of real
    conversations and the transcription of voice notes. A sub-processor
    entry lists the flows its purpose covers.
    """

    ASSISTANT_REPLIES = "assistant_replies"
    CLAIM_VERIFIER = "claim_verifier"
    CONVERSATION_SUMMARIES = "conversation_summaries"
    AUTOTEST_JUDGE = "autotest_judge"
    QUALITY_SAMPLING = "quality_sampling"
    TRANSCRIPTION = "transcription"


class ProcessorDataCategory(StrEnum):
    """
    What a processor use sends: customers' messages (free text, which may
    name people or describe their health), the business's own knowledge,
    booking details, customers' voice notes, or synthetic test
    conversations that hold no customer's data.
    """

    CUSTOMER_MESSAGES = "customer_messages"
    BUSINESS_KNOWLEDGE = "business_knowledge"
    BOOKING_DETAILS = "booking_details"
    VOICE_NOTES = "voice_notes"
    TEST_CONVERSATIONS = "test_conversations"
