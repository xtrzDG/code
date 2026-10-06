from collections.abc import Sequence

from app.contracts.calendar_sync import (
    BookingSystemConnectorContract,
    BookingSystemConnectorRegistryContract,
)
from app.schemas.constants.calendar_sync import BookingSystemKind
from app.schemas.exceptions.application_errors import ValidationFailedError


class BookingSystemConnectorRegistry(BookingSystemConnectorRegistryContract):
    """
    The booking-system connectors by kind: Cal.com now; a market-specific
    one (Altegio, Cloudbeds, Poster) joins with one more adapter here.
    """

    def __init__(self, connectors: Sequence[BookingSystemConnectorContract]) -> None:
        self._connectors: dict[BookingSystemKind, BookingSystemConnectorContract] = {
            connector.kind: connector for connector in connectors
        }

    def connector_for(self, kind: BookingSystemKind) -> BookingSystemConnectorContract:
        connector: BookingSystemConnectorContract | None = self._connectors.get(kind)
        if connector is None:
            raise ValidationFailedError(
                f"The booking system {kind.value} is not supported here."
            )

        return connector

    def kinds(self) -> list[BookingSystemKind]:
        return sorted(self._connectors, key=lambda kind: kind.value)
