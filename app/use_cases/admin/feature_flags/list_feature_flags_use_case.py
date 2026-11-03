from app.contracts.feature_flags import FeatureFlagRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.feature_flags import FeatureFlagDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.feature_flags import FeatureFlagList, FeatureFlagListQuery
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.use_cases.admin.feature_flags.feature_flag_views import build_flag_view
from app.utilities.feature_flags.feature_flag_catalog import FEATURE_FLAGS


class ListFeatureFlagsUseCase(UseCaseContract[FeatureFlagListQuery, FeatureFlagList]):
    """
    GET /v1/admin/feature-flags, for admins who see operations: every flag
    of the registry with its state (off until first set), read by the
    registry's names in one keyed read.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        flag_repo: FeatureFlagRepoContract,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._flag_repo: FeatureFlagRepoContract = flag_repo

    def run(self, input_data: FeatureFlagListQuery) -> FeatureFlagList:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_OPERATIONS,
            )
        )
        stored: dict[str, FeatureFlagDocument] = {
            str(flag.name): flag
            for flag in self._flag_repo.get_many(
                [definition.name for definition in FEATURE_FLAGS]
            )
        }
        return FeatureFlagList(
            items=[
                build_flag_view(definition, stored.get(str(definition.name)))
                for definition in FEATURE_FLAGS
            ]
        )
