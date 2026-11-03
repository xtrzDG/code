"""
The raw error texts providers answered reach platform admins only (OWASP
API3, ASVS V15.3.1, API-05): text-backs, feedback requests, notification
contacts, devices and checks, and channels answer owners and staff
without `last_error`, but with the plain state (`status`,
`is_last_delivery_failed`, a channel's `last_error_reason`). Whether the
person is an admin is asked at every request, with their own id.
"""

import json
import uuid
from collections.abc import Callable
from typing import Any, cast

import pytest
from pydantic import BaseModel

from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.team_view_orchestrator import TeamViewOrchestrator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.schemas.dto.calls.call_settings import TextBackPage, TextBackPageQuery
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.feedback.feedback_requests import FeedbackRequestPage
from app.schemas.dto.notifications.notification_settings import (
    MyNotificationSettingsView,
    NotificationCheckResult,
    NotificationContactList,
    PushDeviceView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.booleans import IsPlatformAdmin
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.deliveries import provider_error_details as views

PROVIDER_WORDS: str = "Telegram sendMessage failed (502): Bad Gateway"
# Ids derived with UUID v5, as missed calls and feedback requests are.
DERIVED: str = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://workshop.example/visit"))
BUSINESS: BusinessId = BusinessId()
OWNER: UserId = UserId()
ADMIN: UserId = UserId()
DELIVERY: dict[str, Any] = {
    "status": "dead",
    "last_error": PROVIDER_WORDS,
    "is_last_delivery_failed": True,
    "attempted_at": 1,
}


def from_json[Model: BaseModel](model: type[Model], data: dict[str, Any]) -> Model:
    """A view as the API's JSON reads (enum values as strings)."""

    return model.model_validate_json(json.dumps(data))


class AdminTeam(UseCaseContract[UserId, IsPlatformAdmin]):
    """Who is a platform admin now, and who was asked."""

    def __init__(self) -> None:
        self.asked: list[UserId] = []

    def run(self, input_data: UserId) -> IsPlatformAdmin:
        self.asked.append(input_data)
        return input_data == ADMIN


class Answer(UseCaseContract[TextBackPageQuery, TextBackPage]):
    def run(self, input_data: TextBackPageQuery) -> TextBackPage:
        return text_backs()


def text_backs() -> TextBackPage:
    return from_json(
        TextBackPage,
        {
            "items": [
                {
                    "id": f"missed_call_{DERIVED}",
                    "reason": "no_answer",
                    "source": "pbx",
                    "called_at": 1,
                    "language": "en",
                    "status": "failed",
                    "last_error": PROVIDER_WORDS,
                }
            ]
        },
    )


def feedback_requests() -> FeedbackRequestPage:
    return from_json(
        FeedbackRequestPage,
        {
            "items": [
                {
                    "id": f"feedback_request_{DERIVED}",
                    "booking_id": "booking_7d8d3d4c-2f7e-4a8a-9f53-0f4c1f1d0a11",
                    "contact_id": "contact_7d8d3d4c-2f7e-4a8a-9f53-0f4c1f1d0a11",
                    "visit_ended_at": 1,
                    "status": "failed",
                    "review_clicks": 0,
                    "last_error": PROVIDER_WORDS,
                }
            ]
        },
    )


def contacts() -> NotificationContactList:
    return from_json(
        NotificationContactList,
        {
            "business_id": str(BUSINESS),
            "items": [
                {
                    "key": "a" * 24,
                    "name": "Nino",
                    "channel": "telegram",
                    "address": "70001",
                    "language": "en",
                    "preferences": {"events": ["handoff"], "quiet_hours": None},
                    "provider_ready": True,
                    "delivery": DELIVERY,
                }
            ],
        },
    )


def device() -> PushDeviceView:
    return from_json(
        PushDeviceView,
        {
            "id": f"push_subscription_{DERIVED}",
            "language": "en",
            "created_at": 1,
            "last_error": PROVIDER_WORDS,
            "is_last_delivery_failed": True,
        },
    )


def settings() -> MyNotificationSettingsView:
    return from_json(
        MyNotificationSettingsView,
        {
            "business_id": str(BUSINESS),
            "preferences": {"events": ["handoff"], "quiet_hours": None},
            "devices": [device().model_dump(mode="json")],
        },
    )


def check() -> NotificationCheckResult:
    return from_json(NotificationCheckResult, {"delivery": DELIVERY})


def channel() -> ChannelView:
    return from_json(
        ChannelView,
        {
            "id": "channel_7d8d3d4c-2f7e-4a8a-9f53-0f4c1f1d0a11",
            "business_id": str(BUSINESS),
            "channel": "telegram",
            "status": "error",
            "has_credential": True,
            "updated_at": 1,
            "last_error": PROVIDER_WORDS,
            "last_error_at": 1,
            "last_error_reason": "credential_rejected",
        },
    )


TEAM_VIEWS: list[tuple[Callable[[], Any], Callable[[Any], Any]]] = [
    (text_backs, views.team_text_backs),
    (feedback_requests, views.team_feedback_requests),
    (contacts, views.team_notification_contacts),
    (check, views.team_notification_check),
    (device, views.team_device),
    (settings, views.team_notification_settings),
    (channel, views.team_channel),
    (lambda: [channel()], views.team_channels),
]


def without_provider_words(answer: object) -> object:
    """The answer as JSON, every last_error taken out."""

    if isinstance(answer, dict):
        fields: dict[str, object] = cast(dict[str, object], answer)
        return {
            key: without_provider_words(value)
            for key, value in fields.items()
            if key != "last_error"
        }
    if isinstance(answer, list):
        items: list[object] = cast(list[object], answer)
        return [without_provider_words(item) for item in items]
    return answer


def as_json(answer: BaseModel | list[ChannelView]) -> object:
    if isinstance(answer, list):
        return [item.model_dump(mode="json") for item in answer]
    return answer.model_dump(mode="json")


@pytest.mark.parametrize(
    ("build", "for_team"),
    TEAM_VIEWS,
    ids=[for_team.__name__ for _, for_team in TEAM_VIEWS],
)
def test_the_team_reads_everything_but_the_providers_words(
    build: Callable[[], Any], for_team: Callable[[Any], Any]
) -> None:
    whole: object = as_json(build())
    team: object = as_json(for_team(build()))

    assert PROVIDER_WORDS in str(whole)
    assert PROVIDER_WORDS not in str(team)
    assert without_provider_words(team) == without_provider_words(whole)


def test_a_view_built_without_the_flag_still_says_it_failed() -> None:
    unflagged = check().delivery.model_copy(update={"is_last_delivery_failed": False})

    team = views.team_delivery(unflagged)

    assert team.last_error is None
    assert team.is_last_delivery_failed


def test_a_channel_keeps_its_reason_and_a_delivery_its_failure() -> None:
    assert views.team_channel(channel()).last_error_reason is not None
    assert views.team_notification_check(check()).delivery.is_last_delivery_failed
    assert views.team_device(device()).is_last_delivery_failed


@pytest.mark.parametrize(
    ("user_id", "sees"), [(ADMIN, True), (OWNER, False)], ids=["admin", "owner"]
)
def test_only_a_platform_admin_of_now_gets_the_whole_answer(
    user_id: UserId, sees: bool
) -> None:
    admins = AdminTeam()
    orchestrator = TeamViewOrchestrator(
        UseCaseOrchestrator(Answer()), admins, views.team_text_backs
    )

    page = orchestrator.execute(
        TextBackPageQuery(user_id=user_id, business_id=BUSINESS)
    )

    assert admins.asked == [user_id]
    assert (page.items[0].last_error is not None) is sees
