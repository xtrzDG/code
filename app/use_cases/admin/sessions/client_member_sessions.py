"""What a platform admin sees of one member's sign-ins, without their contact."""

from typed_time_provider import Microseconds

from app.schemas.domain.businesses import BusinessMember
from app.schemas.domain.users import UserDocument, UserSessionDocument
from app.schemas.dto.admin_sessions import ClientMemberSessionsView
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.users.strings import MaskedLoginDestination
from app.utilities.security.login_destination_masking import (
    mask_e164_phone_number,
    mask_email_address,
)
from app.utilities.security.session_expiry import is_session_over


def member_sessions_view(
    member: BusinessMember,
    user: UserDocument | None,
    sessions: list[UserSessionDocument],
    now: Microseconds,
) -> ClientMemberSessionsView:
    """The member's live sessions counted, the latest use among them."""

    live: list[UserSessionDocument] = [
        session for session in sessions if not is_session_over(session, now)
    ]
    seen: list[int] = [
        int(session.last_seen_at or session.created_at) for session in live
    ]
    return ClientMemberSessionsView(
        user_id=member.user_id,
        role=member.role,
        display_name=None if user is None else user.display_name,
        masked_login=None if user is None else masked_login(user),
        live_session_count=DocumentCount(len(live)),
        last_seen_at=Microseconds(max(seen)) if seen else None,
    )


def masked_login(user: UserDocument) -> MaskedLoginDestination | None:
    if user.phone_number is not None:
        return mask_e164_phone_number(user.phone_number)

    if user.email is not None:
        return mask_email_address(user.email)

    return None
