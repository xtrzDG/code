"""Alerts to the platform team about how sign-in codes are asked for."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.compliance.strings import ClientNetwork
from app.schemas.typings.users.constrained_integers import OtpDestinationCount


class SignInCodeSprayAlert(ImmutableDTO):
    """
    One client network asked sign-in codes for `destination_count` different
    phones and e-mails within the last hour (the threshold or more).
    """

    client_network: ClientNetwork
    destination_count: OtpDestinationCount
    threshold: OtpDestinationCount
