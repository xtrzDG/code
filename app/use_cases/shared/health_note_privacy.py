"""
Who sees a booking's notes that hold health data (PRIV-10, Restricted):
the owner and the staff who serve the customer, by the role they act with
in the business (a brand's owner as an owner, its regional manager as
staff). An agency helper (no copies of customers' data) and platform
support looking in never do: they see that a note is withheld, not the
note (`is_health_note_withheld`). Notes without health data are shown to
everyone who sees the booking, as before.
"""

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.bookings import BookingView
from app.schemas.typings.bookings.booleans import SeesHealthNotes
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.brand_reach import acting_role
from app.utilities.brands.brand_access import direct_role
from app.utilities.privacy.health_notes import is_health_note

TEAM_SERVING_CUSTOMERS: frozenset[BusinessMemberRole] = frozenset(
    {BusinessMemberRole.OWNER, BusinessMemberRole.STAFF}
)


def sees_health_notes(
    brand_repo: BrandRepoContract | None,
    business: BusinessDocument,
    user_id: UserId,
) -> SeesHealthNotes:
    """
    Whether the person serves the business's customers (owner or staff);
    without the brands, by their own role in the business only.
    """

    role: BusinessMemberRole | None = (
        direct_role(business, user_id)
        if brand_repo is None
        else acting_role(brand_repo, business, user_id)
    )
    return role in TEAM_SERVING_CUSTOMERS


def protect_health_note(view: BookingView, sees_notes: SeesHealthNotes) -> BookingView:
    """The booking as this viewer may see it: a health note withheld."""

    if sees_notes or not is_health_note(view.notes):
        return view

    return view.model_copy(update={"notes": None, "is_health_note_withheld": True})
