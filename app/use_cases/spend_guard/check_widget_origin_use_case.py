from app.contracts.repositories.spend_guard_repositories import (
    BusinessLimitsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.widget_origins import WidgetOriginCheck
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.utilities.spend.widget_origins import is_origin_allowed


class CheckWidgetOriginUseCase(UseCaseContract[WidgetOriginCheck, None]):
    """
    Refuse a website-chat request (its config, messages, polls and "talk to
    a person") from a website the business did not allow, so nobody embeds
    another business's chat and spends its budget. A business without a
    list allows every website; the platform's own pages always pass, and so
    does a request that names no page (`widget_origins`).

    Raises:
        AccessDeniedError: the page's website is not on the business's list
            (403; the widget shows nothing there).
    """

    def __init__(
        self,
        business_limits_repo: BusinessLimitsRepoContract,
        platform_origins: list[PublicBaseUrl],
    ) -> None:
        self._limits_repo: BusinessLimitsRepoContract = business_limits_repo
        self._platform_origins: list[str] = [str(o) for o in platform_origins]

    def run(self, input_data: WidgetOriginCheck) -> None:
        limits = self._limits_repo.get_or_default(input_data.business_id)
        if is_origin_allowed(
            input_data.page_origin,
            limits.widget_allowed_origins,
            self._platform_origins,
        ):
            return

        raise AccessDeniedError("This chat is not available on this website.")
