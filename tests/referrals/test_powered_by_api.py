"""
The "Powered by" link with the business's code: on the widget, the hosted
page and the printed card; only a Plus business may take it off.
"""

from httpx2 import Response

from tests.e2e.harness import Workshop
from tests.referrals.referral_workshop import (
    CABINET_BASE_URL,
    Owner,
    open_business,
    program,
    sign_up,
)

OWNER_PHONE: str = "+995 555 12 34 56"


def powered_by(workshop: Workshop, owner: Owner, is_hidden: bool) -> Response:
    return workshop.client.put(
        f"{owner.base}/referrals/powered-by",
        json={"is_hidden": is_hidden},
        headers=owner.headers,
    )


def share_links(workshop: Workshop, owner: Owner) -> dict[str, object]:
    response = workshop.client.get(f"{owner.base}/share-links", headers=owner.headers)
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def test_every_business_shows_the_link_with_its_code(workshop: Workshop) -> None:
    owner = open_business(workshop, OWNER_PHONE)

    view = program(workshop, owner)

    code = view["code"]
    assert view["powered_by"] == {
        "is_shown": True,
        "is_removable": False,
        "is_hidden": False,
        "url": f"{CABINET_BASE_URL}/?ref={code}&src=powered_by",
    }
    assert share_links(workshop, owner)["powered_by_url"] == (
        f"{CABINET_BASE_URL}/?ref={code}&src=table_card"
    )
    hosted = workshop.client.get(f"/v1/public/chat/{owner.business_id}")
    assert hosted.status_code == 200, hosted.text
    assert hosted.json()["powered_by_url"] == view["powered_by"]["url"]


def test_only_a_plus_business_may_take_the_link_off(workshop: Workshop) -> None:
    owner = open_business(workshop, OWNER_PHONE)

    refused = powered_by(workshop, owner, is_hidden=True)

    assert refused.status_code == 409
    body: dict[str, list[dict[str, str]]] = refused.json()
    assert [reason["code"] for reason in body["reasons"]] == ["plan_required"]
    assert program(workshop, owner)["powered_by"]["is_shown"] is True


def test_the_powered_by_link_disappears_on_plus(workshop: Workshop) -> None:
    hotel = open_business(workshop, OWNER_PHONE, plan_key="plus")
    assert program(workshop, hotel)["powered_by"]["is_removable"] is True

    hidden = powered_by(workshop, hotel, is_hidden=True)

    assert hidden.status_code == 200, hidden.text
    assert hidden.json() == {
        "is_shown": False,
        "is_removable": True,
        "is_hidden": True,
        "url": None,
    }
    assert share_links(workshop, hotel)["powered_by_url"] is None
    hosted = workshop.client.get(f"/v1/public/chat/{hotel.business_id}")
    assert hosted.json()["powered_by_url"] is None

    shown = powered_by(workshop, hotel, is_hidden=False)

    assert shown.json()["is_shown"] is True
    assert share_links(workshop, hotel)["powered_by_url"] is not None


def test_staff_cannot_take_the_link_off(workshop: Workshop) -> None:
    hotel = open_business(workshop, OWNER_PHONE, plan_key="plus")
    invited = workshop.client.post(
        f"{hotel.base}/members",
        json={"phone_number": "+995 555 11 22 33", "role": "staff"},
        headers=hotel.headers,
    )
    assert invited.status_code == 201, invited.text
    staff, _ = sign_up(workshop, "+995 555 11 22 33")
    response = workshop.client.put(
        f"{hotel.base}/referrals/powered-by", json={"is_hidden": True}, headers=staff
    )

    assert response.status_code == 403


def test_the_widget_footer_gets_the_link(workshop: Workshop) -> None:
    owner = open_business(workshop, OWNER_PHONE)
    code = program(workshop, owner)["code"]

    config = workshop.client.get(f"/v1/widget/{owner.business_id}/config")

    assert config.status_code == 200, config.text
    assert config.json()["powered_by_url"] == (
        f"{CABINET_BASE_URL}/?ref={code}&src=powered_by"
    )
