"""What a change of the deposit settings did to the pages guests pay on."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.deposits import PaymentPageChangeKind
from app.schemas.typings.deposits.strings import PaymentLinkHost


class PaymentPageChange(ImmutableDTO):
    """One page added, removed, made the default or named by a rule (its host)."""

    kind: PaymentPageChangeKind
    host: PaymentLinkHost
