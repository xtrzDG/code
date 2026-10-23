from typed_time_provider import Microseconds, WallClock

from app.contracts.meta_connection import (
    MetaConnectionStateRepoContract,
    MetaOAuthClientContract,
    MetaPagesClientContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.meta_connection import (
    MetaConnectionPurpose,
    MetaConnectionRefusal,
)
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.meta_connections import MetaConnectionStateDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels.meta_connection import (
    ListMetaPagesCommand,
    MetaPageList,
    MetaPageView,
)
from app.schemas.dto.channels.meta_provider import MetaAppCredentials, MetaPageChoice
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret
from app.schemas.typings.meta_connection.strings import MetaAccessToken
from app.use_cases.channels.meta_connection.meta_states import (
    hash_state,
    link_expired,
    meta_refusal,
    take_state,
)
from app.utilities.channels.meta_sign_in import meta_app_of


class ListMetaPagesUseCase(UseCaseContract[ListMetaPagesCommand, MetaPageList]):
    """
    The page picker after the owner signed in with Facebook: the sign-in
    must be this owner's page-picker sign-in in this business, open and
    unused (it is used up first); Meta's code becomes the owner's
    short-lived token, which lists the pages they manage, pages with a
    linked Instagram professional account first, then by name.

    The token is kept encrypted with the sign-in, usable until the sign-in
    ends (fifteen minutes) or a page is connected, which reads the chosen
    page's token with it and deletes the sign-in. An abandoned sign-in is
    deleted when the business's owner starts the next one, or else by the
    daily purge of stale rows (`PurgeStaleRowsUseCase`), its token with it:
    at most a day after it ended. Nothing about the pages is stored.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        state_repo: MetaConnectionStateRepoContract,
        oauth_client: MetaOAuthClientContract,
        pages_client: MetaPagesClientContract,
        secret_cipher: SecretCipherAdapterContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._state_repo: MetaConnectionStateRepoContract = state_repo
        self._oauth_client: MetaOAuthClientContract = oauth_client
        self._pages_client: MetaPagesClientContract = pages_client
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ListMetaPagesCommand) -> MetaPageList:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        app: MetaAppCredentials | None = meta_app_of(self._app_settings)
        if app is None:
            raise meta_refusal(
                MetaConnectionRefusal.NOT_CONFIGURED,
                "Facebook sign-in is not set up on this server.",
            )

        now: Microseconds = self._wall_clock.now_unix()
        state: MetaConnectionStateDocument = take_state(
            self._state_repo,
            business.id,
            input_data.user_id,
            input_data.request.state,
            MetaConnectionPurpose.PAGES,
            now,
        )
        token: MetaAccessToken = self._oauth_client.exchange_code(
            input_data.request.code, app
        )
        pages: list[MetaPageChoice] = self._pages_client.list_pages(token, app)
        sealed: EncryptedChannelSecret = self._secret_cipher.encrypt(
            ChannelSecret(str(token))
        )

        def keep_token(
            stored: MetaConnectionStateDocument,
        ) -> MetaConnectionStateDocument | None:
            return stored.model_copy(
                update={"encrypted_user_token": sealed, "updated_at": now}
            )

        if (
            self._state_repo.modify(
                business.id, hash_state(input_data.request.state), keep_token
            )
            is None
        ):
            raise link_expired()  # Started again meanwhile (the oldest went).

        return MetaPageList(
            pages=[page_view(page) for page in sorted(pages, key=picker_order)],
            expires_at=state.expires_at,
        )


def picker_order(page: MetaPageChoice) -> tuple[bool, str]:
    """Pages with an Instagram account first, then by name."""

    return (not page.has_instagram, str(page.name or page.page_id).casefold())


def page_view(page: MetaPageChoice) -> MetaPageView:
    return MetaPageView(
        page_id=page.page_id,
        name=page.name,
        username=page.username,
        has_instagram=page.has_instagram,
        instagram_account_id=page.instagram_account_id,
        instagram_username=page.instagram_username,
    )
