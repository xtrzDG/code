"""The embeddings endpoint the hybrid knowledge search reaches."""

from typing import Protocol

from app.contracts.client_contract import ClientContract


class OpenAiEmbeddingsClientContract(ClientContract, Protocol):
    def create_embeddings(self, *, model: str, texts: list[str]) -> list[list[float]]:
        """
        One embedding per text, in the order of `texts` (raw values at the
        provider boundary).

        Raises:
            ExternalServiceError: no key, the endpoint failed, timed out or
                answered in an unexpected shape.
        """
        raise NotImplementedError
