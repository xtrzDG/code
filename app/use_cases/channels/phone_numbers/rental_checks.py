"""What must hold before the platform rents a number for a business."""

from app.contracts.phone_numbers import PhoneNumberRepoContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.storage import StorageScopeContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.phone_numbers import PhoneNumberStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.dto.billing import Money
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.exceptions.phone_number_errors import (
    PhoneNumberPriceChangedError,
    PhoneNumberUnavailableError,
)
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.telephony.constrained_strings import (
    PhoneNumberLabel,
    RentedLineNumber,
)
from app.use_cases.channels.phone_numbers.rented_line_channel import (
    connected_number,
    find_phone_channel,
)
from app.utilities.money.money_formatting import format_money

LABEL_LENGTH: int = 64
# Refusals are English, like every API error; the cabinet words its own.
REFUSAL_LANGUAGE: LanguageTag = LanguageTag("en")


def require_free_line(
    phone_number_repo: PhoneNumberRepoContract,
    channel_repo: ChannelRepoContract,
    business: BusinessDocument,
    phone_number: E164PhoneNumber,
) -> None:
    """
    The business rents no number yet and its phone line is not connected
    with another one.

    Raises:
        ConflictError: it already rents a number, or its line carries
            another number (turn the phone channel off first).
    """

    held: PhoneNumberDocument | None = phone_number_repo.find_held(business.id)
    if held is not None and held.status is PhoneNumberStatus.ACTIVE:
        raise ConflictError(
            "The business already has a number from us. Give it back first "
            "(turn the phone channel off) to take another one."
        )

    channel: ChannelDocument | None = find_phone_channel(channel_repo, business.id)
    line: ChannelExternalId | None = connected_number(channel)
    if line is not None and line != ChannelExternalId(str(phone_number)):
        raise ConflictError(
            "The phone channel is connected with another number. Turn it off "
            "first to take a number here."
        )


def require_unclaimed_number(
    phone_number_repo: PhoneNumberRepoContract,
    channel_repo: ChannelRepoContract,
    storage_scope: StorageScopeContract,
    business: BusinessDocument,
    phone_number: E164PhoneNumber,
) -> None:
    """
    Nobody else holds the number: no other rental, no other business's
    phone channel (looked up platform-wide).

    Raises:
        PhoneNumberUnavailableError: someone holds it.
    """

    with storage_scope.platform_wide():
        holder: PhoneNumberDocument | None = phone_number_repo.find_holder(
            RentedLineNumber(str(phone_number))
        )
        channel: ChannelDocument | None = channel_repo.find_by_external_id(
            ChannelKind.PHONE, ChannelExternalId(str(phone_number))
        )
    if holder is not None or (
        channel is not None and channel.business_id != business.id
    ):
        raise PhoneNumberUnavailableError(
            "This number is no longer available. Search again and pick another one."
        )


def require_quoted_price(quoted: Money, shown: Money) -> None:
    """
    Raises:
        PhoneNumberPriceChangedError: the price differs from the one the
            owner saw.
    """

    if quoted != shown:
        raise PhoneNumberPriceChangedError(
            "The monthly price of this kind of number is now "
            f"{format_money(quoted, REFUSAL_LANGUAGE)} (it was "
            f"{format_money(shown, REFUSAL_LANGUAGE)}). Look at the new price and "
            "take the number again."
        )


def label_of(business: BusinessDocument) -> PhoneNumberLabel:
    """The business's name, cut to what the carrier keeps."""

    name: str = " ".join(str(business.name).split())[:LABEL_LENGTH].strip()
    return PhoneNumberLabel(name or str(business.id)[:LABEL_LENGTH])
