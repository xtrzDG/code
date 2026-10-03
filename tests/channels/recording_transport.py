"""An httpx mock transport that answers scripted routes and records requests."""

import json
import re
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class RecordedRequest:
    method: str
    url: httpx.URL
    headers: httpx.Headers
    body: bytes

    @property
    def path(self) -> str:
        return self.url.path

    def json(self) -> Any:
        return json.loads(self.body) if self.body else None


@dataclass
class ScriptedRoute:
    method: str
    path_pattern: re.Pattern[str]
    responses: list[tuple[int, object]]


@dataclass
class RecordingTransport:
    """httpx.MockTransport that answers scripted routes and records requests."""

    routes: list[ScriptedRoute] = field(default_factory=list[ScriptedRoute])
    requests: list[RecordedRequest] = field(default_factory=list[RecordedRequest])
    failure: Exception | None = None

    def respond(
        self,
        method: str,
        path_pattern: str,
        body: object,
        status_code: int = 200,
    ) -> None:
        """Answer matching requests; the newest script for a route wins."""

        self.routes.insert(
            0,
            ScriptedRoute(
                method=method,
                path_pattern=re.compile(path_pattern),
                responses=[(status_code, body)],
            ),
        )

    def respond_in_turn(
        self,
        method: str,
        path_pattern: str,
        responses: list[tuple[int, object]],
    ) -> None:
        """Answer matching requests with these responses in turn; the last stays."""

        self.routes.insert(
            0,
            ScriptedRoute(
                method=method,
                path_pattern=re.compile(path_pattern),
                responses=list(responses),
            ),
        )

    def build(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def requests_to(self, path_fragment: str) -> list[RecordedRequest]:
        return [request for request in self.requests if path_fragment in request.path]

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(
            RecordedRequest(
                method=request.method,
                url=request.url,
                headers=request.headers,
                body=request.content,
            )
        )
        if self.failure is not None:
            raise self.failure

        for route in self.routes:
            if route.method == request.method and route.path_pattern.search(
                request.url.path
            ):
                status_code, body = (
                    route.responses.pop(0)
                    if len(route.responses) > 1
                    else route.responses[0]
                )
                return httpx.Response(status_code, json=body)

        return httpx.Response(404, json={"error": "not scripted"})
