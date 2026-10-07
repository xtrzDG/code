"""The team's card on a customer: tags and the VIP flag."""

import threading

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.customers.customer_settings import CustomerSettingsQuery
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.utilities.customers.customer_card import MAX_TAGS_PER_CUSTOMER
from tests.customers.customer_bed import CustomerBed


def stored(bed: CustomerBed, contact_id: ContactId) -> ContactDocument:
    contact = bed.customers.testbed.contact_repo.get(
        bed.customers.business.id, contact_id
    )
    assert contact is not None
    return contact


def test_the_owner_tags_a_customer_and_marks_them_vip() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact

    card = bed.tag(giorgi.id, "regular", "birthday in May", is_vip=True)

    assert [str(tag) for tag in card.tags] == ["regular", "birthday in May"]
    assert card.is_vip is True
    assert card.is_blocked is False
    assert [str(tag) for tag in card.known_tags] == ["regular", "birthday in May"]
    contact = stored(bed, giorgi.id)
    assert [mark.added_by for mark in contact.tags] == [bed.owner_id, bed.owner_id]
    assert contact.is_vip is True
    entry = bed.customers.testbed.audit_log_repo.list_by_business(
        bed.customers.business.id
    )[-1]
    assert (entry.action, entry.entity, entry.entity_id, entry.ip_address) == (
        AuditAction.UPDATE,
        "contact",
        str(giorgi.id),
        "192.0.2.10",
    )


def test_tags_compare_without_case_and_come_off_in_any_case() -> None:
    bed = CustomerBed()
    nino = bed.customers.nino.contact
    bed.tag(nino.id, "Regular", "Wine lover")

    again = bed.tag(nino.id, "REGULAR", "terrace")
    removed = bed.tag(nino.id, remove=("wine LOVER",))

    assert [str(tag) for tag in again.tags] == ["Regular", "Wine lover", "terrace"]
    assert [str(tag) for tag in removed.tags] == ["Regular", "terrace"]
    # The business's tags remember the latest used first, each once.
    assert [str(tag) for tag in removed.known_tags] == [
        "terrace",
        "Regular",
        "Wine lover",
    ]


def test_staff_tag_customers_and_unmark_vip() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact
    bed.tag(giorgi.id, is_vip=True)

    card = bed.tag(giorgi.id, "allergy: nuts", user_id=bed.staff_id, is_vip=False)

    assert [str(tag) for tag in card.tags] == ["allergy: nuts"]
    assert card.is_vip is False
    assert stored(bed, giorgi.id).tags[0].added_by == bed.staff_id


def test_a_customer_carries_at_most_twenty_tags() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact
    bed.tag(giorgi.id, *(f"tag {index}" for index in range(15)))

    card = bed.tag(giorgi.id, *(f"more {index}" for index in range(10)))

    assert len(card.tags) == MAX_TAGS_PER_CUSTOMER
    assert str(card.tags[-1]) == "more 4"


def test_customers_of_another_business_and_erased_ones_have_no_card() -> None:
    bed = CustomerBed()
    foreign = bed.customers.foreign.contact

    for contact_id in (foreign.id, ContactId()):
        with pytest.raises(NotFoundError):
            bed.tag(contact_id, "regular")

    giorgi = stored(bed, bed.customers.giorgi.contact.id)
    bed.customers.testbed.contact_repo.save(
        ContactDocument(
            id=giorgi.id,
            business_id=giorgi.business_id,
            erased_at=bed.customers.testbed.clock.now_microseconds(),
        )
    )
    with pytest.raises(ConflictError):
        bed.tag(giorgi.id, "regular")


def test_a_turn_saving_a_stale_contact_keeps_the_card() -> None:
    bed = CustomerBed()
    repo = bed.customers.testbed.contact_repo
    stale = stored(bed, bed.customers.giorgi.contact.id)
    bed.tag(stale.id, "regular", is_vip=True)
    bed.block(stale.id)

    stale.language = None
    repo.save(stale)

    contact = stored(bed, stale.id)
    assert contact.language is None
    assert [str(mark.tag) for mark in contact.tags] == ["regular"]
    assert contact.is_vip is True
    assert contact.block is not None
    assert contact.is_blocked is True


def test_two_colleagues_tagging_at_once_both_land() -> None:
    bed = CustomerBed()
    giorgi = bed.customers.giorgi.contact
    start_together = threading.Barrier(2)
    errors: list[Exception] = []

    def tag(user: str, label: str) -> None:
        try:
            start_together.wait(timeout=5)
            for index in range(5):
                bed.tag(
                    giorgi.id,
                    f"{label} {index}",
                    user_id=bed.owner_id if user == "owner" else bed.staff_id,
                )
        except Exception as error:  # reported below
            errors.append(error)

    threads = [
        threading.Thread(target=tag, args=("owner", "owner")),
        threading.Thread(target=tag, args=("staff", "staff")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert errors == []
    tags = {str(mark.tag) for mark in stored(bed, giorgi.id).tags}
    assert tags == {
        f"{who} {index}" for who in ("owner", "staff") for index in range(5)
    }
    settings = bed.get_settings.run(
        CustomerSettingsQuery(user_id=bed.owner_id, business_id=giorgi.business_id)
    )
    assert {str(tag) for tag in settings.known_tags} == tags
