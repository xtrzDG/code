"""
Fakes of the WhatsApp token renewal: Meta's token endpoints answered per
token (on the real Graph client, no network), a cipher whose every sealing
differs, recorders of the reminders that keep each subject once, as the
outbox does, and the stores' seams where a test changes or breaks a
channel while a run is under way.
"""

from collections.abc import Callable

import httpx
from typed_time_provider import Microseconds

from app.contracts.channel_credentials import ChannelCredentialWatchRepoContract
from app.contracts.notifications import (
    StaffAlertFacilitatorContract,
    StaffAlertTextsContract,
)
from app.contracts.owner_emails import OwnerAccountEmailFacilitatorContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.notifications.staff_alerts import StaffAlert
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
    EncryptedChannelSecret,
)
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit

WABA_ID: str = "102290129340398"
OTHER_WABA_ID: str = "102290129340399"
MANAGEMENT: str = "whatsapp_business_management"
MESSAGING: str = "whatsapp_business_messaging"
MICROSECONDS_PER_SECOND: int = 1_000_000


class ResealingCipher(SecretCipherAdapterContract):
    """Like Fernet, every sealing of the same secret differs; any opens."""

    PREFIX: str = "sealed:"

    def __init__(self) -> None:
        self.sealings: int = 0

    def encrypt(self, secret: ChannelSecret) -> EncryptedChannelSecret:
        self.sealings += 1
        return EncryptedChannelSecret(
            f"{self.PREFIX}{self.sealings}:{str(secret)[::-1]}"
        )

    def decrypt(self, encrypted_secret: EncryptedChannelSecret) -> ChannelSecret:
        text: str = str(encrypted_secret)
        if not text.startswith(self.PREFIX):
            raise ValidationFailedError("Invalid ciphertext.")

        _, _, reversed_secret = text.removeprefix(self.PREFIX).partition(":")
        return ChannelSecret(reversed_secret[::-1])


def graph_error(code: int, message: str) -> dict[str, object]:
    return {"error": {"message": message, "type": "OAuthException", "code": code}}


def debug_answer(
    ends_at: Microseconds | None,
    account: str,
    scopes: tuple[str, ...],
) -> dict[str, object]:
    """`debug_token` of a valid business token (`expires_at` 0: no end)."""

    return {
        "data": {
            "type": "SYSTEM_USER",
            "is_valid": True,
            "expires_at": (
                0 if ends_at is None else int(ends_at) // MICROSECONDS_PER_SECOND
            ),
            "data_access_expires_at": 0,
            "scopes": list(scopes),
            "granular_scopes": [
                {"scope": scope, "target_ids": [account]} for scope in scopes
            ],
        }
    }


