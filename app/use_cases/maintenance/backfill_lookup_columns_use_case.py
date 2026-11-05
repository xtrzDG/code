import logging

from app.contracts.storage import (
    LookupColumnBackfillAdapterContract,
    MigrationRetryPauseContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.lookup_backfill import (
    BackfillLookupColumnsCommand,
    LookupBackfillBatch,
    LookupBackfillReport,
    LookupColumnBackfillReport,
    TriggerLookupColumn,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.exceptions.storage_errors import MigrationLockTimeoutError
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    LookupBackfillBatchCount,
    LookupBackfillBatchSize,
    MigrationAttemptLimit,
    MigrationAttemptNumber,
)
from app.schemas.typings.storage.strings import StoredDocumentKey

DEFAULT_ATTEMPT_LIMIT: MigrationAttemptLimit = MigrationAttemptLimit(5)
logger: logging.Logger = logging.getLogger(__name__)


class BackfillLookupColumnsUseCase(
    UseCaseContract[BackfillLookupColumnsCommand, LookupBackfillReport]
):
    """
    Fill trigger-kept lookup columns for the rows written before their
    migration (`workshop backfill-lookup`, migrations/README.md).

    A migration in the online-safe pattern adds a lookup field as a plain
    column that a trigger fills on every write; older rows keep it empty
    until this runs, after the deploy and outside it. It walks the table in
    primary-key order, `batch_size` rows per short transaction, and fills
    only rows whose document has the field and whose column is empty, so it
    is idempotent and safe while the application writes. A batch that met a
    row locked for too long wrote nothing and is tried again after a pause.
    A named column that no trigger fills is a NotFoundError before anything
    is written.
    """

    def __init__(
        self,
        backfill: LookupColumnBackfillAdapterContract,
        retry_pause: MigrationRetryPauseContract,
        attempt_limit: MigrationAttemptLimit = DEFAULT_ATTEMPT_LIMIT,
    ) -> None:
        self._backfill: LookupColumnBackfillAdapterContract = backfill
        self._retry_pause: MigrationRetryPauseContract = retry_pause
        self._attempt_limit: MigrationAttemptLimit = attempt_limit

    def run(self, input_data: BackfillLookupColumnsCommand) -> LookupBackfillReport:
        columns: list[TriggerLookupColumn] = self._select_columns(input_data)
        if input_data.is_dry_run:
            return LookupBackfillReport(
                is_dry_run=True,
                columns=[
                    LookupColumnBackfillReport(
                        collection_name=column.collection_name,
                        field=column.field,
                        missing=self._backfill.count_missing(column),
                    )
                    for column in columns
                ],
            )

        return LookupBackfillReport(
            columns=[self._fill(column, input_data.batch_size) for column in columns]
        )

    def _select_columns(
        self,
        input_data: BackfillLookupColumnsCommand,
    ) -> list[TriggerLookupColumn]:
        available: list[TriggerLookupColumn] = self._backfill.list_trigger_columns()
        selected: list[TriggerLookupColumn] = [
            column
            for column in available
            if (
                input_data.collection_name is None
                or column.collection_name == input_data.collection_name
            )
            and (input_data.field is None or column.field == input_data.field)
        ]
        if input_data.collection_name is not None and not selected:
            known: str = ", ".join(
                f"{column.collection_name}.{column.field}" for column in available
            )
            raise NotFoundError(
                f"No trigger fills {input_data.collection_name}."
                f"{input_data.field or '*'}; trigger-kept lookup columns: "
                f"{known or 'none'}."
            )

        return selected

    def _fill(
        self,
        column: TriggerLookupColumn,
        batch_size: LookupBackfillBatchSize,
    ) -> LookupColumnBackfillReport:
        after: StoredDocumentKey | None = None
        scanned: int = 0
        filled: int = 0
        batches: int = 0
        while True:
            batch: LookupBackfillBatch = self._fill_batch(column, after, batch_size)
            batches += 1
            scanned += int(batch.scanned_count)
            filled += int(batch.filled_count)
            if batch.last_document_key is None or int(batch.scanned_count) < int(
                batch_size
            ):
                break

            after = batch.last_document_key

        logger.info(
            "Backfill of %s.%s: %d rows looked at, %d filled, %d batches.",
            column.collection_name,
            column.field,
            scanned,
            filled,
            batches,
        )
        return LookupColumnBackfillReport(
            collection_name=column.collection_name,
            field=column.field,
            scanned=DocumentCount(scanned),
            filled=DocumentCount(filled),
            batch_count=LookupBackfillBatchCount(batches),
        )

    def _fill_batch(
        self,
        column: TriggerLookupColumn,
        after: StoredDocumentKey | None,
        batch_size: LookupBackfillBatchSize,
    ) -> LookupBackfillBatch:
        """
        Raises:
            ExternalServiceError: every try met a row locked for too long.
        """

        attempt: int = 1
        while True:
            try:
                return self._backfill.fill_batch(column, after, batch_size)
            except MigrationLockTimeoutError as error:
                if attempt >= int(self._attempt_limit):
                    raise ExternalServiceError(
                        f"Backfill of {column.collection_name}.{column.field} gave "
                        f"up after {attempt} tries: {error}"
                    ) from error

                self._retry_pause.pause(MigrationAttemptNumber(attempt))
                attempt += 1
