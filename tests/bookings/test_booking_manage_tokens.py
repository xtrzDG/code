"""Signed booking manage links: what they prove, when they stop opening."""

import base64
from datetime import UTC, datetime

import pytest
from typed_time_provider import Microseconds

from app.schemas.domain.profiles import BusinessAddress
from app.schemas.dto.booking_manage import BookingManageClaims
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.constrained_strings import BookingManageToken
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.platform.strings import PlatformSecret
from app.use_cases.bookings.public.open_booking_manage_link_use_case import (
    OpenBookingManageLinkUseCase,
)
from app.utilities.bookings.booking_manage_links import (
    build_manage_link,
    choose_maps_url,
    manage_link_expiry,
)
from app.utilities.security.booking_manage_token_signer import (
    BookingManageTokenSigner,
)
from tests.operations.fakes import MovableClock

KEY: PlatformSecret = PlatformSecret("test-encryption-key-0000")  # gitleaks:allow
OLD_KEY: PlatformSecret = PlatformSecret("test-encryption-key-1111")  # gitleaks:allow
STARTS_AT: int = 1_791_298_800  # 2026-10-06 19:00 in Tbilisi
ENDS_AT: int = STARTS_AT + 2 * 60 * 60
NOW: datetime = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def claims(
    business_id: BusinessId | None = None,
    booking_id: BookingId | None = None,
) -> BookingManageClaims:
    return BookingManageClaims(
        business_id=business_id or BusinessId(),
        booking_id=booking_id or BookingId(),
        booking_version=BookingStartsAtUnixSeconds(STARTS_AT),
        expires_at=manage_link_expiry(BookingEndsAtUnixSeconds(ENDS_AT)),
    )


def tampered(token: BookingManageToken, position: int) -> BookingManageToken:
    text: str = str(token)
    replacement: str = "A" if text[position] != "A" else "B"
    return BookingManageToken(text[:position] + replacement + text[position + 1 :])


def test_a_signed_link_reads_back_as_its_claims() -> None:
    signer = BookingManageTokenSigner(KEY)
    issued = claims()

    token = signer.sign(issued)

    assert len(str(token)) == 71
    assert signer.read(token) == issued
    # Another process with the same ENCRYPTION_KEY reads it too.
    assert BookingManageTokenSigner(KEY).read(token) == issued


@pytest.mark.parametrize("position", [0, 5, 20, 40, 52, 60, 70])
def test_an_altered_link_proves_nothing(position: int) -> None:
    signer = BookingManageTokenSigner(KEY)
    token = signer.sign(claims())

    assert signer.read(tampered(token, position)) is None


def test_claims_cannot_be_swapped_under_a_kept_signature() -> None:
    signer = BookingManageTokenSigner(KEY)
    business_a, business_b = BusinessId(), BusinessId()
    booking_id = BookingId()
    raw_a = base64.urlsafe_b64decode(
        str(signer.sign(claims(business_a, booking_id))) + "="
    )
    raw_b = base64.urlsafe_b64decode(
        str(signer.sign(claims(business_b, booking_id))) + "="
    )

    # Business B's payload with business A's signature.
    forged = base64.urlsafe_b64encode(raw_b[:41] + raw_a[41:]).rstrip(b"=").decode()

    assert signer.read(BookingManageToken(forged)) is None


def test_a_link_of_another_key_or_of_garbage_is_refused() -> None:
    token = BookingManageTokenSigner(OLD_KEY).sign(claims())

    assert BookingManageTokenSigner(KEY).read(token) is None
    garbage = BookingManageToken("A" * 71)
    assert BookingManageTokenSigner(KEY).read(garbage) is None
    short = BookingManageToken("A" * 40)
    assert BookingManageTokenSigner(KEY).read(short) is None


def test_links_signed_before_a_key_rotation_still_open() -> None:
    issued = claims()
    old_token = BookingManageTokenSigner(OLD_KEY).sign(issued)
    rotated = BookingManageTokenSigner(KEY, previous_keys=(OLD_KEY,))

    assert rotated.read(old_token) == issued
    # New links are signed with the current key only.
    assert BookingManageTokenSigner(OLD_KEY).read(rotated.sign(issued)) is None


def test_without_encryption_key_links_work_within_the_process() -> None:
    signer = BookingManageTokenSigner(None)
    issued = claims()

    assert signer.read(signer.sign(issued)) == issued
    assert BookingManageTokenSigner(None).read(signer.sign(issued)) is None


def test_the_link_opens_until_a_month_after_the_booking_ends() -> None:
    clock = MovableClock(NOW)
    signer = BookingManageTokenSigner(KEY)
    issued = claims()
    open_link = OpenBookingManageLinkUseCase(signer, clock.wall_clock)
    assert int(issued.expires_at) == (ENDS_AT + 30 * 86_400) * 1_000_000

    assert open_link.run(signer.sign(issued)) == issued

    clock.move_to(datetime.fromtimestamp(ENDS_AT + 30 * 86_400, tz=UTC))
    with pytest.raises(NotFoundError) as expired:
        open_link.run(signer.sign(issued))
    assert [str(reason.code) for reason in expired.value.reasons] == ["link_expired"]

    with pytest.raises(NotFoundError) as forged:
        open_link.run(tampered(signer.sign(issued), 30))
    assert [str(reason.code) for reason in forged.value.reasons] == ["link_invalid"]


def test_an_expiry_in_the_past_is_kept_in_whole_seconds() -> None:
    signer = BookingManageTokenSigner(KEY)
    issued = claims().model_copy(update={"expires_at": Microseconds(1_500_000)})

    assert signer.read(signer.sign(issued)) == issued.model_copy(
        update={"expires_at": Microseconds(1_000_000)}
    )


def test_the_manage_link_lives_on_the_cabinet_site() -> None:
    token = BookingManageTokenSigner(KEY).sign(claims())

    link = build_manage_link(CabinetBaseUrl("https://app.workshop.example/"), token)

    assert str(link) == f"https://app.workshop.example/r/{token}"
    assert build_manage_link(None, token) is None


def test_the_map_link_is_the_owners_or_a_search_of_the_address() -> None:
    owner_link = WebLink("https://maps.example/salobie")
    with_link = BusinessAddress(
        text=AddressText("Tbilisi, Rustaveli 1"), maps_url=owner_link
    )
    without_link = BusinessAddress(text=AddressText("Тбилиси,  проспект Руставели 1"))

    assert choose_maps_url(with_link) == owner_link
    assert str(choose_maps_url(without_link)) == (
        "https://www.google.com/maps/search/?api=1&query="
        "%D0%A2%D0%B1%D0%B8%D0%BB%D0%B8%D1%81%D0%B8%2C%20"
        "%D0%BF%D1%80%D0%BE%D1%81%D0%BF%D0%B5%D0%BA%D1%82%20"
        "%D0%A0%D1%83%D1%81%D1%82%D0%B0%D0%B2%D0%B5%D0%BB%D0%B8%201"
    )
    assert choose_maps_url(None) is None
