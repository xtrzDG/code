"""Checking a passkey's answer to a sign-in step or a step-up."""

import logging

from typed_time_provider import Microseconds

from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.schemas.domain.passkeys import PasskeyChallengeDocument, PasskeyDocument
from app.schemas.dto.passkey_ceremonies import PasskeyAssertionCredential
from app.schemas.dto.passkey_checks import CheckedAssertion
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.use_cases.users.passkeys.passkey_records import audit_passkey_suspended
from app.utilities.security.passkey_policy import (
    clone_suspected,
    is_sign_count_regressed,
    passkey_rejected,
)

logger: logging.Logger = logging.getLogger(__name__)


class PasskeyAssertionCheck:
    """
    A passkey's signature counts when it is one of the person's passkeys
    (not suspected of a copy), its signature checks out against the taken
    challenge, and its counter grew since the last use. A counter that did
    not grow comes from a copied authenticator: the answer is refused and
    the passkey stops signing for good (MFA_CHANGED). The new counter is
    stored by compare-and-swap, so of two answers that read the same
    counter only one counts.
    """

    def __init__(
        self,
        passkey_repo: PasskeyRepoContract,
        ceremony: PasskeyCeremonyAdapterContract,
        audit_log_repo: AuditLogRepoContract,
    ) -> None:
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._ceremony: PasskeyCeremonyAdapterContract = ceremony
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo

    def verify(
        self,
        challenge: PasskeyChallengeDocument,
        credential: PasskeyAssertionCredential,
        client_ip_address: ClientIpAddress | None,
        now: Microseconds,
    ) -> PasskeyDocument:
        """
        Raises:
            PasskeyRejectedError: not the person's passkey, a bad signature,
                a copied authenticator, or a parallel answer came first.
        """

        passkey: PasskeyDocument | None = next(
            (
                stored
                for stored in self._passkey_repo.list_for_user(challenge.user_id)
                if stored.credential_id == credential.id
            ),
            None,
        )
        if passkey is None:
            raise passkey_rejected()

        if passkey.clone_suspected_at is not None:
            raise clone_suspected()

        checked: CheckedAssertion = self._ceremony.check_assertion(
            credential, challenge.challenge, passkey
        )
        if is_sign_count_regressed(passkey.sign_count, checked.sign_count):
            self._passkey_repo.mark_clone_suspected(passkey.id, now)
            audit_passkey_suspended(
                self._audit_log_repo, passkey, client_ip_address, now
            )
            logger.warning(
                "Passkey %s reported a signature counter that did not grow; "
                "it signs nothing more.",
                passkey.id,
            )
            raise clone_suspected()

        used: PasskeyDocument | None = self._passkey_repo.record_use(
            passkey.id, passkey.sign_count, checked.sign_count, now
        )
        if used is None:
            raise passkey_rejected()

        return used
