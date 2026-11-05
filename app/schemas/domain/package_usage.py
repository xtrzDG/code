from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.billing import PackageMetric
from app.schemas.typings.billing.constrained_integers import PackageUsagePercent
from app.schemas.typings.billing.prefixed_id import (
    PackageUsageWarningId,
    SubscriptionId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId


class PackageUsageWarningDocument(BaseDocument):
    """
    Record that the owners were warned about one package metric in one
    billing period (concept: a warning at 80 % of the package, once).
    """

    id: PackageUsageWarningId = Field(default_factory=PackageUsageWarningId)
    business_id: BusinessId
    subscription_id: SubscriptionId
    metric: PackageMetric
    period_start: Microseconds
    usage_percent: PackageUsagePercent
