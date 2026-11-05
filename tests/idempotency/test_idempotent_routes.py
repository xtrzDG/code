"""
A creating route behind the Idempotency-Key dependency: a retry gets the
first answer back instead of a second creation, another body with the same
key and a retry while the first request runs are refused (409), a refused
or failed request frees its key, and a request without a key is untouched.
"""

import threading
from typing import Any

import pytest
from fastapi import FastAPI

from app.schemas.exceptions.application_errors import ConflictError
from tests.idempotency.idempotency_world import IdempotencyWorld
from tests.idempotency.idempotent_route_app import (
    THINGS,
    ThingMaker,
    build_thing_api,
    with_key,
)

KEY: str = "7d1f4e8a-9c3b-4b0e-2a5c-1f2e3d4c5b6a"


def reason_of(response_json: dict[str, Any]) -> object:
    reasons: list[dict[str, object]] = response_json["reasons"]
    return reasons[0]["code"]


def test_without_a_key_every_request_runs() -> None:
    maker = ThingMaker()
    client = build_thing_api(IdempotencyWorld(), maker)

    first = client.post(THINGS, json={"name": "table"})
    second = client.post(THINGS, json={"name": "table"})

    assert (first.status_code, second.status_code) == (201, 201)
    assert first.json()["id"] != second.json()["id"]
    assert maker.runs == 2


def test_a_retry_replays_the_first_answer_without_running_again() -> None:
    maker = ThingMaker(note="Готово ✓")
    client = build_thing_api(IdempotencyWorld(), maker)

    first = client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))
    retry = client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))

    assert maker.runs == 1
    assert (first.status_code, retry.status_code) == (201, 201)
    assert retry.content == first.content
    assert retry.json()["note"] == "Готово ✓"
    assert retry.headers["content-type"] == first.headers["content-type"]
    assert retry.headers["idempotent-replayed"] == "true"
    assert "idempotent-replayed" not in first.headers


def test_the_same_body_in_another_order_and_spacing_is_the_same_request() -> None:
    maker = ThingMaker()
    client = build_thing_api(IdempotencyWorld(), maker)
    headers = {**with_key(KEY), "Content-Type": "application/json"}

    client.post(THINGS, content=b'{"name": "table", "size": 2}', headers=headers)
    retry = client.post(THINGS, content=b'{"size":2,"name":"table"}', headers=headers)

    assert retry.status_code == 201
    assert maker.runs == 1


def test_the_same_key_with_another_body_is_refused() -> None:
    maker = ThingMaker()
    client = build_thing_api(IdempotencyWorld(), maker)
    client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))

    reused = client.post(THINGS, json={"name": "chair"}, headers=with_key(KEY))

    assert reused.status_code == 409
    assert reused.json()["error"] == "conflict"
    assert reason_of(reused.json()) == "idempotency_key_reused"
    assert maker.runs == 1


def test_another_user_may_use_the_same_key() -> None:
    maker = ThingMaker()
    client = build_thing_api(IdempotencyWorld(), maker)
    client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))

    other = client.post(
        THINGS,
        json={"name": "chair"},
        headers=with_key(KEY, user="user_00000000-0000-4000-8000-0000000000aa"),
    )

    assert other.status_code == 201
    assert maker.runs == 2


def test_a_retry_while_the_first_request_runs_is_refused_in_progress() -> None:
    maker = ThingMaker(blocks=True)
    client = build_thing_api(IdempotencyWorld(), maker)
    answers: dict[str, int] = {}

    def first_request() -> None:
        answer = client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))
        answers["first"] = answer.status_code

    running = threading.Thread(target=first_request)
    running.start()
    assert maker.entered.wait(timeout=30)
    during = client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))
    maker.proceed.set()
    running.join(timeout=30)
    after = client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))

    assert during.status_code == 409
    assert reason_of(during.json()) == "in_progress"
    assert answers == {"first": 201}
    assert after.status_code == 201
    assert after.headers["idempotent-replayed"] == "true"
    assert maker.runs == 1


def test_a_refused_request_frees_its_key_and_the_retry_runs() -> None:
    maker = ThingMaker(fails_with=ConflictError("Slot taken."))
    client = build_thing_api(IdempotencyWorld(), maker)
    refused = client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))
    maker.fails_with = None

    retry = client.post(THINGS, json={"name": "chair"}, headers=with_key(KEY))

    assert refused.status_code == 409
    assert retry.status_code == 201
    assert retry.json()["name"] == "chair"
    assert maker.runs == 2


def test_an_unexpected_failure_frees_its_key() -> None:
    maker = ThingMaker(fails_with=RuntimeError("database restarting"))
    client = build_thing_api(IdempotencyWorld(), maker)
    failed = client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))
    maker.fails_with = None

    retry = client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))

    assert failed.status_code == 500
    assert retry.status_code == 201
    assert "idempotent-replayed" not in retry.headers


def test_an_invalid_key_is_refused_before_anything_runs() -> None:
    maker = ThingMaker()
    client = build_thing_api(IdempotencyWorld(), maker)

    spaced = client.post(THINGS, json={"name": "a"}, headers=with_key("two words"))
    long = client.post(THINGS, json={"name": "a"}, headers=with_key("k" * 256))

    for refused in (spaced, long):
        assert refused.status_code == 422
        assert refused.json()["reasons"][0]["details"] == ["header.Idempotency-Key"]
    assert maker.runs == 0


def test_a_huge_answer_is_passed_on_but_not_kept() -> None:
    world = IdempotencyWorld()
    maker = ThingMaker(note="x" * (300 * 1024))
    client = build_thing_api(world, maker)

    first = client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))
    retry = client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))

    assert len(first.json()["note"]) == 300 * 1024
    assert retry.status_code == 201
    assert maker.runs == 2


def test_the_answer_goes_out_even_when_the_key_cannot_be_settled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = IdempotencyWorld()
    maker = ThingMaker()
    client = build_thing_api(world, maker)
    monkeypatch.setattr(world.collection, "modify", failing_modify)

    answer = client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))

    assert answer.status_code == 201
    assert maker.runs == 1


def failing_modify(*arguments: object) -> None:
    del arguments
    raise ConnectionError("database restarting")


def test_a_key_without_the_recorder_is_a_wiring_error() -> None:
    def without_recorder(application: FastAPI) -> None:
        del application

    client = build_thing_api(IdempotencyWorld(), ThingMaker(), without_recorder)

    unwired = client.post(THINGS, json={"name": "table"}, headers=with_key(KEY))
    plain = client.post(THINGS, json={"name": "table"})

    assert unwired.status_code == 500
    assert plain.status_code == 201
