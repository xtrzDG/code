"""
A location's two-factor rule for its team (`require_mfa_for_members`)
against the brand's operations, shared by the in-memory matrix
(tests/platform/test_brand_authorization_matrix.py) and its Postgres run:

- a business that requires two factors joins a brand (a new brand, or
  added as a location) only from a session signed in with two factors;
- once one location of the brand requires two factors, a brand owner
  signed in with the login code alone is refused every owner's operation
  of the brand (403, reason `mfa_required`) without changing the store: the
  shared answers that location's assistant reads, the team that reaches
  it, the locations, the name; a regional manager still gets 403
  `access_denied` on them;
- the brand stays readable, and the dashboard shows that location locked;
- with an authenticator set up, the same person is let through.
"""

from httpx2 import Response

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.platform.authorization_checks import Expectation, expect_error
from tests.platform.authorization_world import Headers
from tests.platform.brand_matrix_checks import BRAND_OWNER_ONLY, check_brand_refusals
from tests.platform.brand_matrix_world import CO_OWNER_PHONE, SHARED_KEY, BrandWorld
from tests.users.mfa.mfa_api import reason_codes, set_up_authenticator


def expect_mfa_required() -> Expectation:
    """403 with the one reason `mfa_required`, else what went wrong."""

    def check(response: Response) -> str | None:
        if response.status_code == 403 and reason_codes(response) == ["mfa_required"]:
            return None

        got: str = f"{response.status_code} {response.text[:160]}"
        return f"expected 403 mfa_required, got {got}"

    return check


def require_two_factors_of_team(brand: BrandWorld, business_id: str) -> None:
    """The location's owners turn the rule on (stored as the settings would)."""

    def turn_on(current: BusinessDocument) -> None:
        current.require_mfa_for_members = True

    repo = brand.world.workshop.container.repositories.business_repo()
    with brand.world.storage_scope.scoped_to_business(BusinessId(business_id)):
        repo.update(BusinessId(business_id), turn_on)


def problem_of(label: str, response: Response, expectation: Expectation) -> list[str]:
    problem: str | None = expectation(response)
    return [] if problem is None else [f"{label}: {problem}"]


def check_joining_a_brand_needs_two_factors(brand: BrandWorld) -> list[str]:
    """D requires two factors: its owner's one-factor session cannot bring it in."""

    client, owner = brand.world.workshop.client, brand.world.owner_b
    require_two_factors_of_team(brand, brand.outside_d)
    created = client.post(
        "/v1/brands",
        json={"name": "Mtsvane Ezo Batumi", "business_id": brand.outside_d},
        headers=owner,
    )
    added = client.post(
        f"/v1/brands/{brand.brand_id}/locations",
        json={"business_id": brand.outside_d},
        headers=owner,
    )
    brands_with_d = [
        str(item["name"])
        for item in client.get("/v1/brands", headers=owner).json()
        if brand.outside_d
        in {str(location["business_id"]) for location in item["locations"]}
    ]
    return (
        problem_of("new brand from D", created, expect_mfa_required())
        + problem_of("D added to the brand", added, expect_mfa_required())
        + ([f"D joined a brand: {brands_with_d}"] if brands_with_d else [])
    )


def check_brand_owner_actions_need_two_factors(brand: BrandWorld) -> list[str]:
    """C requires two factors: the brand's owners' operations follow C's rule."""

    client, co_owner = brand.world.workshop.client, brand.co_owner
    require_two_factors_of_team(brand, brand.location_c)
    failures: list[str] = check_brand_refusals(
        brand, co_owner, expect_mfa_required(), BRAND_OWNER_ONLY
    ) + check_brand_refusals(
        brand, brand.manager, expect_error(403, "access_denied"), BRAND_OWNER_ONLY
    )
    base = f"/v1/brands/{brand.brand_id}"
    read = client.get(base, headers=co_owner)
    dashboard = client.get(f"{base}/dashboard", headers=co_owner)
    locked = {
        str(row["location"]["business_id"]): bool(row["is_locked"])
        for row in dashboard.json()["locations"]
    }
    failures += [] if read.status_code == 200 else [f"brand read: {read.text[:160]}"]
    if locked.get(brand.location_c) is not True or locked.get(brand.world.business_b):
        failures.append(f"dashboard should lock C only: {locked}")

    set_up_authenticator(brand.world.workshop, token_of(co_owner), CO_OWNER_PHONE)
    changed = client.put(
        f"{base}/knowledge/{SHARED_KEY}",
        json={"kind": "faq", "title": "Parking", "body": "Free after 18:00."},
        headers=co_owner,
    )
    return failures + problem_of("with two factors", changed, expect_status(200))


def expect_status(status_code: int) -> Expectation:
    def check(response: Response) -> str | None:
        if response.status_code == status_code:
            return None

        return (
            f"expected {status_code}, got {response.status_code} {response.text[:160]}"
        )

    return check


def token_of(headers: Headers) -> str:
    return headers["Authorization"].removeprefix("Bearer ")
