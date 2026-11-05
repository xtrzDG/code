"""
Whether a customer may get a message they did not ask for (a reminder, a
text-back after a missed call, a request for feedback after a visit).
"""

from collections.abc import Sequence

from app.contracts.privacy import SuppressionListContract
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.privacy.suppression import SuppressedIdentity
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.channels.opt_out import is_opted_out
from app.utilities.privacy.suppressed_identities import contact_identities


def is_messaging_suppressed(
    suppression_list: SuppressionListContract,
    business_id: BusinessId,
    contact: ContactDocument | None,
    also: Sequence[SuppressedIdentity] = (),
) -> bool:
    """
    True when the customer said STOP: on their contact, or on the
    business's suppression list for any of their numbers and accounts (and
    `also`, e.g. the number about to be texted), which outlives an erasure;
    and while the owner blocked them (Customers), who gets nothing at all.
    """

    if is_opted_out(contact) or (contact is not None and contact.block is not None):
        return True

    identities: list[SuppressedIdentity] = [*contact_identities(contact), *also]
    return bool(suppression_list.is_suppressed(business_id, identities))
