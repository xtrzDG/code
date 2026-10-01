import threading
from collections.abc import Callable
from typing import cast

import openai
from openai.types.responses import (
    Response,
    ResponseIncludable,
    ResponseInputParam,
    ResponseTextConfigParam,
    ToolParam,
)
from openai.types.shared_params import Reasoning

from app.contracts.llm_clients import OpenAiResponsesClientContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier

type OpenAiSdkFactory = Callable[[], openai.OpenAI]

REQUEST_TIMEOUT_SECONDS: float = 60.0
MAX_RETRIES: int = 2
ENCRYPTED_REASONING_INCLUDE: ResponseIncludable = "reasoning.encrypted_content"


class OpenAiResponsesClient(OpenAiResponsesClientContract):
    """
    Minimal client of the OpenAI Responses API.

    Requests go to the configured base URL (the EU data-residency endpoint
    `https://eu.api.openai.com/v1` by default) in the configured project.
    Calls are stateless (`store=False`); encrypted reasoning items are
    requested so the transcript can be replayed verbatim. The SDK client is
    created on first use, so the application starts without OPENAI_API_KEY.
    """

    def __init__(
        self,
        base_url: PublicBaseUrl,
        project_id: PlatformIdentifier | None,
        sdk_factory: OpenAiSdkFactory | None = None,
    ) -> None:
        self._base_url: PublicBaseUrl = base_url
        self._project_id: PlatformIdentifier | None = project_id
        self._sdk_factory: OpenAiSdkFactory = (
            sdk_factory if sdk_factory is not None else self._build_sdk_client
        )
        self._lock: threading.Lock = threading.Lock()
        self._sdk_client: openai.OpenAI | None = None

    def create_response(
        self,
        *,
        model: str,
        instructions: str,
        input_items: list[dict[str, object]],
        tools: list[dict[str, object]],
        reasoning_effort: str | None,
        max_output_tokens: int,
        text_format: dict[str, object] | None = None,
    ) -> Response:
        sdk_client: openai.OpenAI = self._get_sdk_client()
        reasoning: Reasoning | openai.Omit = openai.omit
        include: list[ResponseIncludable] | openai.Omit = openai.omit
        if reasoning_effort is not None:
            reasoning = cast(Reasoning, {"effort": reasoning_effort})
            include = [ENCRYPTED_REASONING_INCLUDE]

        try:
            return sdk_client.responses.create(
                model=model,
                instructions=instructions,
                input=cast(ResponseInputParam, input_items),
                tools=cast(list[ToolParam], tools) if tools else openai.omit,
                reasoning=reasoning,
                include=include,
                max_output_tokens=max_output_tokens,
                store=False,
                text=(
                    cast(ResponseTextConfigParam, {"format": text_format})
                    if text_format is not None
                    else openai.omit
                ),
            )
        except openai.AuthenticationError as error:
            raise ExternalServiceError(
                "OpenAI rejected the API key or project."
            ) from error
        except openai.PermissionDeniedError as error:
            raise ExternalServiceError(
                "OpenAI denied access to the model or the data-residency region."
            ) from error
        except openai.NotFoundError as error:
            raise ExternalServiceError(
                f"OpenAI does not serve model {model}."
            ) from error
        except openai.RateLimitError as error:
            raise ExternalServiceError("OpenAI rate limit or quota reached.") from error
        except (openai.BadRequestError, openai.UnprocessableEntityError) as error:
            raise ExternalServiceError(
                f"OpenAI rejected the request (HTTP {error.status_code})."
            ) from error
        except openai.InternalServerError as error:
            raise ExternalServiceError(
                f"OpenAI is unavailable (HTTP {error.status_code})."
            ) from error
        except openai.APIStatusError as error:
            raise ExternalServiceError(
                f"OpenAI returned HTTP {error.status_code}."
            ) from error
        except openai.APITimeoutError as error:
            raise ExternalServiceError("OpenAI did not answer in time.") from error
        except openai.APIConnectionError as error:
            raise ExternalServiceError("OpenAI cannot be reached.") from error
        except openai.APIResponseValidationError as error:
            raise ExternalServiceError(
                "OpenAI returned a response of an unexpected shape."
            ) from error
        except openai.OpenAIError as error:
            raise ExternalServiceError(
                f"OpenAI request failed: {type(error).__name__}."
            ) from error

    def _get_sdk_client(self) -> openai.OpenAI:
        with self._lock:
            if self._sdk_client is None:
                try:
                    self._sdk_client = self._sdk_factory()
                except openai.OpenAIError as error:
                    raise ExternalServiceError(
                        "OpenAI is not configured: set OPENAI_API_KEY."
                    ) from error

            return self._sdk_client

    def _build_sdk_client(self) -> openai.OpenAI:
        return openai.OpenAI(
            base_url=str(self._base_url),
            project=None if self._project_id is None else str(self._project_id),
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=MAX_RETRIES,
        )
