"""The `appsecret_proof` Graph API calls with a person's token carry."""

import hashlib
import hmac

from app.schemas.dto.channels.meta_provider import MetaAppCredentials


def appsecret_proof(access_token: str, app: MetaAppCredentials) -> str:
    """
    HMAC-SHA256 of the token keyed with the app secret (hex): Meta accepts
    the token only from a holder of the secret when the app requires it.
    """

    return hmac.new(
        str(app.app_secret).encode("utf-8"),
        access_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
