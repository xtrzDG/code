"""Steps of the business settings tests: a Georgian restaurant and its updates."""

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.businesses import (
    BusinessSettingsChanges,
    BusinessView,
    ManagerContactInput,
    UpdateBusinessSettingsCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import RawManagerContactAddress
from app.schemas.typings.handoffs.strings import ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from tests.users.accounts_phones import GEORGIA_MOBILE
from tests.users.accounts_testbed import AccountsTestbed


def georgian_restaurant(testbed: AccountsTestbed) -> tuple[UserId, BusinessDocument]:
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    return owner.user.id, testbed.create_restaurant(owner.user.id, "Sakhli")


def update(
    testbed: AccountsTestbed,
    user_id: UserId,
    business_id: BusinessId,
    changes: BusinessSettingsChanges,
) -> BusinessView:
    return testbed.update_business_settings.run(
        UpdateBusinessSettingsCommand(
            user_id=user_id,
            business_id=business_id,
            changes=changes,
        )
    )


def contact(
    channel: ManagerContactChannel,
    address: str,
    language: str | None = None,
) -> ManagerContactInput:
    return ManagerContactInput(
        name=ManagerName("Nino"),
        channel=channel,
        address=RawManagerContactAddress(address),
        language=None if language is None else LanguageTag(language),
    )
