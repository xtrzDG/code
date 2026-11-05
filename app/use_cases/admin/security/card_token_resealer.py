"""
Seal the saved cards' tokens of a business's payment orders (Flitt's
rectoken, which the retries of a declined charge use) again with the
current key, each written back only if the order still holds the token
as it was read (a card saved again meanwhile is sealed with the current
key already).
"""

from collections.abc import Callable

from app.contracts.billing import PaymentOrderRepoContract
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret

type Reseal = Callable[[EncryptedChannelSecret], EncryptedChannelSecret | None]


def reseal_card_tokens(
    payment_order_repo: PaymentOrderRepoContract,
    business_id: BusinessId,
    reseal: Reseal,
) -> None:
    for payment_order in payment_order_repo.list_by_business(business_id):
        token: EncryptedChannelSecret | None = payment_order.sealed_card_token
        if token is None:
            continue

        sealed: EncryptedChannelSecret | None = reseal(token)
        if sealed is not None and sealed != token:
            payment_order_repo.update(
                business_id, payment_order.id, replacing(token, sealed)
            )


def replacing(
    read: EncryptedChannelSecret, sealed: EncryptedChannelSecret
) -> Callable[[PaymentOrderDocument], PaymentOrderDocument | None]:
    def replace(stored: PaymentOrderDocument) -> PaymentOrderDocument | None:
        if stored.sealed_card_token != read:
            return None

        stored.sealed_card_token = sealed
        return stored

    return replace
