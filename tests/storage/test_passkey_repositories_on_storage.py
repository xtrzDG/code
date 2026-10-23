"""
Passkeys on both storages: one credential is one passkey, a use counts
only from the counter it was checked against (compare-and-swap), a
suspended passkey signs nothing more, and a ceremony's challenge is taken
once, also by parallel requests (threads released together by a barrier).
"""

import threading
from collections.abc import Callable

import pytest
from typed_time_provider import Microseconds

from app.repositories.passkey_repositories import (
    PasskeyChallengeRepository,
    PasskeyRepository,
)
from app.schemas.constants.passkeys import PasskeyCeremonyPurpose
from app.schemas.domain.passkeys import PasskeyChallengeDocument, PasskeyDocument
from app.schemas.typings.passkeys.constrained_integers import WebAuthnSignCount
from app.schemas.typings.passkeys.constrained_strings import (
    PasskeyName,
    WebAuthnChallenge,
    WebAuthnCredentialId,
    WebAuthnPublicKey,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.passkey_identity import passkey_id_for
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import CollectionFactory

pytestmark = pytest.mark.usefixtures("platform_scope")

NOW: Microseconds = Microseconds(1_800_000_000_000_000)
PARALLEL_REQUESTS: int = 8
PUBLIC_KEY: WebAuthnPublicKey = WebAuthnPublicKey("pQECAyYgASFYI" + "A" * 43)


def passkey(user_id: UserId, credential: str, created_at: int = 1) -> PasskeyDocument:
    credential_id = WebAuthnCredentialId(credential)
    return PasskeyDocument(
        id=passkey_id_for(credential_id),
        user_id=user_id,
        credential_id=credential_id,
        public_key=PUBLIC_KEY,
        sign_count=WebAuthnSignCount(1),
        name=PasskeyName("Security key"),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def challenge(user_id: UserId, created_at: int) -> PasskeyChallengeDocument:
    return PasskeyChallengeDocument(
        user_id=user_id,
        purpose=PasskeyCeremonyPurpose.SIGN_IN,
        challenge=WebAuthnChallenge("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"),
        expires_at=Microseconds(created_at + 300_000_000),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def all_at_once[Result](
    storage_scope: StorageScopeContext, attempt: Callable[[], Result]
) -> list[Result]:
    """Run `attempt` in parallel threads released together; their results."""

    results: list[Result] = []
    errors: list[BaseException] = []
    lock = threading.Lock()
    start = threading.Barrier(PARALLEL_REQUESTS)

    def run() -> None:
        try:
            start.wait()
            with storage_scope.platform_wide():
                result = attempt()
            with lock:
                results.append(result)
        except BaseException as error:  # pragma: no cover - reported below
            errors.append(error)

    threads = [threading.Thread(target=run) for _ in range(PARALLEL_REQUESTS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    return results


def test_one_credential_is_one_passkey_and_a_person_lists_their_own(
    collections: CollectionFactory,
) -> None:
    repo = PasskeyRepository(collections(PasskeyDocument, "passkeys"))
    owner, stranger = UserId(), UserId()

    assert repo.add(passkey(owner, "Y3JlZGVudGlhbC1vbmUtMDAwMDAw", created_at=1))
    assert repo.add(passkey(owner, "Y3JlZGVudGlhbC10d28tMDAwMDAw", created_at=2))
    # The same credential again, even for another person, adds nothing.
    assert not repo.add(passkey(stranger, "Y3JlZGVudGlhbC1vbmUtMDAwMDAw"))

    listed = repo.list_for_user(owner)
    assert [str(item.credential_id) for item in listed] == [
        "Y3JlZGVudGlhbC10d28tMDAwMDAw",
        "Y3JlZGVudGlhbC1vbmUtMDAwMDAw",
    ]
    assert int(repo.count_for_user(owner)) == 2
    assert repo.list_for_user(stranger) == []


def test_a_use_counts_only_from_the_counter_it_was_checked_against(
    collections: CollectionFactory, storage_scope: StorageScopeContext
) -> None:
    repo = PasskeyRepository(collections(PasskeyDocument, "passkeys"))
    stored = passkey(UserId(), "Y3JlZGVudGlhbC1yYWNlLTAwMDAw")
    repo.add(stored)

    uses = all_at_once(
        storage_scope,
        lambda: repo.record_use(
            stored.id, WebAuthnSignCount(1), WebAuthnSignCount(2), NOW
        ),
    )

    accepted = [use for use in uses if use is not None]
    assert len(accepted) == 1
    assert int(accepted[0].sign_count) == 2
    assert accepted[0].last_used_at == NOW
    # A stale counter is refused after the winner moved it.
    assert (
        repo.record_use(stored.id, WebAuthnSignCount(1), WebAuthnSignCount(3), NOW)
        is None
    )


def test_a_suspended_passkey_signs_nothing_more(
    collections: CollectionFactory,
) -> None:
    repo = PasskeyRepository(collections(PasskeyDocument, "passkeys"))
    stored = passkey(UserId(), "Y3JlZGVudGlhbC1jbG9uZS0wMDAw")
    repo.add(stored)

    first = repo.mark_clone_suspected(stored.id, NOW)
    again = repo.mark_clone_suspected(stored.id, Microseconds(int(NOW) + 5))

    assert first is not None and first.clone_suspected_at == NOW
    assert again is not None and again.clone_suspected_at == NOW
    assert (
        repo.record_use(stored.id, WebAuthnSignCount(1), WebAuthnSignCount(2), NOW)
        is None
    )
    assert repo.delete(stored.id)
    assert repo.mark_clone_suspected(stored.id, NOW) is None
    assert not repo.delete(stored.id)


def test_a_ceremony_challenge_is_taken_once_and_purged_by_age(
    collections: CollectionFactory, storage_scope: StorageScopeContext
) -> None:
    repo = PasskeyChallengeRepository(
        collections(PasskeyChallengeDocument, "passkey_challenges")
    )
    user_id = UserId()
    fresh = challenge(user_id, created_at=int(NOW))
    stale = challenge(user_id, created_at=int(NOW) - 2 * 86_400_000_000)
    repo.save(fresh)
    repo.save(stale)

    taken = all_at_once(storage_scope, lambda: repo.consume(fresh.id, NOW))

    winners = [item for item in taken if item is not None]
    assert len(winners) == 1
    assert winners[0].is_consumed is True
    assert repo.consume(fresh.id, NOW) is None
    assert int(repo.delete_created_before(Microseconds(int(NOW) - 86_400_000_000))) == 1
    assert repo.get(stale.id) is None
    assert repo.get(fresh.id) is not None
