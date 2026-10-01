import logging

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.registries import (
    CountryRegistryContract,
    LanguageRegistryContract,
    LoginCodeSendLockRegistryContract,
)
from app.contracts.repositories import OtpChallengeRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import (
    OtpDeliveryChannel,
    PhoneNumberKind,
)
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.dto.localization import CountryProfile, PhoneNumberDetails
from app.schemas.dto.users import OtpChallengeView, StartOtpLoginCommand
from app.schemas.exceptions.application_errors import (
    CountryRestrictedError,
    ExternalServiceError,
    RateLimitedError,
    ValidationFailedError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.schemas.typings.users.strings import MaskedLoginDestination
from app.utilities.security.email_addresses import parse_email_address
from app.utilities.security.login_code_channels import (
    is_sign_up_restricted,
    list_country_phone_channels,
    list_usable_phone_channels,
)
from app.utilities.security.login_destination_masking import (
    mask_email_address,
    mask_phone_number,
)
from app.utilities.security.one_time_codes import generate_otp_code, hash_otp_code

logger: logging.Logger = logging.getLogger(__name__)

FALLBACK_LANGUAGE: LanguageTag = LanguageTag("en")
RESEND_INTERVAL_SECONDS: int = 30
LIMIT_WINDOW_SECONDS: int = 60 * 60
# Provider details (names, settings, credentials) stay in the server log.
LOGIN_CODE_DELIVERY_FAILED_MESSAGE: str = (
    "We could not send a login code right now. Try another way to sign in "
    "or try again later."
)
TOO_MANY_CODES_MESSAGE: str = "Too many login codes were requested. Try again later."
# Lines that cannot receive a text message with the code.
NON_MESSAGING_PHONE_KINDS: frozenset[PhoneNumberKind] = frozenset(
    {PhoneNumberKind.FIXED_LINE, PhoneNumberKind.TOLL_FREE}
)


class StartOtpLoginUseCase(UseCaseContract[StartOtpLoginCommand, OtpChallengeView]):
    """
    Send a one-time login code to a phone number of any country or an e-mail.

    The phone's country decides whether sign-up is allowed and which channels
    can carry the code (SMS, WhatsApp, Telegram, in its order); only channels
    with a configured provider are used. The requested channel goes first
    when it is one of them; when a provider fails, the same code goes
    through the next channel of the list. E-mail login needs an e-mail
    provider. The code message (and a new account) uses the requested
    language, else the country's owner language, else English. Only a keyed
    hash of the code is stored.

    Every code is a paid message, so sends are limited: a second request
    for the same destination and channel within 30 seconds is refused (one
    immediate switch to another channel is allowed, for a number that is
    not on WhatsApp), and so is a send over the hourly caps per
    destination, per client address and in total. The check and the
    reservation of the send happen under one lock, before any provider is
    called, so parallel requests cannot all pass; a failed delivery drops
    its reservation. When every provider fails, the details are logged and
    the caller gets a generic message.
    """

    def __init__(
        self,
        otp_challenge_repo: OtpChallengeRepoContract,
        phone_number_parser: PhoneNumberParserContract,
        country_registry: CountryRegistryContract,
        language_registry: LanguageRegistryContract,
        otp_delivery_facilitator: OtpDeliveryFacilitatorContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        send_lock_registry: LoginCodeSendLockRegistryContract,
    ) -> None:
        self._otp_challenge_repo: OtpChallengeRepoContract = otp_challenge_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._country_registry: CountryRegistryContract = country_registry
        self._language_registry: LanguageRegistryContract = language_registry
        self._otp_delivery_facilitator: OtpDeliveryFacilitatorContract = (
            otp_delivery_facilitator
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._send_lock_registry: LoginCodeSendLockRegistryContract = send_lock_registry

    def run(self, input_data: StartOtpLoginCommand) -> OtpChallengeView:
        if input_data.locale is not None:
            self._language_registry.get(input_data.locale)

        if input_data.phone_number is not None and input_data.email is None:
            phone_number: PhoneNumberDetails = self._phone_number_parser.parse(
                input_data.phone_number,
                input_data.country_hint,
            )
            return self._start_phone_login(input_data, phone_number)

        if input_data.email is not None and input_data.phone_number is None:
            email: EmailAddress = parse_email_address(input_data.email)
            return self._start_email_login(input_data, email)

        raise ValidationFailedError("Enter either a phone number or an e-mail.")

    def _start_phone_login(
        self,
        input_data: StartOtpLoginCommand,
        phone_number: PhoneNumberDetails,
    ) -> OtpChallengeView:
        if phone_number.kind in NON_MESSAGING_PHONE_KINDS:
            raise ValidationFailedError(
                "This number cannot receive login codes; use a mobile number."
            )

        country: CountryProfile = self._load_allowed_country(phone_number.country_code)
        delivery_channels: list[OtpDeliveryChannel] = (
            self._choose_phone_delivery_channels(
                country,
                input_data.preferred_delivery_channel,
            )
        )
        locale: LanguageTag = input_data.locale or country.default_owner_language
        challenge: OtpChallengeDocument = self._send_code(
            login_method=LoginMethod.PHONE,
            phone_number=phone_number.e164,
            email=None,
            country_code=phone_number.country_code,
            delivery_channels=delivery_channels,
            locale=locale,
            requested_channel=input_data.preferred_delivery_channel,
            client_ip_address=input_data.client_ip_address,
        )
        return OtpChallengeView(
            challenge_id=challenge.id,
            login_method=LoginMethod.PHONE,
            delivery_channel=challenge.delivery_channel,
            masked_destination=mask_phone_number(phone_number),
            expires_in_seconds=self._app_settings.otp_lifetime_seconds,
            locale=locale,
            phone_number=phone_number.e164,
            international_phone_number=phone_number.international_format,
            country_code=phone_number.country_code,
        )

    def _start_email_login(
        self,
        input_data: StartOtpLoginCommand,
        email: EmailAddress,
    ) -> OtpChallengeView:
        if (
            OtpDeliveryChannel.EMAIL
            not in self._otp_delivery_facilitator.available_channels()
        ):
            raise ExternalServiceError(
                "Sign-in by e-mail is not available: no e-mail provider is "
                "configured. Sign in with a phone number."
            )

        locale: LanguageTag = input_data.locale or FALLBACK_LANGUAGE
        if input_data.country_hint is not None:
            country: CountryProfile = self._load_allowed_country(
                input_data.country_hint
            )
            locale = input_data.locale or country.default_owner_language

        masked_destination: MaskedLoginDestination = mask_email_address(email)
        challenge: OtpChallengeDocument = self._send_code(
            login_method=LoginMethod.EMAIL,
            phone_number=None,
            email=email,
            country_code=input_data.country_hint,
            delivery_channels=[OtpDeliveryChannel.EMAIL],
            locale=locale,
            requested_channel=None,
            client_ip_address=input_data.client_ip_address,
        )
        return OtpChallengeView(
            challenge_id=challenge.id,
            login_method=LoginMethod.EMAIL,
            delivery_channel=OtpDeliveryChannel.EMAIL,
            masked_destination=masked_destination,
            expires_in_seconds=self._app_settings.otp_lifetime_seconds,
            locale=locale,
            country_code=input_data.country_hint,
        )

    def _load_allowed_country(self, country_code: CountryCode) -> CountryProfile:
        country: CountryProfile = self._country_registry.get(country_code)
        if is_sign_up_restricted(country, self._app_settings):
            raise CountryRestrictedError(
                f"Sign-up is not available in country {str(country_code)}."
            )

        return country

    def _refuse_over_limits(
        self,
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        requested_channel: OtpDeliveryChannel | None,
        client_ip_address: ClientIpAddress | None,
    ) -> None:
        """
        Refuse a send within 30 seconds of the last one to the same
        destination and channel (a phone may switch to another channel at
        once), or over the hourly caps per destination, per client address
        and in total.
        """

        settings: AppSettings = self._app_settings
        resend_start: int = int(
            self._wall_clock.now_unix_with_delta(Seconds(-RESEND_INTERVAL_SECONDS))
        )
        recent: list[OtpChallengeDocument] = (
            self._otp_challenge_repo.list_created_since(
                self._wall_clock.now_unix_with_delta(Seconds(-LIMIT_WINDOW_SECONDS))
            )
        )
        same_destination: list[OtpChallengeDocument] = [
            challenge
            for challenge in recent
            if (phone_number is not None and challenge.phone_number == phone_number)
            or (email is not None and challenge.email == email)
        ]
        if any(
            int(challenge.created_at) > resend_start
            and (
                phone_number is None
                or requested_channel is None
                or challenge.delivery_channel == requested_channel
            )
            for challenge in same_destination
        ):
            raise RateLimitedError(
                f"A code was just sent. Wait {RESEND_INTERVAL_SECONDS} seconds "
                "before asking for another one."
            )

        if len(same_destination) >= int(settings.otp_sends_per_destination_per_hour):
            raise RateLimitedError(TOO_MANY_CODES_MESSAGE)

        if client_ip_address is not None and len(
            [
                challenge
                for challenge in recent
                if challenge.requested_from_ip == client_ip_address
            ]
        ) >= int(settings.otp_sends_per_ip_per_hour):
            raise RateLimitedError(TOO_MANY_CODES_MESSAGE)

        if len(recent) >= int(settings.otp_sends_per_hour):
            logger.warning(
                "The hourly cap of %s login codes is reached; sends are refused.",
                int(settings.otp_sends_per_hour),
            )
            raise RateLimitedError(TOO_MANY_CODES_MESSAGE)

    def _choose_phone_delivery_channels(
        self,
        country: CountryProfile,
        preferred_channel: OtpDeliveryChannel | None,
    ) -> list[OtpDeliveryChannel]:
        """The country's phone channels that have a provider, preferred first."""

        if not list_country_phone_channels(country):
            raise ValidationFailedError(
                "Login codes cannot be sent to phones in "
                f"{str(country.country_code)}; sign in with e-mail."
            )

        usable_channels: list[OtpDeliveryChannel] = list_usable_phone_channels(
            country, self._otp_delivery_facilitator.available_channels()
        )
        if not usable_channels:
            raise ExternalServiceError(
                "Login codes cannot be sent to phones in "
                f"{str(country.country_code)} right now: no SMS, WhatsApp or "
                "Telegram provider is configured for them. Sign in with e-mail."
            )

        if preferred_channel is not None and preferred_channel in usable_channels:
            usable_channels.remove(preferred_channel)
            usable_channels.insert(0, preferred_channel)

        return usable_channels

    def _send_code(
        self,
        login_method: LoginMethod,
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        country_code: CountryCode | None,
        delivery_channels: list[OtpDeliveryChannel],
        locale: LanguageTag,
        requested_channel: OtpDeliveryChannel | None,
        client_ip_address: ClientIpAddress | None,
    ) -> OtpChallengeDocument:
        now: Microseconds = self._wall_clock.now_unix()
        challenge_id: OtpChallengeId = OtpChallengeId()
        code: OtpCode = generate_otp_code()
        challenge = OtpChallengeDocument(
            id=challenge_id,
            login_method=login_method,
            phone_number=phone_number,
            email=email,
            country_code=country_code,
            delivery_channel=delivery_channels[0],
            locale=locale,
            code_hash=hash_otp_code(challenge_id, code),
            expires_at=self._wall_clock.now_unix_with_delta(
                Seconds(int(self._app_settings.otp_lifetime_seconds))
            ),
            requested_from_ip=client_ip_address,
            created_at=now,
            updated_at=now,
        )
        # Check and reserve together, before any (slow, paid) provider call.
        with self._send_lock_registry.lock():
            self._refuse_over_limits(
                phone_number, email, requested_channel, client_ip_address
            )
            self._otp_challenge_repo.save(challenge)

        try:
            delivery_channel: OtpDeliveryChannel = self._deliver(
                delivery_channels=delivery_channels,
                phone_number=phone_number,
                email=email,
                code=code,
                locale=locale,
            )
        except ExternalServiceError:
            # A failed delivery leaves nothing to throttle.
            self._otp_challenge_repo.delete(challenge_id)
            raise

        if delivery_channel is not challenge.delivery_channel:
            challenge = challenge.model_copy(
                update={"delivery_channel": delivery_channel}
            )
            self._otp_challenge_repo.save(challenge)

        return challenge

    def _deliver(
        self,
        delivery_channels: list[OtpDeliveryChannel],
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        code: OtpCode,
        locale: LanguageTag,
    ) -> OtpDeliveryChannel:
        """
        Send the code through the first channel whose provider accepts it.
        Provider failures are logged; the caller gets a generic message.
        """

        for delivery_channel in delivery_channels:
            try:
                self._otp_delivery_facilitator.deliver(
                    delivery_channel=delivery_channel,
                    phone_number=phone_number,
                    email=email,
                    code=code,
                    language_tag=locale,
                )
            except ExternalServiceError as error:
                logger.warning(
                    "Login code delivery by %s failed: %s",
                    delivery_channel.value,
                    error,
                )
                continue

            return delivery_channel

        raise ExternalServiceError(LOGIN_CODE_DELIVERY_FAILED_MESSAGE)
