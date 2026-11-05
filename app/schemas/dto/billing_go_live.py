"""The free trial that starts when an assistant first goes live."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.billing import PlanKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.billing.booleans import IsTrialStartedAtGoLive


class GoLiveTrialRequest(ImmutableDTO):
    """A business is about to go live: start its trial if it is still due."""

    business: BusinessDocument


class GoLiveTrial(ImmutableDTO):
    """
    Whether the trial started now; when it did, the plan it runs on (the
    business takes it) and when it ends.
    """

    is_started: IsTrialStartedAtGoLive
    plan_key: PlanKey | None = None
    trial_ends_at: Microseconds | None = None
