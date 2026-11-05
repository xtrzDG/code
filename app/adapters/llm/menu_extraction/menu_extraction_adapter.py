from openai.types.responses import Response

from app.adapters.llm.menu_extraction.menu_extraction_prompt import (
    EXTRACTION_INSTRUCTIONS,
    MAX_OUTPUT_TOKENS,
    REASONING_EFFORT,
    TEXT_FORMAT,
)
from app.adapters.llm.menu_extraction.menu_item_parsing import parse_menu_extraction
from app.adapters.llm.menu_extraction.menu_link_reading import read_menu_link
from app.adapters.llm.menu_extraction.menu_media_content import (
    build_media_content,
    decode_base64,
)
from app.contracts.brain import MenuExtractionAdapterContract
from app.contracts.llm_clients import OpenAiResponsesClientContract
from app.contracts.web_fetching import SafeHttpFetcherContract
from app.schemas.dto.menu_import import MenuExtraction, MenuExtractionRequest
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId


class MenuExtractionAdapter(MenuExtractionAdapterContract):
    """
    Reads a menu with a vision-capable OpenAI model (Responses API, strict
    JSON output): photos go as images, PDFs as files, plain text and web
    pages as text (web pages without scripts, styles or hidden text). A
    link is read through the safe fetcher: public http(s) addresses on
    ports 80/443 only, connected at the vetted address, at most 10 MB, with
    up to three checked redirects.

    A link that is not public, cannot be fetched or cannot be read as a
    menu is a ValidationFailedError (422) with a MenuLinkProblem reason; an
    unavailable model stays an ExternalServiceError (502).

    Lines the model returns in an unusable shape (empty title, unknown kind)
    are skipped and counted; malformed prices, currencies, durations and
    tags are dropped from a line rather than failing the import.
    """

    def __init__(
        self,
        client: OpenAiResponsesClientContract,
        model_id: LlmModelId,
        page_fetcher: SafeHttpFetcherContract,
    ) -> None:
        self._client: OpenAiResponsesClientContract = client
        self._model_id: LlmModelId = model_id
        self._page_fetcher: SafeHttpFetcherContract = page_fetcher

    def extract(self, request: MenuExtractionRequest) -> MenuExtraction:
        content: list[dict[str, object]] = self._build_content(request)
        content.append(
            {
                "type": "input_text",
                "text": (
                    "Read this menu. If no currency is printed, the business "
                    f"currency is {request.currency_code}."
                ),
            }
        )
        response: Response = self._client.create_response(
            model=str(self._model_id),
            instructions=EXTRACTION_INSTRUCTIONS,
            input_items=[{"role": "user", "content": content}],
            tools=[],
            reasoning_effort=REASONING_EFFORT,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            text_format=TEXT_FORMAT,
        )
        if response.status == "incomplete" or response.error is not None:
            raise ExternalServiceError("The menu could not be read completely.")

        return parse_menu_extraction(response.output_text)

    def _build_content(self, request: MenuExtractionRequest) -> list[dict[str, object]]:
        if request.data_base64 is not None:
            data: bytes = decode_base64(str(request.data_base64))
            return build_media_content(str(request.media_type), data)

        if request.url is not None:
            media_type, data = read_menu_link(self._page_fetcher, request.url)
            return build_media_content(media_type, data)

        raise ValidationFailedError("Upload a menu file or give a link to it.")
