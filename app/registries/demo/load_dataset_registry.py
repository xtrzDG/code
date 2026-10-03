import random

from app.contracts.load_data import LoadDatasetRegistryContract
from app.registries.demo.load.load_bookings import build_bookings
from app.registries.demo.load.load_history import LoadHistory, LoadHistoryBuilder
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.load_data import LoadVolume, LoadVolumeRequest


class LoadDatasetRegistry(LoadDatasetRegistryContract):
    """
    The bulk history of a load-test business (`workshop seed-load`): chat
    customers with ten-message conversations over the last four months,
    website-widget visitors chatting right now, and bookings from ten
    months ago to two months ahead. The request's seed decides every
    random choice (each business of a run gets its own), so a run is
    repeatable in shape; ids and times follow the moment of seeding.
    """

    def build_volume(self, request: LoadVolumeRequest) -> LoadVolume:
        chooser = random.Random(int(request.random_seed))
        history: LoadHistory = LoadHistoryBuilder(request, chooser).build()
        bookings: list[BookingDocument] = build_bookings(
            request, history.conversations, chooser
        )
        return LoadVolume(
            contacts=history.contacts,
            conversations=history.conversations,
            messages=history.messages,
            bookings=bookings,
            visitors=history.visitors,
        )
