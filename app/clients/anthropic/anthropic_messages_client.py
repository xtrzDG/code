import threading
from collections.abc import Callable
from typing import Literal, cast

import anthropic
from anthropic.types.beta import (
    BetaMessage,
    BetaMessageParam,
    BetaOutputConfigParam,
    BetaTextBlockParam,
    BetaToolUnionParam,
)

from app.contracts.llm_clients import AnthropicMessagesClientContract
from app.schemas.exceptions.application_errors import ExternalServiceError

type AnthropicSdkFactory = Callable[[], anthropic.Anthropic]

REQUEST_TIMEOUT_SECONDS: float = 120.0
MAX_RETRIES: int = 2
# Server-side refusal fallbacks: on a policy decline the API re-runs the same
# request on a fallback model chosen by the refusal category.
SERVER_SIDE_FALLBACK_BETA: Literal["server-side-fallback-2026-07-01"] = (
    "server-side-fallback-2026-07-01"
)
DEFAULT_FALLBACKS: Literal["default"] = "default"


class AnthropicMessagesClient(AnthropicMessagesClientContract):
    """
    Minimal client of the Anthropic Messages API (beta surface).

    Every request opts into automatic prompt caching of the conversation
    prefix, and into effort and server-side refusal fallbacks where the
    caller says the model supports them. No `thinking` parameter and no
    forced `tool_choice` are ever sent: the current models think adaptively
    and reject forced tool use. The SDK client is created on first use, so
    the application starts without ANTHROPIC_API_KEY.
    """

    def __init__(self, sdk_factory: AnthropicSdkFactory | None = None) -> None:
        self._sdk_factory: AnthropicSdkFactory = (
            sdk_factory if sdk_factory is not None else build_default_sdk_client
        )
        self._lock: threading.Lock = threading.Lock()
        self._sdk_client: anthropic.Anthropic | None = None

    def create_message(
        self,
        *,
        model: str,
        max_tokens: int,
        system: list[dict[str, object]],
        tools: list[dict[str, object]],
        messages: list[dict[str, object]],
        effort: str | None,
        is_fallback_enabled: bool,
    ) -> BetaMessage:
        sdk_client: anthropic.Anthropic = self._get_sdk_client()
        try:
            return sdk_client.beta.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=cast(list[BetaTextBlockParam], system),
                tools=(
                    cast(list[BetaToolUnionParam], tools) if tools else anthropic.omit
                ),
                messages=cast(list[BetaMessageParam], messages),
                output_config=(
                    cast(BetaOutputConfigParam, {"effort": effort})
                    if effort is not None
                    else anthropic.omit
                ),
                cache_control={"type": "ephemeral"},
                betas=(
                    [SERVER_SIDE_FALLBACK_BETA]
                    if is_fallback_enabled
                    else anthropic.omit
                ),
                fallbacks=DEFAULT_FALLBACKS if is_fallback_enabled else anthropic.omit,
            )
        except anthropic.AuthenticationError as error:
            raise ExternalServiceError("Anthropic rejected the API key.") from error
        except anthropic.PermissionDeniedError as error:
            raise ExternalServiceError(
                "Anthropic denied access to the model."
            ) from error
        except anthropic.NotFoundError as error:
            raise ExternalServiceError(
                f"Anthropic does not serve model {model}."
            ) from error
        except anthropic.RateLimitError as error:
            raise ExternalServiceError("Anthropic rate limit reached.") from error
        except (
            anthropic.BadRequestError,
            anthropic.RequestTooLargeError,
            anthropic.UnprocessableEntityError,
        ) as error:
            raise ExternalServiceError(
                f"Anthropic rejected the request (HTTP {error.status_code})."
            ) from error
        except (
            anthropic.OverloadedError,
            anthropic.ServiceUnavailableError,
            anthropic.DeadlineExceededError,
            anthropic.InternalServerError,
        ) as error:
            raise ExternalServiceError(
                f"Anthropic is unavailable (HTTP {error.status_code})."
            ) from error
        except anthropic.APIStatusError as error:
            raise ExternalServiceError(
                f"Anthropic returned HTTP {error.status_code}."
            ) from error
        except anthropic.APITimeoutError as error:
            raise ExternalServiceError("Anthropic did not answer in time.") from error
        except anthropic.APIConnectionError as error:
            raise ExternalServiceError("Anthropic cannot be reached.") from error
        except anthropic.APIResponseValidationError as error:
            raise ExternalServiceError(
                "Anthropic returned a response of an unexpected shape."
            ) from error
        except anthropic.AnthropicError as error:
            raise ExternalServiceError(
                f"Anthropic request failed: {type(error).__name__}."
            ) from error

    def _get_sdk_client(self) -> anthropic.Anthropic:
        with self._lock:
            if self._sdk_client is None:
                try:
                    self._sdk_client = self._sdk_factory()
                except anthropic.AnthropicError as error:
                    raise ExternalServiceError(
                        "Anthropic is not configured: set ANTHROPIC_API_KEY."
                    ) from error

            return self._sdk_client


def build_default_sdk_client() -> anthropic.Anthropic:
    """SDK client with credentials resolved from the environment."""

    return anthropic.Anthropic(
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=MAX_RETRIES,
    )
