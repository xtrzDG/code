"""What the cabinet shows of the websites allowed to show a business's chat."""

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.business_limits import BusinessLimitsDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.widget_origins import WidgetAllowedOriginsView
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl

type AuthorizeAccess = UseCaseContract[BusinessAccessRequest, BusinessDocument]


def view_of(
    limits: BusinessLimitsDocument, platform_origins: list[PublicBaseUrl]
) -> WidgetAllowedOriginsView:
    return WidgetAllowedOriginsView(
        origins=list(limits.widget_allowed_origins),
        is_restricted=bool(limits.widget_allowed_origins),
        always_allowed=list(platform_origins),
    )
