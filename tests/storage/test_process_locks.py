"""Named locks of one process: the in-memory advisory locks and the first
stage of the Postgres ones."""

import threading
import time

import pytest

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.adapters.locks.process_locks import ProcessLocks, describe_lock_purpose
from app.registries.locks.customer_message_lock_registry import (
    CustomerMessageLockRegistry,
)
from app.registries.locks.login_code_send_lock_registry import (
    LoginCodeSendLockRegistry,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

FIRST: AdvisoryLockKey = AdvisoryLockKey("customer messages|biz_a|web|visitor")
SECOND: AdvisoryLockKey = AdvisoryLockKey("bookings|biz_a")


def test_a_key_is_reentrant_and_forgotten_once_nobody_uses_it() -> None:
    locks = ProcessLocks()

    with locks.held(FIRST, 1.0), locks.held(FIRST, 1.0), locks.held(SECOND, 1.0):
        assert set(locks._locks) == {FIRST, SECOND}  # pyright: ignore[reportPrivateUsage]

    assert locks._locks == {}  # pyright: ignore[reportPrivateUsage]


def test_a_busy_key_refuses_after_the_wait_without_naming_ids() -> None:
    locks = ProcessLocks()
    holding, release = threading.Event(), threading.Event()

    def hold() -> None:
        with locks.held(FIRST, 1.0):
            holding.set()
            release.wait(5)

    holder = threading.Thread(target=hold)
    holder.start()
    assert holding.wait(5)
    started = time.monotonic()
    with pytest.raises(ExternalServiceError) as refusal, locks.held(FIRST, 0.2):
        pytest.fail("the key was busy")
    waited = time.monotonic() - started
    # Another key is not held up.
    with locks.held(SECOND, 0.2):
        pass
    release.set()
    holder.join()

    assert 0.15 <= waited < 1.0
    assert str(refusal.value).startswith("The customer messages lock stayed busy")
    assert "visitor" not in str(refusal.value)
    assert locks._locks == {}  # pyright: ignore[reportPrivateUsage]


def test_the_purpose_of_a_key() -> None:
    assert describe_lock_purpose(FIRST) == "customer messages"
    assert describe_lock_purpose(AdvisoryLockKey("login code sends")) == (
        "login code sends"
    )


def test_one_customers_turns_wait_for_each_other_and_others_do_not() -> None:
    registry = CustomerMessageLockRegistry(InMemoryAdvisoryLockAdapter())
    business_id = BusinessId()
    events: list[str] = []
    holding = threading.Event()

    def first_turn() -> None:
        with registry.lock_for_customer(
            business_id, ChannelKind.WEB_CHAT, ChannelUserId("visitor-1")
        ):
            holding.set()
            time.sleep(0.1)
            events.append("first turn done")

    turn = threading.Thread(target=first_turn)
    turn.start()
    assert holding.wait(5)
    with registry.lock_for_customer(
        business_id, ChannelKind.WEB_CHAT, ChannelUserId("visitor-2")
    ):
        events.append("another customer")
    with registry.lock_for_customer(
        business_id, ChannelKind.WEB_CHAT, ChannelUserId("visitor-1")
    ):
        events.append("second turn")
    turn.join()

    assert events == ["another customer", "first turn done", "second turn"]


def test_the_login_code_send_lock_is_one_lock() -> None:
    adapter = InMemoryAdvisoryLockAdapter()
    first, second = (
        LoginCodeSendLockRegistry(adapter),
        LoginCodeSendLockRegistry(adapter),
    )
    holding, release = threading.Event(), threading.Event()

    def hold() -> None:
        with first.lock():
            holding.set()
            release.wait(5)

    holder = threading.Thread(target=hold)
    holder.start()
    assert holding.wait(5)
    with (
        pytest.raises(ExternalServiceError),
        adapter.hold_with_transaction(
            AdvisoryLockKey("login code sends"), LockWaitSeconds(1)
        ),
    ):
        pytest.fail("the send lock was busy")
    release.set()
    holder.join()
    with second.lock():
        pass
