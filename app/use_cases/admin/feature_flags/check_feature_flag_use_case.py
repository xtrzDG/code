from app.contracts.feature_flags import FeatureFlagGateContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.feature_flags import FeatureFlagDecision
from app.schemas.domain.users import UserDocument
from app.schemas.dto.feature_flags import FeatureFlagCheck, FeatureFlagCheckQuery
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.use_cases.admin.feature_flags.feature_flag_views import require_definition
from app.utilities.feature_flags.flag_evaluation import is_holding, rollout_bucket


class CheckFeatureFlagUseCase(UseCaseContract[FeatureFlagCheckQuery, FeatureFlagCheck]):
    """
    GET /v1/admin/feature-flags/{flag_name}/businesses/{business_id}, for
    admins who see operations: whether the flag holds for that business now,
    asked through the same gate the release's code asks at request time,
    why, and the business's bucket. The runbook's check after each rollout
    step (docs/operations/deploys.md, "Staged rollouts").

    Raises:
        NotFoundError: the registry lists no flag of that name.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        flag_gate: FeatureFlagGateContract,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._flag_gate: FeatureFlagGateContract = flag_gate

    def run(self, input_data: FeatureFlagCheckQuery) -> FeatureFlagCheck:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_OPERATIONS,
            )
        )
        require_definition(input_data.name)
        decision: FeatureFlagDecision = self._flag_gate.decide(
            input_data.name, input_data.business_id
        )
        return FeatureFlagCheck(
            name=input_data.name,
            business_id=input_data.business_id,
            is_on=is_holding(decision),
            decision=decision,
            bucket=rollout_bucket(input_data.name, input_data.business_id),
        )
