"""The model that names knowledge items in the business's other languages."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.knowledge_aliases import (
    AliasSuggestionRequest,
    AliasSuggestionResult,
)


class KnowledgeAliasSuggesterContract(AdapterContract, Protocol):
    def suggest(self, request: AliasSuggestionRequest) -> AliasSuggestionResult:
        """
        One model call for every item of the request: each title written
        as a customer of the business would write it in each target
        language. The titles are untrusted (an import may have read them
        from a website): they reach the model fenced, as data. Nothing is
        added that the title does not say; a language the model is unsure
        of is left out.

        An answer that is not the requested JSON is returned as unreadable
        (with the tokens it cost), not raised.

        Raises:
            ExternalServiceError: the model is unavailable (LlmRefusedError:
                it declined).
        """
        raise NotImplementedError
