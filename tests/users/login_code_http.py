"""A scripted httpx transport for the login code provider clients."""

import json
from typing import Any
from urllib.parse import parse_qs

import httpx


class ScriptedProvider:
    """Answers every request with the next scripted response and records it."""

    def __init__(self, *responses: httpx.Response | Exception) -> None:
        self.responses: list[httpx.Response | Exception] = list(responses)
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response = (
            self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        )
        if isinstance(response, Exception):
            raise response

        return response

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    def json_body(self) -> Any:
        return json.loads(self.last.content)

    def form_body(self) -> dict[str, list[str]]:
        return parse_qs(self.last.content.decode())


def json_response(status_code: int, body: object) -> httpx.Response:
    return httpx.Response(status_code, json=body)
