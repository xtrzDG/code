"""
A full export is downloaded only through one-time links: an owner asks for
one (stepped up, audited), it works once, for ten minutes, for that owner
alone, an export opens at most three times, and every download is audited
and told to the owners with the address and the browser.
"""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.dto.businesses import InviteStaffCommand, InviteStaffRequest
from app.schemas.dto.privacy.business_exports import BusinessExportListQuery
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.privacy.constrained_strings import BusinessExportToken
from app.schemas.typings.privacy.prefixed_id import BusinessExportId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.privacy.export_download_tokens import (
    download_link_id,
    hash_download_token,
)
from tests.compliance.two_tenants import TwoTenants, seed_two_tenants
from tests.privacy.business_export_bed import (
    DOWNLOAD_IP,
    FIREFOX,
    BusinessExportBed,
)

MINUTE: int = 60
SECOND_OWNER_PHONE: str = "+995599111222"


def token_of(path: str) -> str:
    return path.rsplit("token=", 1)[-1]


def second_owner(tenants: TwoTenants) -> UserId:
    testbed = tenants.testbed
    owner = testbed.sign_in_with_phone(SECOND_OWNER_PHONE)
    testbed.invite_staff.run(
        InviteStaffCommand(
            user_id=tenants.owner_id,
            business_id=tenants.business.id,
            invitation=InviteStaffRequest(
                phone_number=RawPhoneNumberInput(SECOND_OWNER_PHONE),
                role=BusinessMemberRole.OWNER,
            ),
        )
    )
    return owner.user.id


def test_a_link_opens_once_for_ten_minutes() -> None:
    bed = BusinessExportBed(seed_two_tenants())
    ready = bed.ready_export()

    link = bed.link(ready.id)
    first = bed.download(str(link.download_path))

    assert first.content.startswith(b"PK")
    assert int(link.expires_at) == bed.clock.now_microseconds() + 10 * MINUTE * 10**6
    with pytest.raises(NotFoundError):
        bed.download(str(link.download_path))

    late = bed.link(ready.id)
    bed.clock.advance(10 * MINUTE + 1)
    with pytest.raises(NotFoundError):
        bed.download(str(late.download_path))


def test_a_link_works_only_for_the_owner_who_asked() -> None:
    tenants = seed_two_tenants()
    bed = BusinessExportBed(tenants)
    co_owner = second_owner(tenants)
    ready = bed.ready_export()
    path = str(bed.link(ready.id).download_path)

    with pytest.raises(NotFoundError):
        bed.download(path, user_id=co_owner)
    with pytest.raises(AccessDeniedError):
        bed.download(path, user_id=tenants.staff_id)
    with pytest.raises(AccessDeniedError):
        bed.link(ready.id, user_id=tenants.staff_id)

    assert bed.download(path).content.startswith(b"PK")
    assert bed.download(str(bed.link(ready.id, co_owner).download_path), co_owner)


def test_a_token_opens_only_its_own_export() -> None:
    bed = BusinessExportBed(seed_two_tenants())
    ready = bed.ready_export()
    path = str(bed.link(ready.id).download_path)

    with pytest.raises(NotFoundError):
        bed.download(path.replace(str(ready.id), str(BusinessExportId())))
    with pytest.raises(NotFoundError):
        bed.download(path.replace("token=", "token=A"))
    with pytest.raises(NotFoundError):
        bed.link(BusinessExportId())


def test_only_the_hash_of_a_token_is_kept() -> None:
    bed = BusinessExportBed(seed_two_tenants())
    ready = bed.ready_export()
    token = token_of(str(bed.link(ready.id).download_path))

    [stored] = bed.links.list_all()
    assert token not in stored.model_dump_json()
    assert stored.token_hash == hash_download_token(BusinessExportToken(token))
    assert stored.id == download_link_id(stored.token_hash)
    assert stored.user_id == bed.tenants.owner_id
    assert stored.used_at is None


def test_an_export_opens_at_most_three_times() -> None:
    bed = BusinessExportBed(seed_two_tenants())
    ready = bed.ready_export()
    spare = bed.link(ready.id)
    for _ in range(3):
        bed.download(str(bed.link(ready.id).download_path))

    [used_up] = bed.list.run(bed_query(bed)).items
    assert int(used_up.downloads_left) == 0
    with pytest.raises(ConflictError):
        bed.link(ready.id)
    with pytest.raises(ConflictError):
        bed.download(str(spare.download_path))


def test_every_download_is_audited_and_told_to_the_owners() -> None:
    bed = BusinessExportBed(seed_two_tenants())
    ready = bed.ready_export()

    bed.download(str(bed.link(ready.id).download_path))
    bed.download(str(bed.link(ready.id).download_path))

    entries = [
        entry
        for entry in bed.tenants.testbed.audit_log_repo.list_by_business(
            bed.tenants.business.id
        )
        if entry.action in (AuditAction.EXPORT, AuditAction.CREATE)
        and str(entry.entity) in {"business_export", "export_download_link"}
    ]
    downloads = [entry for entry in entries if str(entry.entity) == "business_export"]
    assert [int(entry.record_count or 0) for entry in downloads] == [1, 2]
    assert {str(entry.ip_address) for entry in downloads} == {DOWNLOAD_IP}
    assert all(entry.actor_id == bed.tenants.owner_id for entry in entries)
    assert len(entries) == 4
    assert [int(notice.download_number) for notice in bed.notices.notices] == [1, 2]
    [first, _] = bed.notices.notices
    assert str(first.client_ip_address) == DOWNLOAD_IP
    assert str(first.user_agent) == FIREFOX
    assert first.downloaded_by == bed.tenants.owner_id


def test_the_purge_deletes_expired_links() -> None:
    bed = BusinessExportBed(seed_two_tenants())
    ready = bed.ready_export()
    bed.link(ready.id)
    bed.clock.advance(10 * MINUTE + 1)
    fresh = bed.link(ready.id)

    bed.run_purge()

    [kept] = bed.links.list_all()
    assert kept.expires_at == fresh.expires_at


def bed_query(bed: BusinessExportBed) -> BusinessExportListQuery:
    return BusinessExportListQuery(
        user_id=bed.tenants.owner_id, business_id=bed.tenants.business.id
    )
