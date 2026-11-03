from enum import StrEnum


class LegalDocumentKind(StrEnum):
    """
    The platform's own public texts (docs/legal): the terms of service, the
    privacy policy, the cookie statement and the security overview of the
    public /security page. The data processing agreement has its own
    versions and acceptance (DPA_*).
    """

    TERMS = "terms"
    PRIVACY = "privacy"
    COOKIES = "cookies"
    SECURITY = "security"


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
    conversations, the transcription of voice notes and the embeddings of
    the knowledge search (the model's search queries and the business's
    knowledge). A sub-processor entry lists the flows its purpose covers.
    """

    ASSISTANT_REPLIES = "assistant_replies"
    CLAIM_VERIFIER = "claim_verifier"
    CONVERSATION_SUMMARIES = "conversation_summaries"
    AUTOTEST_JUDGE = "autotest_judge"
    QUALITY_SAMPLING = "quality_sampling"
    TRANSCRIPTION = "transcription"
    KNOWLEDGE_EMBEDDINGS = "knowledge_embeddings"


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


class TransferMechanism(StrEnum):
    """
    The safeguard of a sub-processor's processing (DPA sections 7.2 and 8):
    processed in the EEA, an adequacy decision, the EU-US Data Privacy
    Framework, the 2021 standard contractual clauses, binding corporate
    rules, none offered (a channel the Client chooses to turn on, under the
    vendor's own terms), or still to be confirmed in the contract. An entry
    lists every one that applies, e.g. EEA processing plus SCCs for the
    vendor's support access from the US.
    """

    EEA_PROCESSING = "eea_processing"
    ADEQUACY_DECISION = "adequacy_decision"
    DATA_PRIVACY_FRAMEWORK = "data_privacy_framework"
    STANDARD_CONTRACTUAL_CLAUSES = "standard_contractual_clauses"
    BINDING_CORPORATE_RULES = "binding_corporate_rules"
    NONE_OFFERED = "none_offered"
    TO_BE_CONFIRMED = "to_be_confirmed"
