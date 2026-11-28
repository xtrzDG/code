"""
The notices every owner must get whatever they set up (the pages guests
pay deposits on changed, PAY-06; the business's WhatsApp token from Meta
was not renewed or ends): their account's e-mail, built from the edges of
the context that sends them.
"""

from dependency_injector.providers import Factory, Provider
from typed_time_provider import Microseconds, WallClock

from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.utilities import UtilitiesContainer
from app.facilitators.notifications.owner_account_email_facilitator import (
    OwnerAccountEmailFacilitator,
)
from app.transformers.notifications.staff_notification_text_transformer import (
    StaffNotificationTextTransformer,
)


def owner_account_email_facilitator(
    repositories: RepositoriesContainer,
    facilitators: FacilitatorsContainer,
    utilities: UtilitiesContainer,
    cabinet_base_url: Provider[object],
    wall_clock: Provider[WallClock[Microseconds]],
) -> Factory[OwnerAccountEmailFacilitator]:
    """
    Each owner's sign-in e-mail through the outbox, in their account's
    language, with a signed link into the cabinet (CABINET_BASE_URL, a
    CabinetBaseUrl or None).
    """

    return Factory(
        OwnerAccountEmailFacilitator,
        user_repo=repositories.user_repo,
        manager_notifier=facilitators.manager_notification_facilitator,
        link_signer=facilitators.staff_link_signer,
        text_transformer=Factory(
            StaffNotificationTextTransformer,
            text_resolver=utilities.localized_text_resolver,
        ),
        cabinet_base_url=cabinet_base_url,
        wall_clock=wall_clock,
    )
