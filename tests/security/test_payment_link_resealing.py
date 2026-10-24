"""
A key rotation seals the owner's payment pages that carry a key again: the
live pages and those retired for deposits still waiting on them move to
the current key, pages sealed with it already are left alone, a page
re-sealed during the run keeps its new address, and once the old key is
retired every page still opens.
"""

from collections.abc import Callable

from typed_time_provider import Microseconds

from app.adapters.security.secret_cipher_adapter import SecretCipherAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.deposit_repositories import DepositSettingsRepository
from app.schemas.constants.deposits import PaymentLinkKind
from app.schemas.domain.deposits import (
    DepositSettingsDocument,
    PaymentLink,
    RetiredPaymentLink,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.deposits.constrained_strings import PaymentLinkLabel
from app.schemas.typings.deposits.strings import PaymentLinkHost, PaymentLinkPreview
from app.use_cases.admin.security.secret_resealer import RotationTally, SecretResealer
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.deposits.deposit_keys import deposit_settings_id_of
from tests.security.test_secret_resealer import (
    NEW_KEY,
    OLD,
    OLD_KEY,
    RecordingTelegram,
    calendar_repo,
    channel_repo,
)

BUSINESS: BusinessId = BusinessId()
LIVE_PAGE: str = "https://pay.example.com/d?sum={amount}&token=test-token-0000"
RETIRED_PAGE: str = "https://pay.example.com/d?sum={amount}&key=test-token-0001"
OPEN_PAGE: str = "https://pay.example.com/d?sum={amount}&sig=test-token-0002"
RING_SETTINGS = assemble_app_settings({"ENCRYPTION_KEYS": f"{NEW_KEY},{OLD_KEY}"})
RING: SecretCipherAdapter = SecretCipherAdapter(RING_SETTINGS)
NEW_ONLY: SecretCipherAdapter = SecretCipherAdapter(
    assemble_app_settings({"ENCRYPTION_KEYS": NEW_KEY})
)


def page(address: str, cipher: SecretCipherAdapter) -> PaymentLink:
    return PaymentLink(
        label=PaymentLinkLabel("Bank"),
        kind=PaymentLinkKind.TEMPLATE,
        sealed_address=cipher.encrypt(ChannelSecret(address)),
        host=PaymentLinkHost("pay.example.com"),
        preview=PaymentLinkPreview("https://pay.example.com/d (…)"),
        added_at=Microseconds(1),
    )


def settings_with(
    live: list[PaymentLink], retired: list[PaymentLink]
) -> DepositSettingsDocument:
    return DepositSettingsDocument(
        id=deposit_settings_id_of(BUSINESS),
        business_id=BUSINESS,
        is_enabled=True,
        payment_links=live,
        retired_payment_links=[
            RetiredPaymentLink(link=link, retired_at=Microseconds(2))
            for link in retired
        ],
        created_at=Microseconds(1),
        updated_at=Microseconds(1),
    )


def settings_repo() -> DepositSettingsRepository:
    return DepositSettingsRepository(
        InMemoryDocumentCollectionAdapter[DepositSettingsDocument](
            DepositSettingsDocument
        )
    )


class RacingSettingsRepository(DepositSettingsRepository):
    """The owner re-adds the live page (sealed with the ring) during the run."""

    def update(
        self,
        business_id: BusinessId,
        change: Callable[[DepositSettingsDocument], DepositSettingsDocument | None],
    ) -> DepositSettingsDocument | None:
        def replace_live(stored: DepositSettingsDocument) -> DepositSettingsDocument:
            stored.payment_links[0].sealed_address = RING.encrypt(
                ChannelSecret(OPEN_PAGE)
            )
            return stored

        super().update(business_id, replace_live)
        return super().update(business_id, change)


def run(repo: DepositSettingsRepository) -> RotationTally:
    resealer = SecretResealer(
        channel_repo=channel_repo(),
        calendar_connection_repo=calendar_repo(),
        secret_cipher=RING,
        secret_rotation=RING,
        telegram_client=RecordingTelegram(),
        app_settings=RING_SETTINGS,
        deposit_settings_repo=repo,
    )
    tally = RotationTally()
    resealer.reseal_business(BUSINESS, tally)
    return tally


def addresses(repo: DepositSettingsRepository) -> list[str]:
    stored = repo.get_by_business(BUSINESS)
    assert stored is not None
    pages = [
        *stored.payment_links,
        *(retired.link for retired in stored.retired_payment_links),
    ]
    return [
        str(NEW_ONLY.decrypt(link.sealed_address))
        for link in pages
        if link.sealed_address is not None
    ]


def test_live_and_retired_pages_move_to_the_current_key() -> None:
    repo = settings_repo()
    repo.save(
        settings_with(
            [page(LIVE_PAGE, OLD), page(OPEN_PAGE, RING)], [page(RETIRED_PAGE, OLD)]
        )
    )

    tally = run(repo)

    # Opened with the new key alone: the old one can be retired.
    assert addresses(repo) == [LIVE_PAGE, OPEN_PAGE, RETIRED_PAGE]
    assert (tally.total, tally.rotated, tally.current, tally.unreadable) == (
        3,
        2,
        1,
        0,
    )


def test_a_page_sealed_again_during_the_run_keeps_its_new_address() -> None:
    repo = RacingSettingsRepository(
        InMemoryDocumentCollectionAdapter[DepositSettingsDocument](
            DepositSettingsDocument
        )
    )
    repo.save(settings_with([page(LIVE_PAGE, OLD)], [page(RETIRED_PAGE, OLD)]))

    run(repo)

    assert addresses(repo) == [OPEN_PAGE, RETIRED_PAGE]


def test_a_business_without_deposits_has_nothing_to_reseal() -> None:
    tally = run(settings_repo())

    assert (tally.total, tally.rotated) == (0, 0)
