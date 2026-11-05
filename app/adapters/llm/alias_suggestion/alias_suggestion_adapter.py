from app.adapters.llm.alias_suggestion.alias_suggestion_parsing import (
    parse_suggested_aliases,
)
from app.adapters.llm.alias_suggestion.alias_suggestion_prompt import (
    MAX_OUTPUT_TOKENS,
    build_instructions,
    build_titles_message,
    new_fence_key,
)
from app.contracts.knowledge_aliases import KnowledgeAliasSuggesterContract
from app.contracts.llm import LlmAdapterContract
from app.schemas.constants.assistants import LlmEffort
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.dto.knowledge_aliases import (
    AliasSuggestionRequest,
    AliasSuggestionResult,
    SuggestedAlias,
)
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.strings import MessageText


class KnowledgeAliasSuggestionAdapter(KnowledgeAliasSuggesterContract):
    """
    Names knowledge items in the business's other languages with one call
    to a language model (any provider: the request goes through the
    routing, traced and concurrency-limited LLM adapter).

    The titles go to the model as numbered JSON inside a fence whose key is
    random for each call, and the model is told the fenced titles are
    untrusted data. Aliases for languages that were not asked for, empty or
    overlong ones and ones that only repeat the title are dropped.
    """

    def __init__(self, llm_adapter: LlmAdapterContract, model_id: LlmModelId) -> None:
        self._llm_adapter: LlmAdapterContract = llm_adapter
        self._model_id: LlmModelId = model_id

    def suggest(self, request: AliasSuggestionRequest) -> AliasSuggestionResult:
        if request.items == []:
            return AliasSuggestionResult(model_id=self._model_id)

        fence_key: str = new_fence_key()
        response: LlmResponse = self._llm_adapter.complete(
            LlmRequest(
                model_id=self._model_id,
                system_prompt=SystemPromptText(build_instructions(fence_key)),
                tools=[],
                transcript=[
                    self._llm_adapter.build_user_text_turn(
                        MessageText(build_titles_message(request.items, fence_key))
                    )
                ],
                max_output_tokens=LlmMaxOutputTokens(MAX_OUTPUT_TOKENS),
                effort=LlmEffort.LOW,
            )
        )
        aliases: list[SuggestedAlias] | None = parse_suggested_aliases(
            None if response.text is None else str(response.text),
            request.items,
        )
        return AliasSuggestionResult(
            is_answer_readable=aliases is not None,
            aliases=[] if aliases is None else aliases,
            model_id=self._model_id,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
