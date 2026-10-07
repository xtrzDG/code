"""
ETag and If-Match of the business settings: GET and PATCH answer the
revision as a strong entity tag, a PATCH whose If-Match names another
revision (or that races another save) is refused with 412 and changes
nothing, and `*`, a list naming the current tag or no header at all apply.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.businesses.strings import CityName
from tests.businesses.test_business_routes import create_business, signed_in
from tests.users.accounts_phones import GEORGIA_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed

type JsonObject = dict[str, Any]


class SettingsPage:
    def __init__(self) -> None:
        self.testbed: AccountsTestbed = build_accounts_testbed()
        self.client: TestClient = self.testbed.build_http_client()
        self.owner: dict[str, str] = signed_in(self.testbed, GEORGIA_MOBILE)
        self.business: JsonObject = create_business(self.client, self.owner)
        self.path: str = f"/v1/businesses/{self.business['id']}"

    def read(self) -> tuple[str, JsonObject]:
        answer = self.client.get(self.path, headers=self.owner)
        assert answer.status_code == 200
        body: JsonObject = answer.json()
        return answer.headers["etag"], body

    def change(self, body: JsonObject, if_match: str | None = None) -> Any:
        headers = dict(self.owner)
        if if_match is not None:
            headers["If-Match"] = if_match
        return self.client.patch(self.path, headers=headers, json=body)


def tag(revision: int) -> str:
    return f'"{revision}"'


def test_get_and_patch_answer_the_revision_as_etag() -> None:
    page = SettingsPage()
    etag, business = page.read()

    changed = page.change({"city": "Batumi"}, if_match=etag)

    assert etag == tag(business["revision"])
    assert changed.status_code == 200
    assert changed.headers["etag"] == tag(changed.json()["revision"])
    assert changed.json()["revision"] == business["revision"] + 1
    assert page.read()[0] == changed.headers["etag"]


def test_an_if_match_of_an_older_revision_is_refused_with_412() -> None:
    page = SettingsPage()
    opened, _ = page.read()
    saved = page.change({"city": "Batumi"}, if_match=opened)

    stale = page.change({"name": "Old tab"}, if_match=opened)

    assert stale.status_code == 412
    body: JsonObject = stale.json()
    assert body["error"] == "conflict"
    [reason] = body["reasons"]
    assert reason["code"] == "precondition_failed"
    assert reason["details"] == [str(saved.json()["revision"])]
    _, stored = page.read()
    assert (stored["name"], stored["city"]) == ("Funicular VR", "Batumi")


@pytest.mark.parametrize(
    "if_match",
    [
        "*",
        '"0", {current}',
        "{current}",
    ],
)
def test_any_tag_or_a_list_naming_the_current_one_applies(if_match: str) -> None:
    page = SettingsPage()
    current, _ = page.read()

    changed = page.change(
        {"city": "Kutaisi"}, if_match=if_match.format(current=current)
    )

    assert changed.status_code == 200
    assert changed.json()["city"] == "Kutaisi"


@pytest.mark.parametrize("if_match", ['W/"{revision}"', "{revision}", '"abc"', ""])
def test_weak_unquoted_or_foreign_tags_never_match(if_match: str) -> None:
    page = SettingsPage()
    _, business = page.read()

    refused = page.change(
        {"city": "Kutaisi"}, if_match=if_match.format(revision=business["revision"])
    )

    assert refused.status_code == 412
    assert page.read()[1]["city"] == "Tbilisi"


def test_without_if_match_the_body_revision_still_answers_409() -> None:
    page = SettingsPage()
    _, business = page.read()
    page.change({"city": "Batumi"})

    stale = page.change({"name": "Old tab", "expected_revision": business["revision"]})

    assert stale.status_code == 409
    assert stale.json()["reasons"][0]["code"] == "stale_revision"


def test_a_save_between_reading_and_writing_fails_the_precondition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = SettingsPage()
    etag, business = page.read()
    repo = page.testbed.business_repo
    save_if_unchanged = repo.save_if_unchanged

    def save_after_another_request(document: BusinessDocument) -> bool:
        meanwhile = repo.get(document.id)
        assert meanwhile is not None
        meanwhile.city = CityName("Kutaisi")
        repo.save(meanwhile)
        return save_if_unchanged(document)

    monkeypatch.setattr(repo, "save_if_unchanged", save_after_another_request)

    raced = page.change({"name": "Lost update"}, if_match=etag)

    assert raced.status_code == 412
    assert raced.json()["reasons"][0]["code"] == "precondition_failed"
    monkeypatch.undo()
    _, stored = page.read()
    assert (stored["name"], stored["city"]) == ("Funicular VR", "Kutaisi")
    assert stored["revision"] == business["revision"] + 1


def test_the_api_description_documents_etag_and_if_match() -> None:
    page = SettingsPage()
    description: JsonObject = page.client.get("/openapi.json").json()
    operations: JsonObject = description["paths"]["/v1/businesses/{business_id}"]

    for method in ("get", "patch"):
        assert "ETag" in operations[method]["responses"]["200"]["headers"]
    headers = [
        parameter["name"]
        for parameter in operations["patch"]["parameters"]
        if parameter["in"] == "header"
    ]
    assert "If-Match" in headers
    assert "412" in operations["patch"]["responses"]
