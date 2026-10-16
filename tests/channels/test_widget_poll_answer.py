"""
The widget poll serializes its answer in the route (one hop to a request
thread instead of two): the answer is byte for byte the one FastAPI builds
for a route that returns the DTO, headers included, and the API description
still names the DTO.
"""

from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from httpx2 import Response as HttpResponse
from typed_time_provider import Microseconds

from app.gateways.http.serialized_json_response import serialized_json_response
from app.gateways.http.widget_cors_middleware import WIDGET_CORS_HEADERS
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.localization import TextDirection
from app.schemas.dto.channels.widget import WidgetMessagesView, WidgetMessageView
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.e2e.harness import start_workshop

VIEWS: tuple[WidgetMessagesView, ...] = (
    WidgetMessagesView(items=[]),
    WidgetMessagesView(items=[], cursor=MessageId(), is_handed_off=True),
    WidgetMessagesView(
        items=[
            WidgetMessageView(
                id=MessageId(),
                author=MessageAuthor.ASSISTANT,
                text=MessageText('שלום! "Table" for 2?\nДа — 🍷 \\ ok '),
                language=LanguageTag("he"),
                direction=TextDirection.RIGHT_TO_LEFT,
                created_at=Microseconds(1_790_000_000_000_001),
            ),
            WidgetMessageView(
                id=MessageId(),
                author=MessageAuthor.STAFF,
                text=MessageText("Hi"),
                direction=TextDirection.LEFT_TO_RIGHT,
                created_at=Microseconds(1_790_000_000_000_002),
            ),
        ],
        cursor=MessageId(),
        has_more=True,
    ),
)


def answers(view: WidgetMessagesView) -> tuple[HttpResponse, HttpResponse]:
    """The view as FastAPI answers it and as the helper does."""

    application = FastAPI()

    @application.get("/framework")
    def framework(response: Response) -> WidgetMessagesView:
        response.headers.update(WIDGET_CORS_HEADERS)
        return view

    @application.get("/serialized", response_model=WidgetMessagesView)
    def serialized() -> Response:
        return serialized_json_response(view, WIDGET_CORS_HEADERS)

    client = TestClient(application)
    return client.get("/framework"), client.get("/serialized")


class TestWidgetPollAnswer:
    def test_the_answer_is_the_one_fastapi_builds(self) -> None:
        for view in VIEWS:
            framework, serialized = answers(view)

            assert serialized.status_code == framework.status_code == 200
            assert serialized.content == framework.content
            assert serialized.headers.raw == framework.headers.raw

    def test_the_api_description_names_the_view(self) -> None:
        description = start_workshop().application.openapi()
        poll = description["paths"]["/v1/widget/{business_id}/messages"]["get"]

        assert poll["responses"]["200"]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/WidgetMessagesView"
        }
