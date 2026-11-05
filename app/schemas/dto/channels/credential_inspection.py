"""What Meta says of a channel's access token (Graph API `debug_token`)."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds


class MetaTokenFacts(ImmutableDTO):
    """
    Whether the token still works and when it stops: the earlier of its own
    expiry and the end of its data access (None: neither ends, as with a
    system user's token).
    """

    is_valid: bool
    expires_at: Microseconds | None = None
