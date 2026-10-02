"""Connecting Google Calendar: stored tokens, who completes it, refusals, disconnect."""

import hashlib
from datetime import datetime
from urllib.parse import parse_qs, urlsplit

import pytest

from app.schemas.constants.calendar import CalendarConnectionFailure
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationState,
    CalendarAuthorizationStateHash,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from tests.operations.calendar_world import CalendarWorld


class TestConnection:
    def test_connect_stores_encrypted_tokens_and_only_the_state_hash(self) -> None:
        calendar = CalendarWorld()

        view = calendar.start_view()
        state = CalendarAuthorizationState(
            parse_qs(urlsplit(str(view.authorization_url)).query)["state"][0]
        )
        state_hash = CalendarAuthorizationStateHash(
            hashlib.sha256(str(state).encode()).hexdigest()
        )
        pending = calendar.state_repo.find_by_state_hash(state_hash)
        assert pending is not None
        assert pending.business_id == calendar.business.id
        assert int(view.expires_at) - int(calendar.world.clock.now_microseconds()) == (
            10 * 60 * 1_000_000
        )

        outcome = calendar.complete(state)

        assert outcome.failure is None
        assert outcome.business_id == calendar.business.id
        assert outcome.connection is not None
        connection = calendar.connection()
        assert connection is not None
        assert connection.calendar_id == "primary"
        assert connection.calendar_name == "owner@example.com"
        assert connection.connected_by == calendar.owner_id
        assert "refresh-initial" not in str(connection.encrypted_refresh_token)
        assert calendar.cipher.decrypt(connection.encrypted_refresh_token) == (
            "refresh-initial"
        )
        replayed = calendar.complete(state)
        assert replayed.failure is CalendarConnectionFailure.LINK_EXPIRED
        assert replayed.business_id == calendar.business.id
        assert replayed.connection is None

    def test_only_the_user_who_started_can_complete_the_connection(self) -> None:
        calendar = CalendarWorld()
        state = calendar.start()

        foreign = calendar.complete(state, user_id=UserId())

        assert foreign.failure is CalendarConnectionFailure.LINK_EXPIRED
        assert foreign.business_id is None
        assert calendar.connection() is None
        assert not any(
            request.url.host == "oauth2.googleapis.com"
            for request in calendar.google.requests
        )
        # The state is not used up: the owner can still finish.
        owner = calendar.complete(state)
        assert owner.failure is None
        assert calendar.connection() is not None

    def test_expired_forged_and_refused_authorizations(self) -> None:
        calendar = CalendarWorld()
        state = calendar.start()
        calendar.world.clock.move_to(
            datetime.fromisoformat("2026-10-05T08:11:00+00:00")
        )

        expired = calendar.complete(state)
        assert expired.failure is CalendarConnectionFailure.LINK_EXPIRED
        assert expired.business_id == calendar.business.id

        forged = calendar.complete(CalendarAuthorizationState("forged-state"))
        assert forged.failure is CalendarConnectionFailure.LINK_EXPIRED
        assert forged.business_id is None
        assert calendar.complete(None, code=None).business_id is None

        declined = calendar.complete(
            calendar.start(), code=None, provider_error="access_denied"
        )
        assert declined.failure is CalendarConnectionFailure.ACCESS_DENIED
        assert declined.business_id == calendar.business.id
        odd_error = calendar.complete(
            calendar.start(), code=None, provider_error="server_error"
        )
        assert odd_error.failure is CalendarConnectionFailure.PROVIDER_ERROR

        bad_code = calendar.complete(calendar.start(), code="bad-code")
        assert bad_code.failure is CalendarConnectionFailure.PROVIDER_ERROR

        calendar.google.grants_refresh_token = False
        no_offline = calendar.complete(calendar.start())
        assert no_offline.failure is CalendarConnectionFailure.NO_OFFLINE_ACCESS

        with pytest.raises(NotFoundError):
            calendar.start_view(BusinessId())

        assert calendar.connection() is None

    def test_a_failed_title_lookup_does_not_stop_the_connection(self) -> None:
        calendar = CalendarWorld()
        calendar.google.calendar_name = None

        assert calendar.complete(calendar.start()).failure is None

        connection = calendar.connection()
        assert connection is not None
        assert connection.calendar_name is None

    def test_disconnect_revokes_the_token_and_forgets_events(self) -> None:
        calendar = CalendarWorld()
        calendar.complete(calendar.start())
        calendar.sync.sync(calendar.booking())

        assert calendar.disconnect()
        assert calendar.google.revoked_tokens == ["refresh-initial"]
        assert calendar.connection() is None
        assert calendar.link_repo.list_by_business(calendar.business.id) == []
        assert not calendar.disconnect()

        calendar.complete(calendar.start())
        calendar.google.failure_status = 503
        assert calendar.disconnect()
        assert calendar.connection() is None
