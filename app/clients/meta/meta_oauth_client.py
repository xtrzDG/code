import httpx

from app.clients.meta.graph_api_client import GraphApiClient
from app.clients.meta.meta_grant_readers import read_access_token, read_token_grants
from app.clients.meta.meta_graph_errors import build_graph_error
from app.contracts.meta_connection import MetaOAuthClientContract
from app.schemas.dto.channels.meta_provider import MetaAppCredentials, MetaTokenGrants
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaEmbeddedSignupCode,
    MetaLoginCode,
)
from app.schemas.typings.meta_connection.strings import MetaAccessToken
from app.utilities.channels.json_values import JsonObject, parse_json_object

OAUTH_TOKEN_PATH: str = "/oauth/access_token"


class MetaOAuthClient(GraphApiClient, MetaOAuthClientContract):
    """
    Facebook Login's server side for the platform's Meta app.

    - `exchange_code`: `GET /oauth/access_token` with the app's id and
      secret trades the code the cabinet's Facebook SDK received (valid for
      seconds, used once) for a token: the business's own token of WhatsApp
      Embedded Signup, or the owner's short-lived token of Facebook Login.
    - `extend_user_token`: `grant_type=fb_exchange_token` trades a person's
      short-lived token for a long-lived one (page tokens read with it do
      not expire).
    - `read_grants`: `GET /debug_token` asked with the app's token (in the
      Authorization header) lists what a token may do, with the objects of
      its granular permissions (the WhatsApp Business Accounts of Embedded
      Signup).

    Meta's token endpoint takes the app secret as a query parameter; the
    request log of httpx is muted and errors never carry the URL, so it is
    written nowhere. Refused codes and tokens raise ValidationFailedError,
    an unreachable Meta ExternalServiceError.
    """

    def exchange_code(
        self,
        code: MetaEmbeddedSignupCode | MetaLoginCode,
        app: MetaAppCredentials,
    ) -> MetaAccessToken:
        return read_access_token(
            self._get(
                OAUTH_TOKEN_PATH,
                {
                    "client_id": str(app.app_id),
                    "client_secret": str(app.app_secret),
                    "code": str(code),
                },
            )
        )

    def extend_user_token(
        self, token: MetaAccessToken, app: MetaAppCredentials
    ) -> MetaAccessToken:
        return read_access_token(
            self._get(
                OAUTH_TOKEN_PATH,
                {
                    "grant_type": "fb_exchange_token",
                    "client_id": str(app.app_id),
                    "client_secret": str(app.app_secret),
                    "fb_exchange_token": str(token),
                },
            )
        )

    def read_grants(
        self, token: MetaAccessToken, app: MetaAppCredentials
    ) -> MetaTokenGrants:
        return read_token_grants(
            self._get(
                "/debug_token",
                {"input_token": str(token)},
                authorization=f"Bearer {app.app_id}|{app.app_secret}",
            )
        )

    def _get(
        self,
        path: str,
        params: dict[str, str],
        authorization: str | None = None,
    ) -> JsonObject:
        try:
            response: httpx.Response = self._http_client.get(
                path,
                params=params,
                headers=(
                    {} if authorization is None else {"Authorization": authorization}
                ),
            )
        except httpx.HTTPError as transport_error:
            raise ExternalServiceError(
                f"Meta sign-in request failed: {type(transport_error).__name__}."
            ) from None

        body: JsonObject = parse_json_object(response.content) or {}
        if response.status_code < 400 and "error" not in body:
            return body

        raise build_graph_error(
            response.status_code,
            body,
            response.headers.get("Retry-After"),
            is_lookup=True,
        )
