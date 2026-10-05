"""
GET /v1/legal/subprocessors and GET /v1/legal/{terms|privacy|cookies}:
public, in the language asked for (else its base language, else English),
the version in force by the day, a later version announced ahead.
"""

from pathlib import Path

from app.registries.legal.subprocessor_catalog import SUBPROCESSORS
from tests.legal.legal_http import build_legal_client
from tests.legal.legal_world import Clock, announced_entry, retiring_entry


def test_the_sub_processor_list_in_the_language_asked_for() -> None:
    client = build_legal_client(Clock("2026-10-06"))

    english = client.get("/v1/legal/subprocessors")
    russian = client.get("/v1/legal/subprocessors", params={"language": "ru-RU"})
    georgian = client.get(
        "/v1/legal/subprocessors", headers={"Accept-Language": "ka,en;q=0.5"}
    )

    assert english.status_code == 200
    assert english.headers["cache-control"] == "public, max-age=300"
    body = english.json()
    assert body["language"] == "en"
    assert body["as_of"] == "2026-10-06"
    assert body["notice_days"] == 30
    assert [item["key"] for item in body["subprocessors"]][:2] == [
        "openai",
        "elevenlabs",
    ]
    assert body["subprocessors"][0] == {
        "key": "openai",
        "name": "OpenAI (EU data residency project)",
        "purpose": "Language model that writes the assistant's replies",
        "personal_data": "Messages, the Client's knowledge, booking details",
        "location": "EU (data residency)",
        "added_on": "2026-10-01",
        "removed_on": None,
        "is_in_force": True,
    }
    assert body["upcoming_changes"] == []
    assert russian.json()["language"] == "ru"
    assert russian.json()["subprocessors"][0]["purpose"].startswith("Языковая модель")
    assert georgian.json()["language"] == "ka"


def test_announced_changes_show_when_owners_hear_of_them() -> None:
    entries = (
        retiring_entry(removed_on="2027-01-01", announced_on="2026-11-15"),
        *SUBPROCESSORS[1:],
        announced_entry("mailbox", added_on="2026-12-01", announced_on="2026-10-20"),
    )
    client = build_legal_client(Clock("2026-10-25"), entries=entries)

    body = client.get("/v1/legal/subprocessors", params={"language": "de"}).json()

    assert body["language"] == "en"
    mailbox = next(item for item in body["subprocessors"] if item["key"] == "mailbox")
    assert mailbox["is_in_force"] is False
    assert [
        (change["key"], change["kind"], change["name"], change["notice_from"])
        for change in body["upcoming_changes"]
    ] == [
        ("mailbox-added-2026-12-01", "added", "Mailbox EU", "2026-11-01"),
        (
            "openai-removed-2027-01-01",
            "removed",
            "OpenAI (EU data residency project)",
            "2026-12-02",
        ),
    ]


def test_a_sub_processor_that_left_is_gone_from_the_list() -> None:
    entries = (
        retiring_entry(removed_on="2027-01-01", announced_on="2026-11-15"),
        *SUBPROCESSORS[1:],
    )
    client = build_legal_client(Clock("2027-01-01"), entries=entries)

    body = client.get("/v1/legal/subprocessors").json()

    assert "openai" not in {item["key"] for item in body["subprocessors"]}
    assert body["upcoming_changes"] == []


def test_the_terms_in_force_in_three_languages() -> None:
    client = build_legal_client(Clock("2026-10-05"))

    terms = client.get("/v1/legal/terms", params={"language": "ru"})
    privacy = client.get("/v1/legal/privacy", headers={"Accept-Language": "ka"})
    cookies = client.get("/v1/legal/cookies", params={"language": "fr"})

    assert terms.status_code == 200
    body = terms.json()
    assert body["kind"] == "terms"
    assert body["version"] == "2026-10-05"
    assert body["language"] == "ru"
    assert body["available_languages"] == ["en", "ka", "ru"]
    assert body["title"] == "Условия использования"
    assert body["text"].startswith("# Условия использования")
    assert body["has_placeholders"] is True
    assert body["upcoming_version"] is None
    assert privacy.json()["title"] == "კონფიდენციალურობის პოლიტიკა"
    assert cookies.json()["language"] == "en"
    assert cookies.json()["title"] == "Cookie Statement"


def test_no_text_before_the_first_version_and_unknown_documents() -> None:
    client = build_legal_client(Clock("2026-10-04"))

    assert client.get("/v1/legal/terms").status_code == 404
    assert client.get("/v1/legal/refunds").status_code == 404
    assert (
        client.get("/v1/legal/terms", params={"version": "2030-01-01"}).status_code
        == 404
    )
    assert client.get("/v1/legal/terms", params={"version": "soon"}).status_code == 422
    assert client.get("/v1/legal/terms", params={"language": "!!"}).status_code == 422


def test_a_published_later_version_is_announced_and_readable(tmp_path: Path) -> None:
    (tmp_path / "terms-2026-10-05.en.md").write_text("# Terms\n\nOld.", "utf-8")
    (tmp_path / "terms-2026-12-01.en.md").write_text(
        "# Terms\n\nNew, see [the help](https://example.com).", "utf-8"
    )
    client = build_legal_client(Clock("2026-11-10"), documents=tmp_path)

    current = client.get("/v1/legal/terms").json()
    ahead = client.get("/v1/legal/terms", params={"version": "2026-12-01"}).json()
    later = build_legal_client(Clock("2026-12-01"), documents=tmp_path)

    assert current["version"] == "2026-10-05"
    assert current["upcoming_version"] == "2026-12-01"
    assert current["has_placeholders"] is False
    assert ahead["text"].startswith("# Terms\n\nNew")
    # A Markdown link is not a field to fill.
    assert ahead["has_placeholders"] is False
    assert ahead["upcoming_version"] is None
    assert later.get("/v1/legal/terms").json()["version"] == "2026-12-01"
