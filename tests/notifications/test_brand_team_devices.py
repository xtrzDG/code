"""
The devices of a brand's team hear the alerts of the locations they work
in, with the role the brand gives them there; once off the brand (or the
location out of it), their devices are forgotten like any former member's.
"""

from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.handoffs import HandoffUrgency
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.brands import BrandDocument, BrandMember
from app.schemas.dto.notifications.staff_alerts import StaffAlert
from app.schemas.typings.brands.strings import BrandName
from app.schemas.typings.users.prefixed_id import UserId
from tests.notifications.alert_world import AlertWorld
from tests.notifications.test_staff_alert_facilitator import handoff, texts


def brand_world() -> tuple[AlertWorld, UserId, UserId]:
    """The world's business as a location of a brand with an owner and a
    regional manager of the location, neither of them on its own team."""

    world = AlertWorld()
    brand_owner, manager = UserId(), UserId()
    brand = BrandDocument(
        name=BrandName("Salobie Bia"),
        members=[
            BrandMember(user_id=brand_owner, role=BrandMemberRole.BRAND_OWNER),
            BrandMember(
                user_id=manager,
                role=BrandMemberRole.REGIONAL_MANAGER,
                business_ids=[world.business.id],
            ),
        ],
    )
    world.brands.add(brand)
    world.business = world.business.model_copy(update={"brand_id": brand.id})
    return world, brand_owner, manager


def pushed_users(world: AlertWorld) -> set[UserId]:
    return {item.user_id for item in world.push_queue.queued}


def test_the_brand_teams_devices_hear_the_locations_alerts() -> None:
    world, brand_owner, manager = brand_world()
    owner_phone = world.add_device(brand_owner, "en")
    manager_phone = world.add_device(manager, "ka")

    world.alerts.alert(world.business, handoff(world, HandoffUrgency.HIGH), texts())

    assert pushed_users(world) == {brand_owner, manager}
    assert world.subscriptions.get(world.business.id, owner_phone.id) is not None
    assert world.subscriptions.get(world.business.id, manager_phone.id) is not None


def test_an_owners_alert_reaches_the_brand_owner_not_the_manager() -> None:
    world, brand_owner, manager = brand_world()
    world.add_device(brand_owner, "en")
    world.add_device(manager, "ka")
    for_owners: StaffAlert = handoff(world, HandoffUrgency.HIGH).model_copy(
        update={"member_roles": [BusinessMemberRole.OWNER]}
    )

    world.alerts.alert(world.business, for_owners, texts())

    assert pushed_users(world) == {brand_owner}


def test_devices_of_a_location_out_of_the_brand_are_forgotten() -> None:
    world, brand_owner, _ = brand_world()
    phone = world.add_device(brand_owner, "en")
    world.business = world.business.model_copy(update={"brand_id": None})

    world.alerts.alert(world.business, handoff(world, HandoffUrgency.HIGH), texts())

    assert brand_owner not in pushed_users(world)
    assert world.subscriptions.get(world.business.id, phone.id) is None
