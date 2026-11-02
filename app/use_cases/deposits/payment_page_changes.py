"""
Which changes of the deposit settings touch the pages guests pay on: a page
added or removed, another default template, a deposit rule pointed at
another page. Such a change needs a fresh confirmation of the person
(step-up) and is told to the owners (`payment_page_notices`); deposits
switched on or off, hold times and amounts are neither.
"""

from dataclasses import dataclass

from app.schemas.constants.deposits import PaymentPageChangeKind
from app.schemas.domain.deposits import DepositSettingsDocument
from app.schemas.dto.deposits.payment_page_changes import PaymentPageChange
from app.schemas.typings.deposits.prefixed_id import PaymentLinkId
from app.schemas.typings.deposits.strings import PaymentLinkHost


@dataclass(frozen=True)
class PaymentPageState:
    """The pages of the settings (by id, with their hosts) and who uses which."""

    pages: dict[PaymentLinkId, PaymentLinkHost]
    default_page: PaymentLinkId | None
    rule_pages: frozenset[PaymentLinkId]


def payment_page_state(settings: DepositSettingsDocument) -> PaymentPageState:
    """A copy of the pages' state, taken before the settings are edited in place."""

    return PaymentPageState(
        pages={link.id: link.host for link in settings.payment_links},
        default_page=settings.default_payment_link_id,
        rule_pages=frozenset(
            entry.policy.payment_link_id
            for entry in settings.policies
            if entry.policy.payment_link_id is not None
        ),
    )


def payment_page_changes(
    before: PaymentPageState, after: PaymentPageState
) -> list[PaymentPageChange]:
    """What changed for the pages, in a stable order (empty: nothing did)."""

    changes: list[PaymentPageChange] = [
        PaymentPageChange(kind=PaymentPageChangeKind.ADDED, host=host)
        for page_id, host in after.pages.items()
        if page_id not in before.pages
    ]
    changes.extend(
        PaymentPageChange(kind=PaymentPageChangeKind.REMOVED, host=host)
        for page_id, host in before.pages.items()
        if page_id not in after.pages
    )
    named: list[tuple[PaymentPageChangeKind, PaymentLinkId]] = []
    if after.default_page is not None and after.default_page != before.default_page:
        named.append((PaymentPageChangeKind.DEFAULT_CHANGED, after.default_page))
    named.extend(
        (PaymentPageChangeKind.RULE_PAGE_CHANGED, page_id)
        for page_id in sorted(after.rule_pages - before.rule_pages, key=str)
    )
    # A default or a rule names only a page of the settings.
    changes.extend(
        PaymentPageChange(kind=kind, host=after.pages[page_id])
        for kind, page_id in named
        if page_id in after.pages
    )
    return changes
