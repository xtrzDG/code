"""The access token of a business's Google connection, refreshed when due."""

from typed_time_provider import Microseconds

from app.contracts.operations import (
    CalendarConnectionRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.domain.calendar import CalendarConnectionDocument
from app.schemas.dto.operations.calendar_connection import CalendarTokenGrant
from app.schemas.typings.bookings.strings import (
    CalendarAccessToken,
    CalendarRefreshToken,
)
from app.schemas.typings.channels.strings import ChannelSecret
from app.utilities.scheduling.zoned_time import MICROSECONDS_PER_SECOND

# Refresh a cached access token this long before Google expires it.
ACCESS_TOKEN_SAFETY_SECONDS: int = 60


def fresh_access_token(
    connection: CalendarConnectionDocument,
    connection_repo: CalendarConnectionRepoContract,
    calendar_client: GoogleCalendarClientContract,
    secret_cipher: SecretCipherAdapterContract,
    now: Microseconds,
) -> CalendarAccessToken:
    """
    The cached access token while it is good for another minute; otherwise
    a new one from the refresh token, cached (encrypted) on the connection.

    Raises:
        ExternalServiceError: Google refused the refresh (invalid_grant:
            the owner revoked access) or could not be reached.
    """

    safety_margin: int = ACCESS_TOKEN_SAFETY_SECONDS * MICROSECONDS_PER_SECOND
    if (
        connection.encrypted_access_token is not None
        and connection.access_token_expires_at is not None
        and int(connection.access_token_expires_at) > int(now) + safety_margin
    ):
        return CalendarAccessToken(
            str(secret_cipher.decrypt(connection.encrypted_access_token))
        )

    grant: CalendarTokenGrant = calendar_client.refresh_access_token(
        CalendarRefreshToken(
            str(secret_cipher.decrypt(connection.encrypted_refresh_token))
        )
    )
    connection.encrypted_access_token = secret_cipher.encrypt(
        ChannelSecret(str(grant.access_token))
    )
    connection.access_token_expires_at = Microseconds(
        int(now) + int(grant.expires_in) * MICROSECONDS_PER_SECOND
    )
    if grant.refresh_token is not None:
        connection.encrypted_refresh_token = secret_cipher.encrypt(
            ChannelSecret(str(grant.refresh_token))
        )

    connection.updated_at = now
    connection_repo.save(connection)
    return grant.access_token
