"""
Connecting Google Calendar is bound to the flow and the session that
started it: the consent link carries a PKCE challenge (S256) whose
verifier is kept sealed and sent with the code exchange, the completion
must come on the same session, and the person must still own the business.
"""

import base64
import hashlib
from urllib.parse import parse_qs, urlsplit

from app.schemas.constants.calendar import CalendarConnectionFailure
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessMember
from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationState,
    CalendarCodeVerifier,
)
from app.schemas.typings.users.prefixed_id import UserId, UserSessionId
from app.use_cases.calendar.calendar_state import (
    code_challenge_of,
    generate_code_verifier,
    hash_authorization_state,
)
from tests.operations.calendar_world import CalendarWorld


def consent_query(calendar: CalendarWorld) -> dict[str, str]:
    url = str(calendar.start_view().authorization_url)
    return {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}


def test_the_challenge_is_the_s256_of_a_fresh_verifier() -> None:
    verifier = CalendarCodeVerifier("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")

    # RFC 7636, appendix B.
    assert str(code_challenge_of(verifier)) == (
        "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    )
    fresh = {str(generate_code_verifier()) for _ in range(20)}
    assert len(fresh) == 20
    assert all(43 <= len(value) <= 128 for value in fresh)


def test_the_verifier_is_sealed_and_proves_the_flow_at_the_exchange() -> None:
    calendar = CalendarWorld()
    query = consent_query(calendar)
    state = CalendarAuthorizationState(query["state"])
    stored = calendar.state_repo.find_by_state_hash(hash_authorization_state(state))
    assert stored is not None
    assert stored.session_id == calendar.session_id
    assert stored.sealed_code_verifier is not None
    verifier: str = str(calendar.cipher.decrypt(stored.sealed_code_verifier))
    assert verifier not in str(stored.sealed_code_verifier)
    assert query["code_challenge_method"] == "S256"
    assert query["code_challenge"] == base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()

    outcome = calendar.complete(state)

    assert outcome.failure is None
    [exchange] = [
        request
        for request in calendar.google.requests
        if request.url.host == "oauth2.googleapis.com"
    ]
    assert calendar.google.form(exchange)["code_verifier"] == verifier


def test_another_session_of_the_same_owner_cannot_finish_it() -> None:
    calendar = CalendarWorld()
    state = calendar.start()

    elsewhere = calendar.complete(state, session_id=UserSessionId())

    assert elsewhere.failure is CalendarConnectionFailure.LINK_EXPIRED
    assert elsewhere.business_id is None
    assert calendar.connection() is None
    assert not any(
        request.url.host == "oauth2.googleapis.com"
        for request in calendar.google.requests
    )
    # Not used up: the session that started it still finishes.
    assert calendar.complete(state).failure is None


def test_a_state_from_before_the_session_binding_is_never_finished() -> None:
    calendar = CalendarWorld()
    state = calendar.start()
    stored = calendar.state_repo.find_by_state_hash(hash_authorization_state(state))
    assert stored is not None
    calendar.state_repo.save(
        stored.model_copy(update={"session_id": None, "sealed_code_verifier": None})
    )

    assert calendar.complete(state).failure is CalendarConnectionFailure.LINK_EXPIRED
    assert calendar.connection() is None


def test_an_owner_removed_meanwhile_cannot_finish_connecting() -> None:
    calendar = CalendarWorld()
    state = calendar.start()
    business = calendar.world.business_repo.get(calendar.business.id)
    assert business is not None
    successor = UserId()
    business.members = [BusinessMember(user_id=successor, role=BusinessMemberRole.OWNER)]
    calendar.world.business_repo.save(business)

    outcome = calendar.complete(state)

    assert outcome.failure is CalendarConnectionFailure.LINK_EXPIRED
    assert outcome.business_id is None
    assert calendar.connection() is None
    assert not any(
        request.url.host == "oauth2.googleapis.com"
        for request in calendar.google.requests
    )
