from app.adapters.llm.website_extraction.website_extraction_prompt import (
    MAX_OUTPUT_TOKENS,
    build_instructions,
    build_page_message,
)
from app.adapters.llm.website_extraction.website_item_parsing import (
    parse_website_items,
)
from app.contracts.llm import LlmAdapterContract
from app.contracts.website_import import WebsiteExtractionAdapterContract
from app.schemas.constants.assistants import LlmEffort
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.dto.menu_import import ExtractedMenuItem
from app.schemas.dto.website_import import (
    WebsitePageExtraction,
    WebsitePageExtractionRequest,
)
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.menu_import.constrained_integers import MenuLineCount
from app.utilities.knowledge.website.website_text_fencing import new_fence_key


class WebsiteExtractionAdapter(WebsiteExtractionAdapterContract):
    """
    Reads one website page with the assistants' language model (any
    provider: the request goes through the routing, traced and
    concurrency-limited LLM adapter) and asks for a JSON list of items.

    The page text is fenced with a key random for each page, and the model
    is told the fenced text is untrusted data. Items of a kind the business
    does not keep, with an empty title or beyond 60 per page are skipped
    and counted; malformed prices, currencies, durations and tags are
    dropped from an item rather than failing the page.
    """

    def __init__(self, llm_adapter: LlmAdapterContract, model_id: LlmModelId) -> None:
        self._llm_adapter: LlmAdapterContract = llm_adapter
        self._model_id: LlmModelId = model_id

    def extract(self, request: WebsitePageExtractionRequest) -> WebsitePageExtraction:
        fence_key: str = new_fence_key()
        page_message: str = build_page_message(
            str(request.page.url),
            None if request.page.title is None else str(request.page.title),
            str(request.page.text),
            request.currency_code,
            fence_key,
        )
        response: LlmResponse = self._llm_adapter.complete(
            LlmRequest(
                model_id=self._model_id,
                system_prompt=SystemPromptText(
                    build_instructions(request.allowed_kinds, fence_key)
                ),
                tools=[],
                transcript=[
                    self._llm_adapter.build_user_text_turn(MessageText(page_message))
                ],
                max_output_tokens=LlmMaxOutputTokens(MAX_OUTPUT_TOKENS),
                effort=LlmEffort.LOW,
            )
        )
        parsed: tuple[list[ExtractedMenuItem], int] | None = parse_website_items(
            None if response.text is None else str(response.text),
            {kind.value for kind in request.allowed_kinds},
        )
        items, skipped = ([], 0) if parsed is None else parsed
        return WebsitePageExtraction(
            is_answer_readable=parsed is not None,
            items=items,
            skipped_line_count=MenuLineCount(skipped),
            model_id=self._model_id,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
