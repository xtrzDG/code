"""
Brand access never widens what a member sees: a brand owner owns the
brand's locations, a regional manager is staff in the locations assigned
to them only, and nobody reaches a business that left the brand.
"""

from app.schemas.constants.users import BusinessMemberRole
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.brands.brand_access import (
    brand_grant,
    direct_role,
    effective_role,
    visible_location_ids,
)
from app.utilities.brands.brand_locations import (
    first_location_id,
    is_further_location,
)
from tests.brands.brand_builders import build_brand, build_location

OWNER = UserId()
MANAGER = UserId()
STRANGER = UserId()


def test_a_brand_owner_owns_every_location_of_the_brand() -> None:
    brand = build_brand(OWNER)
    location = build_location(brand, UserId())

    assert brand_grant(brand, location, OWNER) is BusinessMemberRole.OWNER


def test_a_regional_manager_is_staff_only_where_assigned() -> None:
    first = build_location(None, UserId())
    second = build_location(None, UserId())
    brand = build_brand(OWNER, {MANAGER: [first.id]})
    assigned = first.model_copy(update={"brand_id": brand.id})
    other = second.model_copy(update={"brand_id": brand.id})

    assert brand_grant(brand, assigned, MANAGER) is BusinessMemberRole.STAFF
    assert brand_grant(brand, other, MANAGER) is None
    assert visible_location_ids(brand, MANAGER, [assigned.id, other.id]) == [
        assigned.id
    ]


def test_nobody_reaches_a_business_outside_the_brand() -> None:
    location = build_location(None, UserId())
    brand = build_brand(OWNER, {MANAGER: [location.id]})

    # Assigned once, but the business no longer names the brand.
    assert brand_grant(brand, location, OWNER) is None
    assert brand_grant(brand, location, MANAGER) is None


def test_strangers_get_nothing_from_a_brand() -> None:
    brand = build_brand(OWNER)
    location = build_location(brand, UserId())

    assert brand_grant(brand, location, STRANGER) is None
    assert visible_location_ids(brand, STRANGER, [location.id]) == []


def test_a_brand_owner_outranks_a_staff_seat_but_a_manager_never_does() -> None:
    assert (
        effective_role(BusinessMemberRole.STAFF, BusinessMemberRole.OWNER)
        is BusinessMemberRole.OWNER
    )
    # A location's own owner stays owner when the brand makes them staff.
    assert (
        effective_role(BusinessMemberRole.OWNER, BusinessMemberRole.STAFF)
        is BusinessMemberRole.OWNER
    )
    assert effective_role(None, BusinessMemberRole.STAFF) is BusinessMemberRole.STAFF
    assert effective_role(None, None) is None


def test_the_own_team_role_is_read_from_the_business() -> None:
    location = build_location(None, OWNER)

    assert direct_role(location, OWNER) is BusinessMemberRole.OWNER
    assert direct_role(location, STRANGER) is None


def test_the_oldest_location_is_the_first_and_the_others_are_further() -> None:
    brand = build_brand(OWNER)
    first = build_location(brand, OWNER, created_at=10)
    later = build_location(brand, OWNER, created_at=20)
    outside = build_location(None, OWNER, created_at=5)
    locations = [later, first]

    assert first_location_id(locations) == first.id
    assert is_further_location(first, locations) is False
    assert is_further_location(later, locations) is True
    assert is_further_location(outside, locations) is False
    assert is_further_location(first, [first]) is False
