from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels.meta_connection import (
    MetaSignInOptionsQuery,
    MetaSignInOptionsView,
)
from app.schemas.dto.channels.meta_provider import MetaAppCredentials
from app.utilities.channels.meta_sign_in import META_GRAPH_API_VERSION, meta_app_of


class GetMetaSignInOptionsUseCase(
    UseCaseContract[MetaSignInOptionsQuery, MetaSignInOptionsView]
):
    """
    Which Facebook sign-ins the Channels page offers (any member reads it;
    only owners connect): the page picker of Messenger and Instagram needs
    the platform's Meta app (META_APP_ID, META_APP_SECRET); WhatsApp
    Embedded Signup also its configuration (META_EMBEDDED_SIGNUP_CONFIG_ID).
    Without them the cabinet shows the manual fields alone.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        app_settings: AppSettings,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: MetaSignInOptionsQuery) -> MetaSignInOptionsView:
        self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        app: MetaAppCredentials | None = meta_app_of(self._app_settings)
        if app is None:
            return MetaSignInOptionsView(whatsapp=False, pages=False)

        return MetaSignInOptionsView(
            whatsapp=self._app_settings.meta_embedded_signup_config_id is not None,
            pages=True,
            app_id=app.app_id,
            graph_api_version=META_GRAPH_API_VERSION,
        )
