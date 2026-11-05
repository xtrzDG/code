"""
The OpenAI Embeddings API through the real SDK client: the documented
answer is read in input order, the request names the model, the texts and
float encoding at the EU endpoint, and failures become the platform's error.
"""

import json
from typing import Any

import httpx2
import openai
import pytest

from app.clients.openai.openai_embeddings_client import OpenAiEmbeddingsClient
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from tests.brain.provider_http_fakes import OPENAI_EU_BASE_URL, ScriptedHttp
from tests.contracts.contract_files import load_json_fixture

TEXTS: list[str] = ["გაქვთ პარკინგი?", "Do you have parking?"]


def build_client(http: ScriptedHttp) -> OpenAiEmbeddingsClient:
    def build_sdk() -> openai.OpenAI:
        return openai.OpenAI(
            api_key="test-token-0000",
            base_url=OPENAI_EU_BASE_URL,
            http_client=http.build_http_client(),
            max_retries=0,
        )

    return OpenAiEmbeddingsClient(
        api_key=PlatformSecret("test-token-0000"),
        base_url=PublicBaseUrl(OPENAI_EU_BASE_URL),
        project_id=PlatformIdentifier("proj_eu_restaurants"),
        sdk_factory=build_sdk,
    )


def answer(status: int, body: dict[str, Any]) -> httpx2.Response:
    return httpx2.Response(status, json=body)


def test_the_documented_answer_is_read_in_the_order_of_the_texts() -> None:
    fixture: dict[str, Any] = load_json_fixture("openai", "embeddings_response.json")
    http = ScriptedHttp(responses=[answer(200, fixture)])

    vectors = build_client(http).create_embeddings(
        model="text-embedding-3-small", texts=TEXTS
    )

    assert vectors == [
        [-0.0067, 0.0291, 0.0503, -0.0118],
        [0.0115, -0.0402, 0.0321, 0.0049],
    ]
    [request] = http.requests
    assert str(request.url) == f"{OPENAI_EU_BASE_URL}/embeddings"
    assert request.headers["authorization"] == "Bearer test-token-0000"
    assert json.loads(request.content) == {
        "model": "text-embedding-3-small",
        "input": TEXTS,
        "encoding_format": "float",
    }


def test_an_answer_with_missing_vectors_is_refused() -> None:
    fixture: dict[str, Any] = load_json_fixture("openai", "embeddings_response.json")
    fixture["data"] = fixture["data"][:1]
    http = ScriptedHttp(responses=[answer(200, fixture)])

    with pytest.raises(ExternalServiceError, match="1 vectors for 2 texts"):
        build_client(http).create_embeddings(
            model="text-embedding-3-small", texts=TEXTS
        )


def test_documented_errors_become_the_platforms_error() -> None:
    errors: dict[str, Any] = load_json_fixture("openai", "openai_errors.json")
    unauthorized = next(case for case in errors["cases"] if case["status"] == 401)
    http = ScriptedHttp(responses=[answer(401, unauthorized["body"])])

    with pytest.raises(ExternalServiceError, match="HTTP 401"):
        build_client(http).create_embeddings(
            model="text-embedding-3-small", texts=TEXTS
        )


def test_without_a_key_nothing_is_sent() -> None:
    client = OpenAiEmbeddingsClient(
        api_key=None,
        base_url=PublicBaseUrl(OPENAI_EU_BASE_URL),
        project_id=None,
    )

    with pytest.raises(ExternalServiceError, match="EMBEDDINGS_API_KEY"):
        client.create_embeddings(model="text-embedding-3-small", texts=TEXTS)
