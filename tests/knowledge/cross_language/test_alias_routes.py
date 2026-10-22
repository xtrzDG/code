"""
The editor's flow over HTTP: suggest translations, review them as chips
(accept, edit, add, remove) with PATCH, and find the item in Georgian.
"""

from typing import Any

from tests.knowledge.routes_fixture import OWNER, STAFF, STRANGER, build_fixture


def test_suggested_aliases_are_reviewed_in_the_editor_and_searched() -> None:
    fixture = build_fixture()
    client, base = fixture.client, fixture.base
    created: dict[str, Any] = client.post(
        f"{base}/knowledge",
        json={
            "kind": "faq",
            "title": "Do you have parking?",
            "body": "The city lot is next door.",
            "languages": ["en"],
        },
        headers=OWNER,
    ).json()
    assert created["aliases"] == []

    suggested = client.post(
        f"{base}/knowledge/{created['id']}/aliases/suggest", headers=STAFF
    )

    assert suggested.status_code == 200
    assert [
        (alias["language"], alias["text"], alias["status"])
        for alias in suggested.json()["aliases"]
    ] == [
        ("ka", "გაქვთ პარკინგი?", "suggested"),
        ("ru", "Есть ли парковка?", "suggested"),
    ]

    reviewed = client.patch(
        f"{base}/knowledge/{created['id']}",
        json={
            "aliases": [
                {"language": "ka", "text": "გაქვთ პარკინგი?", "status": "approved"},
                {"language": "ru", "text": "Парковка есть?", "status": "approved"},
                {"language": "ru", "text": "Где поставить машину?"},
            ]
        },
        headers=OWNER,
    )

    assert reviewed.status_code == 200
    assert [
        (alias["language"], alias["text"], alias["status"])
        for alias in reviewed.json()["aliases"]
    ] == [
        ("ka", "გაქვთ პარკინგი?", "approved"),
        ("ru", "Парковка есть?", "approved"),
        ("ru", "Где поставить машину?", "approved"),
    ]
    found = client.post(
        f"{base}/knowledge/search",
        json={"query": "პარკინგი გაქვთ?", "language": "ka"},
        headers=OWNER,
    ).json()
    assert found["items"][0]["title"] == "Do you have parking?"


def test_strangers_and_languages_the_business_does_not_use_are_refused() -> None:
    fixture = build_fixture()
    client, base = fixture.client, fixture.base
    item_id: str = client.post(
        f"{base}/knowledge",
        json={"kind": "faq", "title": "Do you have parking?", "body": "Yes."},
        headers=OWNER,
    ).json()["id"]

    stranger = client.post(
        f"{base}/knowledge/{item_id}/aliases/suggest", headers=STRANGER
    )
    hebrew = client.patch(
        f"{base}/knowledge/{item_id}",
        json={"aliases": [{"language": "he", "text": "יש חניה?"}]},
        headers=OWNER,
    )

    assert stranger.status_code == 404
    assert hebrew.status_code == 422
    assert fixture.harness.alias_suggester.requests == []
