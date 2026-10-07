"""
A small API with one creating route behind the Idempotency-Key dependency,
the response recorder and the error handlers, over the idempotency world.
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated

from base_pydantic_schemas import ImmutableDTO
from fastapi import APIRouter, Depends, FastAPI, Header, Request
from fastapi.testclient import TestClient

from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.idempotency.idempotency_dependency import (
    build_idempotency_dependency,
)
from app.gateways.http.idempotency.response_recorder import install_idempotency
from app.gateways.http.strict_request_parsing import build_json_body_dependency
from app.schemas.typings.users.prefixed_id import UserId
from tests.idempotency.idempotency_world import OWNER, IdempotencyWorld

THINGS: str = "/v1/things"


class ThingRequest(ImmutableDTO):
    name: str
    size: int = 1


class ThingView(ImmutableDTO):
    id: str
    name: str
    note: str = ""


read_thing_body = build_json_body_dependency(ThingRequest)


async def signed_in_user(
    request: Request, authorization: Annotated[str | None, Header()] = None
) -> UserId:
    del request
    return UserId(authorization) if authorization else OWNER


@dataclass
class ThingMaker:
    """The route's work: counts its runs; can block, fail or answer big."""

    runs: int = 0
    entered: threading.Event = field(default_factory=threading.Event)
    proceed: threading.Event = field(default_factory=threading.Event)
    blocks: bool = False
    fails_with: Exception | None = None
    note: str = ""

    def make(self, body: ThingRequest) -> ThingView:
        self.runs += 1
        self.entered.set()
        if self.blocks:
            assert self.proceed.wait(timeout=30)
        if self.fails_with is not None:
            raise self.fails_with
        return ThingView(id=f"thing_{self.runs}", name=body.name, note=self.note)


def build_thing_api(
    world: IdempotencyWorld,
    maker: ThingMaker,
    install: Callable[[FastAPI], None] = install_idempotency,
) -> TestClient:
    application = FastAPI()
    install_error_handlers(application)
    install(application)
    idempotent = build_idempotency_dependency(
        signed_in_user, world.claim_operator(), world.finish_operator()
    )
    router = APIRouter()

    @router.post(THINGS, status_code=201, dependencies=[Depends(idempotent)])
    def create_thing(
        body: Annotated[ThingRequest, Depends(read_thing_body)],
    ) -> ThingView:
        return maker.make(body)

    application.include_router(router)
    return TestClient(application, raise_server_exceptions=False)


def with_key(key: str, user: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {"Idempotency-Key": key}
    if user is not None:
        headers["Authorization"] = user
    return headers
