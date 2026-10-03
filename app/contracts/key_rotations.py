"""The record of the latest re-encryption of the stored secrets."""

from collections.abc import Callable
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.key_rotations import KeyRotationDocument
from app.schemas.typings.security.prefixed_id import KeyRotationId


class KeyRotationRepoContract(RepoContract, Protocol):
    def get_latest(self) -> KeyRotationDocument | None:
        raise NotImplementedError

    def start(
        self,
        rotation: KeyRotationDocument,
        stale_before: Microseconds,
    ) -> bool:
        """
        Make the run the latest one, in one step, unless the latest is
        still queued or running and changed since `stale_before`. False,
        and nothing stored, when one is in progress.
        """
        raise NotImplementedError

    def update(
        self,
        rotation_id: KeyRotationId,
        change: Callable[[KeyRotationDocument], KeyRotationDocument],
    ) -> KeyRotationDocument | None:
        """
        Store what `change` makes of the run, in one step; None, and
        nothing written, when the latest run is another one.
        """
        raise NotImplementedError
