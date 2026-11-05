"""
One client network asking sign-in codes for many different phones and
e-mails is a spray (SMS pumping, account enumeration, a takeover attempt
across accounts): the platform admins hear of it. The per-address caps
stop each burst; this sees the spread.
"""

from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.dto.sign_in_alerts import SignInCodeSprayAlert
from app.schemas.typings.compliance.strings import ClientIpAddress, ClientNetwork
from app.schemas.typings.users.constrained_integers import OtpDestinationCount
from app.utilities.channels.widget_rate_limits import describe_client_network

# Different phones and e-mails one network may ask codes for in an hour
# before the admins are told (a family, an office or a shared café stays
# under it; a script does not).
SPRAY_DESTINATIONS_PER_NETWORK: OtpDestinationCount = OtpDestinationCount(10)


def find_code_spray(
    recent: list[OtpChallengeDocument],
    client_ip_address: ClientIpAddress | None,
) -> SignInCodeSprayAlert | None:
    """
    The alert when the network of `client_ip_address` asked codes for the
    threshold of different destinations or more among the challenges of
    the last hour (this request's included); None otherwise.
    """

    if client_ip_address is None:
        return None

    network: str = describe_client_network(client_ip_address)
    destinations: set[str] = {
        destination_of(challenge)
        for challenge in recent
        if challenge.requested_from_ip is not None
        and describe_client_network(challenge.requested_from_ip) == network
    }
    if len(destinations) < int(SPRAY_DESTINATIONS_PER_NETWORK):
        return None

    return SignInCodeSprayAlert(
        client_network=ClientNetwork(network),
        destination_count=OtpDestinationCount(len(destinations)),
        threshold=SPRAY_DESTINATIONS_PER_NETWORK,
    )


def destination_of(challenge: OtpChallengeDocument) -> str:
    """A technical key of the code's destination (an e-mail without case)."""

    if challenge.phone_number is not None:
        return f"phone:{challenge.phone_number}"

    return f"email:{str(challenge.email or '').strip().casefold()}"
