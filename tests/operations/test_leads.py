from datetime import datetime

import pytest

from app.schemas.constants.bookings import LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.dto.bookings import CreateLeadCommand, LeadView
from app.schemas.dto.operations.leads import (
    LeadPage,
    ListLeadsQuery,
    UpdateLeadStatusCommand,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import LeadId
from app.schemas.typings.bookings.strings import LeadBudgetText, LeadDetails
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from tests.operations.operations_world import OperationsWorld


class LeadsFixture:
    def __init__(self) -> None:
        self.world = OperationsWorld()
        self.business = self.world.add_business()
        self.contact = self.world.add_contact(self.business)

    def create(
        self,
        is_sandbox: bool = False,
        contact_id: ContactId | None = None,
    ) -> LeadView:
        return self.world.create_lead().run(
            CreateLeadCommand(
                business_id=self.business.id,
                contact_id=contact_id or self.contact.id,
                conversation_id=ConversationId(),
                contact_name=ContactName("Ketevan"),
                contact_phone_number=E164PhoneNumber("+995577112233"),
                lead_type=LeadType.BANQUET,
                details=LeadDetails("Wedding dinner with live music"),
                requested_date=LocalDate("2026-11-14"),
                party_size=PartySize(60),
                budget=LeadBudgetText("about 6000 lari"),
                source_channel=ChannelKind.INSTAGRAM,
                language=LanguageTag("ka"),
                is_sandbox=is_sandbox,
            )
        )


def test_lead_notifies_managers_with_all_details() -> None:
    leads = LeadsFixture()

    view = leads.create()

    assert view.status is LeadStatus.NEW
    texts = {
        str(contact.language): str(text) for contact, text in leads.world.notifier.sent
    }
    assert texts["ru"].splitlines() == [
        "Новая заявка · Salobie Bia",
        "Тип: Банкет",
        "Wedding dinner with live music",
        "Имя: Ketevan",
        "Телефон: +995 577 11 22 33",
        "Канал: Instagram",
        "Дата: суббота, 14 ноября 2026 г.",
        "Гостей: 60",
        "Бюджет: about 6000 lari",
    ]
    assert texts["ka"].startswith("ახალი მოთხოვნა · Salobie Bia\nტიპი: ბანკეტი")
    assert texts["en"] == (
        "New request · Salobie Bia\nBanquet · Saturday, November 14, 2026"
    )
    contact = leads.world.contact_repo.get(leads.business.id, leads.contact.id)
    assert contact is not None and contact.phone_number == "+995577112233"


def test_sandbox_lead_is_silent_and_unknown_contact_is_refused() -> None:
    leads = LeadsFixture()

    assert leads.create(is_sandbox=True).is_sandbox
    assert leads.world.notifier.sent == []
    with pytest.raises(NotFoundError):
        leads.create(contact_id=ContactId())


def test_list_and_update_leads() -> None:
    leads = LeadsFixture()
    first = leads.create()
    leads.create(is_sandbox=True)
    staff_id = UserId()

    updated = leads.world.update_lead_status().run(
        UpdateLeadStatusCommand(
            business_id=leads.business.id,
            lead_id=first.id,
            status=LeadStatus.IN_PROGRESS,
        )
    )
    listed = leads.world.list_leads().run(
        ListLeadsQuery(business_id=leads.business.id, actor_id=staff_id)
    )
    in_progress = leads.world.list_leads().run(
        ListLeadsQuery(
            business_id=leads.business.id,
            actor_id=staff_id,
            status=LeadStatus.NEW,
            include_sandbox=True,
        )
    )

    assert updated.status is LeadStatus.IN_PROGRESS
    assert [item.id for item in listed.items] == [first.id]
    assert listed.items[0].contact_name == "Ketevan"
    assert listed.items[0].contact_phone_number == "+995577112233"
    assert len(in_progress.items) == 1 and in_progress.items[0].is_sandbox
    view_entries = [
        entry
        for entry in leads.world.audit_repo.list_by_business(leads.business.id)
        if entry.action is AuditAction.VIEW
    ]
    [view] = view_entries
    assert view.record_count == 2 and view.actor_id == staff_id
    with pytest.raises(NotFoundError):
        leads.world.update_lead_status().run(
            UpdateLeadStatusCommand(
                business_id=leads.business.id,
                lead_id=LeadId(),
                status=LeadStatus.WON,
            )
        )


def test_leads_page_newest_first_with_status_counts() -> None:
    leads = LeadsFixture()
    created: list[LeadView] = []
    for minute in range(3):
        leads.world.clock.move_to(
            datetime.fromisoformat(f"2026-10-05T10:0{minute}:00+04:00")
        )
        created.append(leads.create())
    leads.world.update_lead_status().run(
        UpdateLeadStatusCommand(
            business_id=leads.business.id,
            lead_id=created[0].id,
            status=LeadStatus.WON,
        )
    )
    leads.create(is_sandbox=True)

    def page(
        cursor: PageCursor | None = None, status: LeadStatus | None = None
    ) -> LeadPage:
        return leads.world.list_leads().run(
            ListLeadsQuery(
                business_id=leads.business.id,
                actor_id=UserId(),
                status=status,
                page=PageRequest(size=PageSize(2), cursor=cursor),
            )
        )

    first = page()
    second = page(first.next_cursor)
    won = page(status=LeadStatus.WON)

    assert [item.id for item in first.items] == [created[2].id, created[1].id]
    assert [item.id for item in second.items] == [created[0].id]
    assert second.next_cursor is None
    assert [item.id for item in won.items] == [created[0].id]
    assert {count.status: int(count.count) for count in won.status_counts} == {
        LeadStatus.NEW: 2,
        LeadStatus.IN_PROGRESS: 0,
        LeadStatus.WON: 1,
        LeadStatus.LOST: 0,
    }
