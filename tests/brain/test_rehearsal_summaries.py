"""The development model writes a conversation summary from the customer's words."""

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.constants.assistants import LlmEffort
from app.schemas.dto.conversations import LlmRequest
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.llm_rehearsal.rehearsal_background import (
    EMPTY_CONVERSATION_SUMMARY,
    rehearse_background_task,
    rehearse_summary,
)
from app.utilities.memory.conversation_summary_prompt import (
    CONVERSATION_SUMMARY_SYSTEM_PROMPT,
)


def summary_request(text: str, prompt: str) -> LlmRequest:
    adapter = ScriptedLlmAdapter.from_turns([])
    return LlmRequest(
        model_id=LlmModelId("scripted"),
        system_prompt=SystemPromptText(prompt),
        tools=[],
        transcript=[adapter.build_user_text_turn(MessageText(text))],
        max_output_tokens=LlmMaxOutputTokens(400),
        effort=LlmEffort.LOW,
    )


def test_the_summary_quotes_what_the_customer_first_wrote() -> None:
    request = summary_request(
        "Business: Sakhli\nConversation:\nCustomer: A table for 2 tonight?\n"
        "Assistant: Booked.\nCustomer: Thanks!",
        CONVERSATION_SUMMARY_SYSTEM_PROMPT,
    )

    assert rehearse_background_task(request) == (
        "The customer wrote: “A table for 2 tonight?”"
    )


def test_long_or_missing_words_still_make_a_short_summary() -> None:
    assert rehearse_summary("Conversation:\nAssistant: Hello") == (
        EMPTY_CONVERSATION_SUMMARY
    )
    assert len(rehearse_summary("Customer: " + "x" * 500)) < 300


def test_the_assistant_turns_are_not_background_tasks() -> None:
    assert (
        rehearse_background_task(summary_request("Hi", "You are Sakhli's ...")) is None
    )
