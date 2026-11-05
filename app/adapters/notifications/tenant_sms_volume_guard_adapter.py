"""
A business's SMS volume (LOG-05): every SMS sent for a business (staff
notifications, missed-call text-backs) counts in the business's hourly
bucket, shared by every process. The SMS past ALERT_VOLUME of an hour
counts the platform signal `tenant_sms_surge` once (the
`tenant_sms_volume` alert), and from CAP_VOLUME on an SMS is refused, and
counted again, until the hour is over: an account abused for SMS pumping
costs at most that many messages an hour. SMS outside a business (the
platform's own login codes have their own caps) pass unchanged.
"""

import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.messaging_clients import SmsMessagingClientContract
from app.contracts.monitoring import SignalCounterAdapterContract
from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.dto.rate_limits import RateLimitCounter, RateLimitWindow
from app.schemas.exceptions.application_errors import ProviderRateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.strings import SmsMessageText
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
    RetryAfterSeconds,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.limits.sliding_window_limits import locate_window
from app.utilities.observability.log_context import current_log_context

LOGGER: logging.Logger = logging.getLogger(__name__)
HOUR: RateWindowSeconds = RateWindowSeconds(60 * 60)
ALERT_VOLUME: int = 60
CAP_VOLUME: RequestsPerWindow = RequestsPerWindow(200)
KEY_PREFIX: str = "tenant-sms:"


class TenantSmsVolumeGuardAdapter(SmsMessagingClientContract):
    """SMS counted per business and hour, alerted past 60, refused past 200."""

    def __init__(
        self,
        inner_client: SmsMessagingClientContract,
        buckets: RateLimitBucketAdapterContract,
        signal_counter: SignalCounterAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._inner_client: SmsMessagingClientContract = inner_client
        self._buckets: RateLimitBucketAdapterContract = buckets
        self._signals: SignalCounterAdapterContract = signal_counter
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def send_sms(self, recipient: E164PhoneNumber, text: SmsMessageText) -> None:
        """
        Raises:
            ProviderRateLimitedError: the business's SMS of this hour reached
                the cap; sending again next hour can succeed.
        """

        business_id: BusinessId | None = current_log_context().business_id
        if business_id is not None:
            self._admit(business_id)
        self._inner_client.send_sms(recipient, text)

    def _admit(self, business_id: BusinessId) -> None:
        key = RateLimitKey(f"{KEY_PREFIX}{business_id}")
        window: RateLimitWindow = locate_window(self._wall_clock.now_unix(), HOUR)
        refused = self._buckets.count_if_within(
            [RateLimitCounter(key=key, limit=CAP_VOLUME)], window
        )
        if refused is not None:
            self._signals.count(PlatformSignal.TENANT_SMS_SURGE)
            LOGGER.warning(
                "SMS of business %s refused: %s SMS an hour reached",
                business_id,
                CAP_VOLUME,
            )
            raise ProviderRateLimitedError(
                f"The business sent {int(CAP_VOLUME)} SMS this hour; more wait "
                "for the next hour.",
                retry_after_seconds=RetryAfterSeconds(int(HOUR)),
            )

        sent: int = int(self._buckets.read_counts(key, window).current_count)
        if sent == ALERT_VOLUME + 1:
            self._signals.count(PlatformSignal.TENANT_SMS_SURGE)
            LOGGER.warning(
                "Business %s sent more than %s SMS this hour", business_id, ALERT_VOLUME
            )
