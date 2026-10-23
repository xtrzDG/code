import httpx

from app.clients.meta.graph_requests import graph_request
from app.clients.meta.meta_app_proof import appsecret_proof
from app.clients.meta.meta_grant_readers import (
    read_next_cursor,
    read_page_access_token,
    read_page_choice,
)
from app.clients.meta.meta_graph_client import (
    DEFAULT_GRAPH_API_VERSION,
    META_GRAPH_BASE_URL,
    REQUEST_TIMEOUT,
)
from app.contracts.meta_connection import MetaPagesClientContract
from app.schemas.dto.channels.meta_provider import MetaAppCredentials, MetaPageChoice
from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.meta_connection.strings import (
    MetaAccessToken,
    MetaPageAccessToken,
)
from app.utilities.channels.json_values import JsonObject, read_objects

# The page, its username and the Instagram professional account linked to it.
PAGE_CHOICE_FIELDS: str = "id,name,username,instagram_business_account{id,username}"
PAGES_PER_REQUEST: int = 100
# A person rarely manages more than a few pages; an agency's hundreds are
# read up to this many requests (1000 pages) and the rest left out.
MAX_PAGE_REQUESTS: int = 10


class MetaPagesClient(MetaPagesClientContract):
    """
    The pages a signed-in person manages (`GET /me/accounts`, page by page)
    and the token of one of them (`GET /{page-id}?fields=access_token`),
    with the person's token in the Authorization header and its
    `appsecret_proof`. A page token read with a long-lived person's token
    does not expire.
    """

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        api_version: str = DEFAULT_GRAPH_API_VERSION,
        base_url: str = META_GRAPH_BASE_URL,
    ) -> None:
        self._http_client: httpx.Client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/{api_version}",
            timeout=REQUEST_TIMEOUT,
            transport=transport,
        )

    def list_pages(
        self, user_token: MetaAccessToken, app: MetaAppCredentials
    ) -> list[MetaPageChoice]:
        pages: list[MetaPageChoice] = []
        cursor: str | None = None
        for _ in range(MAX_PAGE_REQUESTS):
            params: dict[str, str] = {
                "fields": PAGE_CHOICE_FIELDS,
                "limit": str(PAGES_PER_REQUEST),
                "appsecret_proof": appsecret_proof(str(user_token), app),
            }
            if cursor is not None:
                params["after"] = cursor

            body: JsonObject = graph_request(
                self._http_client,
                "GET",
                "/me/accounts",
                str(user_token),
                params=params,
                is_lookup=True,
            )
            pages.extend(
                choice
                for page in read_objects(body, "data")
                if (choice := read_page_choice(page)) is not None
            )
            cursor = read_next_cursor(body)
            if cursor is None:
                break

        return pages

    def read_page_token(
        self,
        user_token: MetaAccessToken,
        page_id: MetaObjectId,
        app: MetaAppCredentials,
    ) -> MetaPageAccessToken | None:
        return read_page_access_token(
            graph_request(
                self._http_client,
                "GET",
                f"/{page_id}",
                str(user_token),
                params={
                    "fields": "access_token",
                    "appsecret_proof": appsecret_proof(str(user_token), app),
                },
                is_lookup=True,
            )
        )
