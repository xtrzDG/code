"""
The admin's feature flags: everyone who sees operations lists them and
checks a business; only a SUPER admin after a step-up changes one, every
change is audited, a name outside the registry is unknown, a business
cannot be on both lists, and the gate reads a change at the next request.
"""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.feature_flags import FeatureFlagDecision
from app.schemas.dto.feature_flags import (
    FeatureFlagCheckQuery,
    FeatureFlagCommand,
    FeatureFlagListQuery,
    FeatureFlagRequest,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.feature_flags.constrained_integers import (
    FeatureFlagRolloutPercent,
)
from app.schemas.typings.feature_flags.constrained_strings import (
    FeatureFlagChangeReason,
    FeatureFlagName,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.feature_flags.feature_flag_catalog import RELEASE_CANARY
from tests.feature_flags.flag_world import FlagWorld
from tests.spend_guard.platform_pause_world import NOW

PILOT: BusinessId = BusinessId()


def command(
    admin: UserId,
    percent: int = 0,
    included: list[BusinessId] | None = None,
    excluded: list[BusinessId] | None = None,
    is_enabled: bool = True,
    name: FeatureFlagName = RELEASE_CANARY,
) -> FeatureFlagCommand:
    return FeatureFlagCommand(
        user_id=admin,
        name=name,
        request=FeatureFlagRequest(
            is_enabled=is_enabled,
            rollout_percent=FeatureFlagRolloutPercent(percent),
            included_business_ids=included or [],
            excluded_business_ids=excluded or [],
            reason=FeatureFlagChangeReason("Pilot business first"),
        ),
        client_ip_address=ClientIpAddress("203.0.113.7"),
    )


def check(world: FlagWorld, business: BusinessId) -> FeatureFlagDecision:
    return (
        world.check_use_case()
        .run(
            FeatureFlagCheckQuery(
                user_id=world.support, name=RELEASE_CANARY, business_id=business
            )
        )
        .decision
    )


def test_every_registry_flag_is_listed_off_until_first_set() -> None:
    world = FlagWorld()

    listed = world.list_use_case().run(FeatureFlagListQuery(user_id=world.support))

    assert [item.name for item in listed.items] == [RELEASE_CANARY]
    assert listed.items[0].is_enabled is False
    assert listed.items[0].changed_at is None
    assert check(world, PILOT) is FeatureFlagDecision.OFF


def test_a_super_admin_rolls_a_flag_out_and_the_change_is_audited() -> None:
    world = FlagWorld()

    view = world.set_use_case().run(command(world.super_admin, included=[PILOT]))

    assert view.is_enabled and view.included_business_ids == [PILOT]
    assert view.changed_by == world.super_admin and view.changed_at == NOW
    assert check(world, PILOT) is FeatureFlagDecision.INCLUDED
    assert check(world, BusinessId()) is FeatureFlagDecision.OUTSIDE_ROLLOUT
    (entry,) = world.audit_entries.list_all()
    assert entry.action is AuditAction.UPDATE
    assert (str(entry.entity), str(entry.entity_id)) == (
        "feature_flag",
        "release_canary",
    )
    assert str(entry.reason) == "Pilot business first"
    assert str(entry.ip_address) == "203.0.113.7"
    assert entry.business_id is None

    world.set_use_case().run(command(world.super_admin, percent=100, excluded=[PILOT]))

    assert check(world, PILOT) is FeatureFlagDecision.EXCLUDED
    assert check(world, BusinessId()) is FeatureFlagDecision.IN_ROLLOUT
    assert len(world.audit_entries.list_all()) == 2


def test_only_a_super_admin_after_a_step_up_changes_a_flag() -> None:
    world = FlagWorld()

    with pytest.raises(AccessDeniedError):
        world.set_use_case().run(command(world.support))

    world.step_up.is_recent = False
    with pytest.raises(StepUpRequiredError):
        world.set_use_case().run(command(world.super_admin))

    assert world.audit_entries.list_all() == []
    assert world.flags.get(RELEASE_CANARY) is None


def test_refusals_change_nothing() -> None:
    world = FlagWorld()
    world.set_use_case().run(command(world.super_admin, percent=5))

    with pytest.raises(ConflictError):
        world.set_use_case().run(command(world.super_admin, percent=5))
    with pytest.raises(ValidationFailedError):
        world.set_use_case().run(
            command(world.super_admin, included=[PILOT], excluded=[PILOT])
        )
    with pytest.raises(NotFoundError):
        world.set_use_case().run(
            command(world.super_admin, name=FeatureFlagName("not_registered"))
        )
    with pytest.raises(NotFoundError):
        world.check_use_case().run(
            FeatureFlagCheckQuery(
                user_id=world.support,
                name=FeatureFlagName("not_registered"),
                business_id=PILOT,
            )
        )

    assert len(world.audit_entries.list_all()) == 1


def test_checking_a_business_shows_its_bucket() -> None:
    world = FlagWorld()
    world.set_use_case().run(command(world.super_admin, percent=100))

    result = world.check_use_case().run(
        FeatureFlagCheckQuery(
            user_id=world.support, name=RELEASE_CANARY, business_id=PILOT
        )
    )

    assert result.is_on is True
    assert 0 <= int(result.bucket) <= 99
