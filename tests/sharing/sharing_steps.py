"""Steps of the sharing tests: an owner's business, its staff, a second business."""

from dataclasses import dataclass
from typing import Any

from tests.e2e.harness import Workshop, bearer

type JsonObject = dict[str, Any]


@dataclass(frozen=True)
class SharedBusiness:
    business_id: str
    owner: dict[str, str]

    @property
    def base(self) -> str:
        return f"/v1/businesses/{self.business_id}"


def create_business(workshop: Workshop, phone: str, name: str) -> SharedBusiness:
    token, _ = workshop.sign_in_with_phone(phone)
    created = workshop.client.post(
        "/v1/businesses",
        json={"name": name, "niche_key": "restaurant"},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    return SharedBusiness(str(created.json()["id"]), bearer(token))


def add_staff(
    workshop: Workshop, business: SharedBusiness, phone: str
) -> dict[str, str]:
    invited = workshop.client.post(
        f"{business.base}/members",
        json={"phone_number": phone, "role": "staff"},
        headers=business.owner,
    )
    assert invited.status_code == 201, invited.text
    return bearer(workshop.sign_in_with_phone(phone)[0])


def share_links(
    workshop: Workshop,
    business: SharedBusiness,
    headers: dict[str, str] | None = None,
    source: str | None = None,
) -> JsonObject:
    response = workshop.client.get(
        f"{business.base}/share-links",
        params={} if source is None else {"src": source},
        headers=headers or business.owner,
    )
    assert response.status_code == 200, response.text
    body: JsonObject = response.json()
    return body


def set_slug(workshop: Workshop, business: SharedBusiness, slug: str) -> Any:
    return workshop.client.put(
        f"{business.base}/public-slug", json={"slug": slug}, headers=business.owner
    )
