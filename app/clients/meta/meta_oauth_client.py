from collections.abc import Mapping

import httpx

from app.clients.meta.graph_api_client import GraphApiClient
from app.clients.meta.meta_grant_readers import read_access_token, read_token_grants
from app.clients.meta.meta_graph_errors import build_graph_error
from app.contracts.channel_credentials import MetaTokenRefreshClientContract
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
# Meta's Refresh API: a system user token that expires is renewed for
# another 60 days from the day of the call.
SIXTY_DAY_RENEWAL_PARAMETER: str = "set_token_expires_in_60_days"
SIXTY_DAY_RENEWAL: Mapping[str, str] = {SIXTY_DAY_RENEWAL_PARAMETER: "true"}


class MetaOAuthClient(
    GraphApiClient, MetaOAuthClientContract, MetaTokenRefreshClientContract
):
    """
    Facebook Login's server side for the platform's Meta app.

    - `exchange_code`: `GET /oauth/access_token` with the app's id and
      secret trades the code the cabinet's Facebook SDK received (valid for
      seconds, used once) for a token: the business's own token of WhatsApp
      Embedded Signup, or the owner's short-lived token of Facebook Login.
    - `extend_user_token`: `grant_type=fb_exchange_token` trades a person's
      short-lived token for a long-lived one (page tokens read with it do
      not expire).
    - `refresh_business_token`: the same exchange with
      `set_token_expires_in_60_days=true` renews the business's Embedded
      Signup token (a system user token of 60 days) for another 60 days.
      Meta's `expires_in` is ignored: `read_grants` tells the new end. The
      old token keeps working until its own end and is never revoked.
    - `read_grants`: `GET /debug_token` asked with the app's token (in the
      Authorization header) lists what a token may do, with the objects of
      its granular permissions (the WhatsApp Business Accounts of Embedded
      Signup), and when it ends.

    Meta's token endpoint takes the app secret and the traded token as query
    parameters (no Authorization header, no `appsecret_proof`); the request
    log of httpx is muted and errors never carry the URL, so neither is
    written anywhere. Refused codes and tokens raise ValidationFailedError,
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
        return self._exchange_token(token, app, {})

    def refresh_business_token(
        self, token: MetaAccessToken, app: MetaAppCredentials
    ) -> MetaAccessToken:
        return self._exchange_token(token, app, SIXTY_DAY_RENEWAL)

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

    def _exchange_token(
        self,
        token: MetaAccessToken,
        app: MetaAppCredentials,
        options: Mapping[str, str],
    ) -> MetaAccessToken:
        """`grant_type=fb_exchange_token`: the token Meta trades for `token`."""

        return read_access_token(
            self._get(
                OAUTH_TOKEN_PATH,
                {
                    "grant_type": "fb_exchange_token",
                    "client_id": str(app.app_id),
                    "client_secret": str(app.app_secret),
                    "fb_exchange_token": str(token),
                    **options,
                },
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
