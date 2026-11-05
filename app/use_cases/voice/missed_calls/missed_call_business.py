"""The business a missed call belongs to, and the caller's number."""

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.calls.missed_calls import MissedCallReport
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.channels.channel_phone_numbers import parse_messaging_phone_number


def find_missed_call_business(
    business_repo: BusinessRepoContract,
    channel_repo: ChannelRepoContract,
    phone_number_parser: PhoneNumberParserContract,
    report: MissedCallReport,
) -> BusinessDocument | None:
    """
    The business the report names, else the one whose phone line was
    called (its phone channel, connected or not: a call that came after
    the line was turned off is still its caller).
    """

    if report.business_id is not None:
        return business_repo.get(report.business_id)

    if report.assistant_number is None:
        return None

    number: E164PhoneNumber | None = parse_messaging_phone_number(
        phone_number_parser, str(report.assistant_number)
    )
    if number is None:
        return None

    channel: ChannelDocument | None = channel_repo.find_by_external_id(
        ChannelKind.PHONE, ChannelExternalId(str(number))
    )
    return None if channel is None else business_repo.get(channel.business_id)


def read_caller_number(
    phone_number_parser: PhoneNumberParserContract,
    business: BusinessDocument,
    report: MissedCallReport,
) -> E164PhoneNumber | None:
    """The caller's number in E.164 (a national format is read as local)."""

    if report.caller_number is None:
        return None

    return parse_messaging_phone_number(
        phone_number_parser, str(report.caller_number), business.country_code
    )
