"""
A key rotation seals the saved cards' tokens again: tokens under an old key
move to the current one, tokens under it already are left alone, a card
saved again during the run keeps its new token, and once the old key is
retired every token still opens.
"""

from app.adapters.security.secret_cipher_adapter import SecretCipherAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.billing import PaymentOrderChange
from app.repositories.payment_repositories import PaymentOrderRepository
from app.schemas.constants.payments import PaymentProvider
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.typings.billing.constrained_integers import (
    BillingIntervalMonths,
    MoneyAmountMinor,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId, SubscriptionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.use_cases.admin.security.secret_resealer import RotationTally, SecretResealer
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.security.test_payment_link_resealing import NEW_ONLY, RING, RING_SETTINGS
from tests.security.test_secret_resealer import (
    OLD,
    RecordingTelegram,
    calendar_repo,
    channel_repo,
)

BUSINESS: BusinessId = BusinessId()
LOST_KEY: str = "resealer-lost-key-0000000000000000000000"  # gitleaks:allow
LOST = SecretCipherAdapter(assemble_app_settings({"ENCRYPTION_KEYS": LOST_KEY}))
OLD_TOKEN: str = "rectoken-test-0000"
CURRENT_TOKEN: str = "rectoken-test-0001"
NEWER_TOKEN: str = "rectoken-test-0002"


def order(token: str | None, cipher: SecretCipherAdapter) -> PaymentOrderDocument:
    return PaymentOrderDocument(
        business_id=BUSINESS,
        subscription_id=SubscriptionId(),
        provider=PaymentProvider.FLITT,
        invoice_ids=[],
        amount_minor=MoneyAmountMinor(51700),
        currency_code=CurrencyCode("GEL"),
        recurring_amount_minor=MoneyAmountMinor(51700),
        recurring_interval_months=BillingIntervalMonths(1),
        sealed_card_token=(
            None if token is None else cipher.encrypt(ChannelSecret(token))
        ),
    )


def orders_repo() -> PaymentOrderRepository:
    return PaymentOrderRepository(
        InMemoryDocumentCollectionAdapter[PaymentOrderDocument](PaymentOrderDocument)
    )


class RacingOrderRepository(PaymentOrderRepository):
    """The owner saves a new card on the order while the run reseals it."""

    def update(
        self,
        business_id: BusinessId,
        payment_order_id: PaymentOrderId,
        change: PaymentOrderChange,
    ) -> PaymentOrderDocument | None:
        def save_new_card(stored: PaymentOrderDocument) -> PaymentOrderDocument:
            stored.sealed_card_token = RING.encrypt(ChannelSecret(NEWER_TOKEN))
            return stored

        super().update(business_id, payment_order_id, save_new_card)
        return super().update(business_id, payment_order_id, change)


def run(repo: PaymentOrderRepository) -> RotationTally:
    tally = RotationTally()
    SecretResealer(
        channel_repo=channel_repo(),
        calendar_connection_repo=calendar_repo(),
        secret_cipher=RING,
        secret_rotation=RING,
        telegram_client=RecordingTelegram(),
        app_settings=RING_SETTINGS,
        payment_order_repo=repo,
    ).reseal_business(BUSINESS, tally)
    return tally


def tokens(repo: PaymentOrderRepository) -> set[str]:
    return {
        str(NEW_ONLY.decrypt(stored.sealed_card_token))
        for stored in repo.list_by_business(BUSINESS)
        if stored.sealed_card_token is not None
    }


def test_saved_card_tokens_move_to_the_current_key() -> None:
    repo = orders_repo()
    sealed_current = order(CURRENT_TOKEN, RING)
    for document in (order(OLD_TOKEN, OLD), sealed_current, order(None, RING)):
        repo.save(document)

    tally = run(repo)

    assert (tally.total, tally.rotated, tally.current) == (2, 1, 1)
    assert tokens(repo) == {OLD_TOKEN, CURRENT_TOKEN}
    stored = repo.get(sealed_current.id)
    assert stored is not None
    assert stored.sealed_card_token == sealed_current.sealed_card_token


def test_a_card_saved_again_during_the_run_keeps_its_token() -> None:
    repo = RacingOrderRepository(
        InMemoryDocumentCollectionAdapter[PaymentOrderDocument](PaymentOrderDocument)
    )
    repo.save(order(OLD_TOKEN, OLD))

    run(repo)

    assert tokens(repo) == {NEWER_TOKEN}


def test_an_unreadable_token_is_counted_and_left_alone() -> None:
    repo = orders_repo()
    broken = order(OLD_TOKEN, LOST)
    repo.save(broken)

    tally = run(repo)

    assert tally.unreadable == 1
    stored = repo.get(broken.id)
    assert stored is not None
    assert stored.sealed_card_token == broken.sealed_card_token
