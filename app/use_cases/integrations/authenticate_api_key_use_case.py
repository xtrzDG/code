import hmac

from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.integration_repositories import ApiKeyRepoContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.integrations import ApiKeyStatus
from app.schemas.domain.api_keys import ApiKeyDocument
from app.schemas.dto.public_api.access import ApiKeyCredentials, ApiKeyPrincipal
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    RateLimitedError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.integrations.constrained_integers import (
    PublicApiRequestsPerMinute,
)
from app.schemas.typings.integrations.constrained_strings import ApiKeySecretHash
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.channels.widget_rate_limits import (
    describe_client_network,
    refuse_over_limits,
)
from app.utilities.integrations.integration_secrets import hash_api_key

INVALID_KEY_MESSAGE: str = "The API key is not valid (any more)."
TOO_MANY_MESSAGE: str = "Too many requests with this API key; try again shortly."
TOO_MANY_REFUSED_MESSAGE: str = (
    "Too many requests with keys that are not valid; try again shortly."
)
RATE_KEY_PREFIX: str = "public-api:key"
REFUSED_KEY_PREFIX: str = "public-api:refused"
# Keys that are not valid a client network may present in a minute before
# it is refused without the digest being computed: scrypt costs about 10 ms
# and 4 MiB, which a script guessing keys must not get for free. Generous,
# since integration platforms send many businesses' requests from a few
# addresses; past it their next request gets 429 with Retry-After.
REFUSED_KEYS_PER_NETWORK: RequestsPerWindow = RequestsPerWindow(60)
MINUTE: RateWindowSeconds = RateWindowSeconds(60)
# When a key was last used is written at most this often (a busy key
# would otherwise write its document on every request).
LAST_USED_STAMP_MICROSECONDS: int = 60 * 1_000_000


class AuthenticateApiKeyUseCase(UseCaseContract[ApiKeyCredentials, ApiKeyPrincipal]):
    """
    A public API request's bearer key: found across businesses by its
    scrypt digest (the token names no business), then everything else in its
    business's scope. A revoked or unknown key, or one whose business is
    gone, is 401; each key may make PUBLIC_API_REQUESTS_PER_MINUTE requests
    a minute (429 with Retry-After past them). A client network that sent
    REFUSED_KEYS_PER_NETWORK keys that are not valid within a minute is
    refused (429) before the next key's digest is computed. The stored
    digest is compared in constant time. When the key was last used is
    kept to the minute.
    """

    def __init__(
        self,
        api_key_repo: ApiKeyRepoContract,
        business_repo: BusinessRepoContract,
        rate_limits: RequestRateLimitRegistryContract,
        storage_scope: StorageScopeContract,
        requests_per_minute: PublicApiRequestsPerMinute,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._api_key_repo: ApiKeyRepoContract = api_key_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._rate_limits: RequestRateLimitRegistryContract = rate_limits
        self._storage_scope: StorageScopeContract = storage_scope
        self._requests_per_minute: PublicApiRequestsPerMinute = requests_per_minute
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ApiKeyCredentials) -> ApiKeyPrincipal:
        refusals: RateLimitCounter | None = refusal_counter(
            input_data.client_ip_address
        )
        self._refuse_a_guessing_network(refusals)
        digest: ApiKeySecretHash = hash_api_key(input_data.token)
        with self._storage_scope.platform_wide():
            found: ApiKeyDocument | None = self._api_key_repo.find_by_secret_hash(
                digest
            )
        if (
            found is None
            or found.status is not ApiKeyStatus.ACTIVE
            or not hmac.compare_digest(str(found.secret_hash), str(digest))
        ):
            if refusals is not None:
                self._rate_limits.try_acquire_all(
                    [refusals], MINUTE, self._wall_clock.now_unix()
                )
            raise AuthenticationRequiredError(INVALID_KEY_MESSAGE)

        with self._storage_scope.scoped_to_business(found.business_id):
            if self._business_repo.get(found.business_id) is None:
                raise AuthenticationRequiredError(INVALID_KEY_MESSAGE)

            now: Microseconds = self._wall_clock.now_unix()
            refuse_over_limits(
                self._rate_limits,
                [
                    RateLimitCounter(
                        key=RateLimitKey(f"{RATE_KEY_PREFIX}:{found.id}"),
                        limit=RequestsPerWindow(int(self._requests_per_minute)),
                    )
                ],
                TOO_MANY_MESSAGE,
                now,
            )
            self._stamp_use(found, now)

        return ApiKeyPrincipal(
            api_key_id=found.id,
            api_key_name=found.name,
            business_id=found.business_id,
            scopes=found.scopes,
            created_by=found.created_by,
            client_ip_address=input_data.client_ip_address,
        )

    def _refuse_a_guessing_network(self, refusals: RateLimitCounter | None) -> None:
        if refusals is None:
            return

        now: Microseconds = self._wall_clock.now_unix()
        if self._rate_limits.has_room(refusals, MINUTE, now):
            return

        raise RateLimitedError(
            TOO_MANY_REFUSED_MESSAGE,
            retry_after_seconds=self._rate_limits.seconds_until_free(
                refusals, MINUTE, now
            ),
        )

    def _stamp_use(self, api_key: ApiKeyDocument, now: Microseconds) -> None:
        last_used: Microseconds | None = api_key.last_used_at
        if last_used is not None and int(now) - int(last_used) < (
            LAST_USED_STAMP_MICROSECONDS
        ):
            return

        self._api_key_repo.update(
            api_key.business_id,
            api_key.id,
            lambda stored: stored.model_copy(
                update={"last_used_at": now, "updated_at": now}
            ),
        )


def refusal_counter(
    client_ip_address: ClientIpAddress | None,
) -> RateLimitCounter | None:
    """The counter of a client network's refused keys (none without an address)."""

    if client_ip_address is None:
        return None

    network: str = describe_client_network(client_ip_address)
    return RateLimitCounter(
        key=RateLimitKey(f"{REFUSED_KEY_PREFIX}:{network}"),
        limit=REFUSED_KEYS_PER_NETWORK,
    )
