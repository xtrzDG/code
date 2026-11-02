"""
Session writes that race on both stores (in memory and Postgres): a use
never moves a session's end later than the stored one, a rotation's
wind-down cannot be undone by a use read before it, and a rotation ticket
is taken once.
"""

from concurrent.futures import ThreadPoolExecutor

import pytest
from typed_time_provider import Microseconds

from app.repositories.user_repositories import UserSessionRepository
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.sessions import SessionActivity
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessTokenHash
from app.utilities.security.session_rotation_tickets import (
    generate_rotation_ticket,
    hash_rotation_ticket,
)
from tests.storage.conftest import CollectionFactory
from tests.storage.storage_testing import FIXED_NANOSECONDS

pytestmark = pytest.mark.usefixtures("platform_scope")

NOW: int = FIXED_NANOSECONDS // 1_000
SECOND: int = 1_000_000
DAY: int = 24 * 3600 * SECOND


def sessions(collections: CollectionFactory) -> UserSessionRepository:
    return UserSessionRepository(collections(UserSessionDocument, "user_sessions"))


def two_week_session() -> UserSessionDocument:
    return UserSessionDocument(
        user_id=UserId(),
        token_hash=AccessTokenHash("b" * 64),
        expires_at=Microseconds(NOW + 14 * DAY),
        idle_expires_at=Microseconds(NOW + 7 * DAY),
        auth_level=AuthLevel.ONE_FACTOR,
        authenticated_at=Microseconds(NOW),
        created_at=Microseconds(NOW),
        updated_at=Microseconds(NOW),
    )


def use(at: int, expires_at: int, idle_expires_at: int) -> SessionActivity:
    return SessionActivity(
        seen_at=Microseconds(at),
        expires_at=Microseconds(expires_at),
        idle_expires_at=Microseconds(idle_expires_at),
    )


def test_a_use_never_moves_the_end_later(collections: CollectionFactory) -> None:
    repo = sessions(collections)
    session = two_week_session()
    repo.save(session)

    recorded = repo.record_activity(
        session.id, use(NOW + SECOND, NOW + 30 * DAY, NOW + 31 * DAY)
    )

    assert recorded is not None
    assert (recorded.expires_at, recorded.idle_expires_at) == (
        session.expires_at,
        session.expires_at,
    )
    stored = repo.get(session.id)
    assert stored is not None
    assert (stored.expires_at, stored.idle_expires_at, stored.last_seen_at) == (
        session.expires_at,
        session.expires_at,
        NOW + SECOND,
    )


def test_a_use_read_before_a_wind_down_cannot_undo_it(
    collections: CollectionFactory,
) -> None:
    repo = sessions(collections)
    session = two_week_session()
    repo.save(session)
    ticket = generate_rotation_ticket()
    repo.hold_rotation_ticket(
        session.id,
        hash_rotation_ticket(ticket),
        Microseconds(NOW),
        Microseconds(NOW + 120 * SECOND),
    )
    # A request read the session before the rotation and computed its use.
    stale = use(NOW + SECOND, int(session.expires_at), NOW + 7 * DAY + SECOND)

    taken = repo.take_rotation_ticket(
        session.id,
        hash_rotation_ticket(ticket),
        Microseconds(NOW + SECOND),
        Microseconds(NOW + 31 * SECOND),
    )
    repo.record_activity(session.id, stale)

    assert taken is not None
    assert taken.rotation_proven_at == NOW
    wound = repo.get(session.id)
    assert wound is not None
    assert (wound.expires_at, wound.idle_expires_at) == (
        NOW + 31 * SECOND,
        NOW + 31 * SECOND,
    )
    assert (wound.auth_level, wound.authenticated_at, wound.rotated_at) == (
        AuthLevel.ONE_FACTOR,
        None,
        NOW + SECOND,
    )
    assert wound.rotation_ticket_hash is None


def test_a_ticket_is_taken_once(collections: CollectionFactory) -> None:
    repo = sessions(collections)
    session = two_week_session()
    repo.save(session)
    ticket_hash = hash_rotation_ticket(generate_rotation_ticket())
    repo.hold_rotation_ticket(
        session.id, ticket_hash, Microseconds(NOW), Microseconds(NOW + 120 * SECOND)
    )

    def take(_: int) -> UserSessionDocument | None:
        return repo.take_rotation_ticket(
            session.id,
            ticket_hash,
            Microseconds(NOW + SECOND),
            Microseconds(NOW + 31 * SECOND),
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        taken = [result for result in pool.map(take, range(4)) if result is not None]

    assert len(taken) == 1
    assert (
        repo.hold_rotation_ticket(
            session.id, ticket_hash, Microseconds(NOW), Microseconds(NOW + SECOND)
        )
        is None
    )
    assert (
        repo.record_authentication(
            session.id, AuthLevel.TWO_FACTOR, Microseconds(NOW + 2 * SECOND)
        )
        is None
    )
