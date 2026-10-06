from app.contracts.calendar_sync import (
    BookingSystemConnectorContract,
    BookingSystemConnectorRegistryContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.constants.calendar_sync import BookingSystemKind
from app.schemas.domain.calendar_sync import BookingSystemLink
from app.schemas.dto.calendar_sync.busy_reads import (
    BookingSystemCredentials,
    BookingSystemRead,
    BookingSystemResource,
    BusyPeriod,
    BusyWindow,
)
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.strings import BookingSystemApiKey


class BookingSystemBusyReader:
    """
    The bookings a resource has in the business's booking system, through
    the connector of its kind; the API key is decrypted only for the call.
    """

    def __init__(
        self,
        registry: BookingSystemConnectorRegistryContract,
        secret_cipher: SecretCipherAdapterContract,
    ) -> None:
        self._registry: BookingSystemConnectorRegistryContract = registry
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher

    def read(
        self,
        link: BookingSystemLink,
        window: BusyWindow,
        timeout: BusyTimeFetchSeconds,
    ) -> list[BusyPeriod]:
        """
        Raises:
            BusyTimeSourceError: why the bookings were not read.
        """

        connector: BookingSystemConnectorContract = self._registry.connector_for(
            link.kind
        )
        return connector.list_busy(
            BookingSystemRead(
                credentials=BookingSystemCredentials(
                    api_key=BookingSystemApiKey(
                        str(self._secret_cipher.decrypt(link.encrypted_api_key))
                    ),
                    external_resource_id=link.external_resource_id,
                ),
                window=window,
                timeout=timeout,
            )
        )

    def describe(
        self,
        kind: BookingSystemKind,
        credentials: BookingSystemCredentials,
        timeout: BusyTimeFetchSeconds,
    ) -> BookingSystemResource:
        """Check a key and a resource before they are saved (raises the reason)."""

        return self._registry.connector_for(kind).describe(credentials, timeout)
