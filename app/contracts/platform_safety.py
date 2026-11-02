"""
The platform's safety switches and watchers: the global pause, the daily
budget stop's spend reading, the periodic jobs' heartbeats and the daily
payment reconciliation with the payment providers.
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.contracts.registry_contract import RegistryContract
from app.contracts.repo_contract import RepoContract
from app.schemas.domain.payment_reconciliations import PaymentReconciliationDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.domain.periodic_job_heartbeats import PeriodicJobHeartbeatDocument
from app.schemas.domain.platform_pauses import PlatformPauseDocument
from app.schemas.dto.payment_reconciliation import ProviderPaymentState
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.billing.constrained_strings import ReconciliationDay
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit


class PlatformPauseRepoContract(RepoContract, Protocol):
    def get(self) -> PlatformPauseDocument | None:
        """The pause as it stands; None before the first pause."""
        raise NotImplementedError

    def save(self, pause: PlatformPauseDocument) -> None:
        raise NotImplementedError


class PlatformSpendGaugeContract(RegistryContract, Protocol):
    def spend_today(self, now: Microseconds) -> CostMicroUsd:
        """
        The platform's provider spend of the UTC day of `now`, read at most
        once a minute per process (the daily budget stop's reading).
        """
        raise NotImplementedError


class PeriodicJobHeartbeatRepoContract(RepoContract, Protocol):
    def get_many(
        self, job_names: Sequence[JobName]
    ) -> list[PeriodicJobHeartbeatDocument]:
        raise NotImplementedError

    def save(self, heartbeat: PeriodicJobHeartbeatDocument) -> None:
        raise NotImplementedError

    def list_overdue(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[PeriodicJobHeartbeatDocument]:
        """Heartbeats whose `due_by` passed by `now`, the longest overdue first."""
        raise NotImplementedError


class PaymentReconciliationRepoContract(RepoContract, Protocol):
    def get(self, day: ReconciliationDay) -> PaymentReconciliationDocument | None:
        raise NotImplementedError

    def save(self, reconciliation: PaymentReconciliationDocument) -> None:
        """Store the day's result, replacing an earlier run of the same day."""
        raise NotImplementedError


class PaymentStatusReaderAdapterContract(AdapterContract, Protocol):
    def read_status(
        self, payment_order: PaymentOrderDocument
    ) -> ProviderPaymentState | None:
        """
        What the order's provider says about its payment; None when there
        is nothing to ask about (no reference yet) or the provider does
        not know it.

        Raises:
            ExternalServiceError: the provider could not be reached or
                answered unreadably (the order counts as unreadable).
        """
        raise NotImplementedError
