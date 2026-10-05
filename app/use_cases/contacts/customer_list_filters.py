"""The customer list's filters: a tag, VIPs or blocked customers."""

from app.schemas.constants.customers import CustomerListFilter
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.contacts import ContactListQuery
from app.schemas.dto.customers.customer_records import CustomerPageFilter
from app.utilities.customers.customer_card import tag_key


def page_filter_of(query: ContactListQuery) -> CustomerPageFilter:
    """The filter the database applies to a page of the list."""

    return CustomerPageFilter(
        tag=query.tag,
        vip_only=query.list_filter is CustomerListFilter.VIP,
        blocked_only=query.list_filter is CustomerListFilter.BLOCKED,
    )


def accepts(page_filter: CustomerPageFilter, contact: ContactDocument) -> bool:
    """The same filter on one contact (a search walks without the database's)."""

    if page_filter.vip_only and not contact.is_vip:
        return False

    if page_filter.blocked_only and contact.block is None:
        return False

    return page_filter.tag is None or tag_key(page_filter.tag) in {
        mark.key for mark in contact.tags
    }
