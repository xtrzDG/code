"""Fakes implementing the contracts the operations module depends on."""

import threading
from datetime import UTC, datetime

import phonenumbers
from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.localization_utilities import (
    LocalizedTextResolverContract,
    PhoneNumberParserContract,
)
from app.contracts.operations import BookingCalendarSyncFacilitatorContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.constants.localization import PhoneNumberKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import ManagerContact
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.localization import LocalizedText, PhoneNumberDetails
from app.schemas.exceptions.application_errors import (
    InvalidPhoneNumberError,
    ValidationFailedError,
)
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_integers import CountryCallingCode
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import (
    FormattedPhoneNumber,
    LocalizedTextValue,
    RawPhoneNumberInput,
)

ENGLISH: LanguageTag = LanguageTag("en")


class FakeLocalizedTextResolver(LocalizedTextResolverContract):
    """Exact tag, base language, English, any value (the contract's chain)."""

    def resolve(
        self,
        text: LocalizedText,
        language_tag: LanguageTag,
    ) -> LocalizedTextValue:
        if language_tag in text.values:
            return text.values[language_tag]

        base_language = LanguageTag(str(language_tag).split("-")[0])
        if base_language in text.values:
            return text.values[base_language]

        if ENGLISH in text.values:
            return text.values[ENGLISH]

        return next(iter(text.values.values()))


class PhonenumbersParser(PhoneNumberParserContract):
    """Parser backed by the phonenumbers library (any country)."""

    def parse(
        self,
        raw_phone_number: RawPhoneNumberInput,
        country_hint: CountryCode | None,
    ) -> PhoneNumberDetails:
        try:
            number = phonenumbers.parse(
                str(raw_phone_number),
                None if country_hint is None else str(country_hint),
            )
        except phonenumbers.NumberParseException as error:
            raise InvalidPhoneNumberError(str(error)) from error

        if not phonenumbers.is_valid_number(number):
            raise InvalidPhoneNumberError(f"{raw_phone_number} is not valid.")

        region: str = phonenumbers.region_code_for_number(number) or "ZZ"
        return PhoneNumberDetails(
            e164=E164PhoneNumber(
                phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
            ),
            country_code=CountryCode(region),
            calling_code=CountryCallingCode(number.country_code or 1),
            kind=PhoneNumberKind.MOBILE,
            is_mobile=True,
            international_format=FormattedPhoneNumber(
                phonenumbers.format_number(
                    number, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )
            ),
            national_format=FormattedPhoneNumber(
                phonenumbers.format_number(
                    number, phonenumbers.PhoneNumberFormat.NATIONAL
                )
            ),
        )


class RecordingManagerNotifier(ManagerNotificationFacilitatorContract):
    """Records notifications; addresses listed as failing return False."""

    def __init__(
        self,
        failing_addresses: frozenset[str] = frozenset(),
        raising_addresses: frozenset[str] = frozenset(),
    ) -> None:
        self._failing_addresses: frozenset[str] = failing_addresses
        self._raising_addresses: frozenset[str] = raising_addresses
        self._lock: threading.Lock = threading.Lock()
        self.sent: list[tuple[ManagerContact, MessageText]] = []
        self.notifications: list[StaffNotification] = []

    def notify(self, notification: StaffNotification) -> bool:
        contact: ManagerContact = notification.contact
        if str(contact.address) in self._raising_addresses:
            raise RuntimeError("Notifier exploded.")

        with self._lock:
            self.sent.append((contact, notification.text))
            self.notifications.append(notification)

        return str(contact.address) not in self._failing_addresses


class RecordingCalendarSync(BookingCalendarSyncFacilitatorContract):
    def __init__(self) -> None:
        self.synced: list[BookingDocument] = []

    def sync(self, booking: BookingDocument) -> None:
        self.synced.append(booking)


class ReversingSecretCipher(SecretCipherAdapterContract):
    """Readable stand-in for encryption: prefix and reverse."""

    def encrypt(self, secret: ChannelSecret) -> EncryptedChannelSecret:
        return EncryptedChannelSecret(f"enc:{str(secret)[::-1]}")

    def decrypt(self, encrypted_secret: EncryptedChannelSecret) -> ChannelSecret:
        text: str = str(encrypted_secret)
        if not text.startswith("enc:"):
            raise ValidationFailedError("Not an encrypted secret.")

        return ChannelSecret(text[len("enc:") :][::-1])


class MovableClock:
    """Wall clock whose time tests can move."""

    def __init__(self, moment: datetime) -> None:
        self._nanoseconds: int = to_nanoseconds(moment)
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self._nanoseconds,
        )

    def move_to(self, moment: datetime) -> None:
        self._nanoseconds = to_nanoseconds(moment)

    def now_microseconds(self) -> Microseconds:
        return self.wall_clock.now_unix()


def to_nanoseconds(moment: datetime) -> int:
    utc_moment: datetime = moment.astimezone(UTC)
    epoch: datetime = datetime(1970, 1, 1, tzinfo=UTC)
    delta = utc_moment - epoch
    return (delta.days * 86_400 + delta.seconds) * 1_000_000_000 + (
        delta.microseconds * 1_000
    )


def to_microseconds(moment: datetime) -> Microseconds:
    return Microseconds(to_nanoseconds(moment) // 1_000)
