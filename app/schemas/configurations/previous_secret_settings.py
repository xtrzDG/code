from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.platform.strings import PlatformSecret


class PreviousSecretSettings(ImmutableDTO):
    """
    The value a webhook secret had before its rotation (`<NAME>_PREVIOUS`),
    so callbacks keep being accepted while the provider still signs with
    it: ELEVENLABS_WEBHOOK_SECRET_PREVIOUS, META_APP_SECRET_PREVIOUS,
    FLITT_SECRET_KEY_PREVIOUS, ZADARMA_API_SECRET_PREVIOUS and
    TWILIO_AUTH_TOKEN_PREVIOUS. A verifier tries the current value first,
    then this one; nothing outgoing is ever signed with it, and without a
    current value it opens nothing. All optional: remove each once the
    provider has switched (docs/dev/environment.md).
    """

    elevenlabs_webhook_secret: PlatformSecret | None = Field(default=None, repr=False)
    meta_app_secret: PlatformSecret | None = Field(default=None, repr=False)
    flitt_secret_key: PlatformSecret | None = Field(default=None, repr=False)
    zadarma_api_secret: PlatformSecret | None = Field(default=None, repr=False)
    twilio_auth_token: PlatformSecret | None = Field(default=None, repr=False)
