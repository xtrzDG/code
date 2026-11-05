"""
Seal the owner's payment pages that carry a key again with the current key
(the live pages and those retired for deposits still waiting on them), in
one write of the business's deposit settings that replaces only the
addresses still sealed as they were read (a page removed and added again
meanwhile is sealed with the current key already).
"""

from collections.abc import Callable

from app.contracts.repositories.deposit_repositories import (
    DepositSettingsRepoContract,
)
from app.schemas.domain.deposits import DepositSettingsDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.utilities.deposits.payment_pages import every_page

type Reseal = Callable[[EncryptedChannelSecret], EncryptedChannelSecret | None]


def reseal_payment_links(
    settings_repo: DepositSettingsRepoContract,
    business_id: BusinessId,
    reseal: Reseal,
) -> None:
    """Every sealed payment page of the business under the current key."""

    settings: DepositSettingsDocument | None = settings_repo.get_by_business(
        business_id
    )
    if settings is None:
        return

    resealed: dict[EncryptedChannelSecret, EncryptedChannelSecret] = {}
    for page in every_page(settings):
        if page.sealed_address is None:
            continue

        sealed = reseal(page.sealed_address)
        if sealed is not None and sealed != page.sealed_address:
            resealed[page.sealed_address] = sealed

    if resealed:
        settings_repo.update(business_id, replacing(resealed))


def replacing(
    resealed: dict[EncryptedChannelSecret, EncryptedChannelSecret],
) -> Callable[[DepositSettingsDocument], DepositSettingsDocument | None]:
    def replace(stored: DepositSettingsDocument) -> DepositSettingsDocument | None:
        changed: bool = False
        for page in every_page(stored):
            if page.sealed_address is not None and page.sealed_address in resealed:
                page.sealed_address = resealed[page.sealed_address]
                changed = True

        return stored if changed else None

    return replace
