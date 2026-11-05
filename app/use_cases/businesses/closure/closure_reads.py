"""What the closure's use cases read about a business besides its closure."""

from typed_time_provider import Microseconds

from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.business_closures.booleans import IsViewerBusinessOwner
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.billing_records import (
    find_current_subscription,
    is_service_paid_for,
)
from app.use_cases.shared.brand_reach import acting_role


def is_owner_of(
    brand_repo: BrandRepoContract, business: BusinessDocument, user_id: UserId
) -> IsViewerBusinessOwner:
    """An owner of the business, or of its brand (who acts as its owner)."""

    return acting_role(brand_repo, business, user_id) is BusinessMemberRole.OWNER


def is_paid_for(
    subscription_repo: SubscriptionRepoContract,
    business: BusinessDocument,
    now: Microseconds,
) -> bool:
    """The business is entitled to the service again (paid, trial, grace)."""

    return is_service_paid_for(
        find_current_subscription(subscription_repo, business.id), now
    )