class ScriptedMetaTokens:
    """
    Meta's token endpoints by token: what renewing a token answers and what
    `debug_token` says of a token. An unscripted renewal is refused like an
    expired session (190); an unscripted token is invalid. `failure` makes
    every request fail on the network; `before_renewal` runs when Meta is
    asked to renew (what happens to the channel meanwhile).
    """

    def __init__(self) -> None:
        self.renewals: dict[str, tuple[int, object]] = {}
        self.grants: dict[str, object] = {}
        self.requests: list[httpx.Request] = []
        self.failure: Exception | None = None
        self.before_renewal: Callable[[], None] | None = None

    def renew(
        self,
        old: str,
        new: str,
        ends_at: Microseconds | None,
        account: str = WABA_ID,
        scopes: tuple[str, ...] = (MANAGEMENT, MESSAGING),
    ) -> None:
        self.renewals[old] = (
            200,
            {"access_token": new, "token_type": "bearer", "expires_in": 5183944},
        )
        self.grants[new] = debug_answer(ends_at, account, scopes)

    def refuse(self, old: str, status_code: int = 400, code: int = 190) -> None:
        self.renewals[old] = (
            status_code,
            graph_error(code, "Error validating access token: Session has expired."),
        )

    def renewed(self) -> list[str]:
        """The tokens Meta was asked to renew, in order."""

        return [
            request.url.params["fb_exchange_token"]
            for request in self.requests
            if request.url.path.endswith("/oauth/access_token")
        ]

    def build(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure

        if request.url.path.endswith("/oauth/access_token"):
            if self.before_renewal is not None:
                self.before_renewal()
            status_code, body = self.renewals.get(
                request.url.params["fb_exchange_token"],
                (400, graph_error(190, "Error validating access token.")),
            )
            return httpx.Response(status_code, json=body)

        if request.url.path.endswith("/debug_token"):
            answer: object = self.grants.get(
                request.url.params["input_token"], {"data": {"is_valid": False}}
            )
            return httpx.Response(200, json=answer)

        return httpx.Response(404, json=graph_error(803, "Not scripted."))


class RecordingStaffAlerts(StaffAlertFacilitatorContract):
    """Every alert raised; one with a subject queued before queues nothing."""

    def __init__(self) -> None:
        self.raised: list[tuple[StaffAlert, StaffAlertTextsContract]] = []
        self.queued: list[StaffAlert] = []
        self.fails: bool = False

    def alert(
        self,
        business: BusinessDocument,
        alert: StaffAlert,
        texts: StaffAlertTextsContract,
    ) -> DeliveredNotificationCount:
        del business
        self.raised.append((alert, texts))
        if self.fails:
            raise RuntimeError("The outbox is down.")

        if alert.subject in {queued.subject for queued in self.queued}:
            return DeliveredNotificationCount(0)

        self.queued.append(alert)
        return DeliveredNotificationCount(1)

    def subjects(self) -> list[str]:
        return [str(alert.subject) for alert in self.queued]


class RecordingOwnerEmails(OwnerAccountEmailFacilitatorContract):
    """Every owner e-mail asked for; one subject is mailed once."""

    def __init__(self) -> None:
        self.mailed: list[StaffAlert] = []

    def email_owners(
        self,
        business: BusinessDocument,
        alert: StaffAlert,
        texts: StaffAlertTextsContract,
    ) -> DeliveredNotificationCount:
        del business, texts
        if alert.subject in {mailed.subject for mailed in self.mailed}:
            return DeliveredNotificationCount(0)

        self.mailed.append(alert)
        return DeliveredNotificationCount(1)


class HookedCredentialWatch(ChannelCredentialWatchRepoContract):
    """The channels a run lists, then `after_listing` (a change meanwhile)."""

    def __init__(self, inner: ChannelCredentialWatchRepoContract) -> None:
        self._inner: ChannelCredentialWatchRepoContract = inner
        self.after_listing: Callable[[], None] | None = None

    def list_active_credentials_ending_before(
        self,
        kind: ChannelKind,
        ending_before: Microseconds,
        in_error_ending_from: Microseconds,
        limit: DocumentQueryLimit,
    ) -> list[ChannelDocument]:
        listed: list[ChannelDocument] = (
            self._inner.list_active_credentials_ending_before(
                kind, ending_before, in_error_ending_from, limit
            )
        )
        if self.after_listing is not None:
            self.after_listing()
        return listed


class FlakyChannelRepo(ChannelRepoContract):
    """The channel store, unreachable for the channels in `failing`."""

    def __init__(self, inner: ChannelRepoContract) -> None:
        self._inner: ChannelRepoContract = inner
        self.failing: set[ChannelId] = set()

    def save(self, channel: ChannelDocument) -> None:
        self._inner.save(channel)

    def get(self, channel_id: ChannelId) -> ChannelDocument | None:
        self._fail(channel_id)
        return self._inner.get(channel_id)

    def list_by_business(self, business_id: BusinessId) -> list[ChannelDocument]:
        return self._inner.list_by_business(business_id)

    def modify(
        self,
        business_id: BusinessId,
        channel_id: ChannelId,
        change: Callable[[ChannelDocument], ChannelDocument | None],
    ) -> ChannelDocument | None:
        self._fail(channel_id)
        return self._inner.modify(business_id, channel_id, change)

    def find_by_external_id(
        self, kind: ChannelKind, external_id: ChannelExternalId
    ) -> ChannelDocument | None:
        return self._inner.find_by_external_id(kind, external_id)

    def _fail(self, channel_id: ChannelId) -> None:
        if channel_id in self.failing:
            raise ExternalServiceError("The channel store is unavailable.")
