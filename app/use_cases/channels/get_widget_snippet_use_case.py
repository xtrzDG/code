import html
from urllib.parse import urlencode

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels.widget import WidgetSnippetQuery, WidgetSnippetView
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import (
    WidgetDemoUrl,
    WidgetScriptUrl,
)
from app.schemas.typings.channels.strings import WidgetEmbedSnippet
from app.utilities.channels.channel_endpoints import (
    DEMO_BUSINESS_PARAMETER,
    WIDGET_BUSINESS_ATTRIBUTE,
    WIDGET_DEMO_PATH,
    WIDGET_SCRIPT_PATH,
    join_public_url,
)


class GetWidgetSnippetUseCase(UseCaseContract[WidgetSnippetQuery, WidgetSnippetView]):
    """
    Embed code of the website chat widget (concept section 6):
    <script src="<APP_BASE_URL>/widget.js" data-tenant="<business id>" async>,
    and the address of the page that previews it. Owners and staff may read
    them.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        app_settings: AppSettings,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: WidgetSnippetQuery) -> WidgetSnippetView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        base_url = self._app_settings.app_base_url
        if base_url is None:
            raise ExternalServiceError(
                "The widget code needs APP_BASE_URL, which is not configured."
            )

        script_url = WidgetScriptUrl(join_public_url(str(base_url), WIDGET_SCRIPT_PATH))
        escaped_business_id: str = html.escape(str(business.id), quote=True)
        snippet: str = (
            f'<script src="{html.escape(str(script_url), quote=True)}" '
            f'{WIDGET_BUSINESS_ATTRIBUTE}="{escaped_business_id}" '
            "async></script>"
        )
        demo_url = WidgetDemoUrl(
            join_public_url(str(base_url), WIDGET_DEMO_PATH)
            + "?"
            + urlencode({DEMO_BUSINESS_PARAMETER: str(business.id)})
        )
        return WidgetSnippetView(
            business_id=business.id,
            script_url=script_url,
            snippet=WidgetEmbedSnippet(snippet),
            demo_url=demo_url,
        )
