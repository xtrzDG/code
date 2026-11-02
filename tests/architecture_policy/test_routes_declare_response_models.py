"""
Every route declares what it answers (OWASP API3, ASVS V15.3.1): a typed
response DTO from `app/schemas/dto` (FastAPI reads it from the return
annotation), or a hand-built `Response` whose bytes the route makes itself
(a redirect, an empty 204, a file, a provider's own format). A route
answering a dict, `Any` or a stored document would serialize whatever the
object holds, so it fails here before the API description changes.
"""

import inspect
import os
import typing
from collections.abc import Iterator, Sequence

import pytest
from base_pydantic_schemas import ImmutableDTO
from fastapi import APIRouter, FastAPI, Response
from fastapi.routing import APIRoute
from pydantic import BaseModel
from starlette.routing import BaseRoute

from app.main import create_application
from app.schemas.domain.users import UserDocument
from app.schemas.dto.conversation_feed.conversation_views import ConversationPage

DTO_PACKAGE: str = "app.schemas.dto"


@pytest.fixture(scope="module")
def application() -> Iterator[FastAPI]:
    saved: dict[str, str] = dict(os.environ)
    os.environ.clear()
    try:
        yield create_application()
    finally:
        os.environ.clear()
        os.environ.update(saved)


def api_routes(application: FastAPI) -> list[APIRoute]:
    return list(walk(application.routes))


def walk(routes: Sequence[BaseRoute]) -> Iterator[APIRoute]:
    """The API routes, also those of included routers (kept whole by FastAPI)."""

    for route in routes:
        if isinstance(route, APIRoute):
            yield route

        included: object = getattr(route, "original_router", None)
        if isinstance(included, APIRouter):
            yield from walk(included.routes)


def model_classes(annotation: object) -> list[type]:
    """The classes inside a response model (`list[X]`, `X | None`)."""

    if isinstance(annotation, type):
        return [annotation]

    return [
        found
        for argument in typing.get_args(annotation)
        for found in model_classes(argument)
    ]


def returns_a_built_response(route: APIRoute) -> bool:
    annotation: object = inspect.signature(route.endpoint).return_annotation
    return isinstance(annotation, type) and issubclass(annotation, Response)


def is_dto(model: type) -> bool:
    return issubclass(model, ImmutableDTO) and model.__module__.startswith(DTO_PACKAGE)


def describe(route: APIRoute) -> str:
    return f"{sorted(route.methods)} {route.path}"


def undeclared_routes(routes: list[APIRoute]) -> list[str]:
    """Routes that answer neither a DTO (or a list of them) nor a built Response."""

    return [
        describe(route)
        for route in routes
        if not returns_a_built_response(route)
        and route.status_code != 204
        and not any(is_dto(model) for model in model_classes(route.response_model))
    ]


def misplaced_models(routes: list[APIRoute]) -> list[str]:
    """Pydantic models in answers that are not DTOs (a stored document)."""

    return [
        f"{describe(route)}: {model.__module__}.{model.__qualname__}"
        for route in routes
        for model in model_classes(route.response_model)
        if issubclass(model, BaseModel) and not is_dto(model)
    ]


def test_the_application_has_routes(application: FastAPI) -> None:
    assert len(api_routes(application)) >= 400


def test_every_route_declares_a_response_dto_or_builds_its_response(
    application: FastAPI,
) -> None:
    assert undeclared_routes(api_routes(application)) == []


def test_response_models_are_dtos_never_stored_documents(
    application: FastAPI,
) -> None:
    assert misplaced_models(api_routes(application)) == []


def test_the_checks_catch_a_dict_a_document_and_an_untyped_answer() -> None:
    router = APIRouter()

    @router.get("/dict")
    def answer_a_dict() -> dict[str, str]:
        return {}

    @router.get("/document")
    def answer_a_document() -> UserDocument:
        raise NotImplementedError

    @router.get("/untyped")
    def answer_anything():  # type: ignore[no-untyped-def]  # noqa: ANN202
        return None

    @router.get("/dto")
    def answer_a_dto() -> list[ConversationPage]:
        return []

    @router.get("/redirect")
    def answer_a_redirect() -> Response:
        return Response(status_code=303)

    routes: list[APIRoute] = list(walk(router.routes))

    assert undeclared_routes(routes) == [
        "['GET'] /dict",
        "['GET'] /document",
        "['GET'] /untyped",
    ]
    assert misplaced_models(routes) == [
        "['GET'] /document: app.schemas.domain.users.UserDocument"
    ]
