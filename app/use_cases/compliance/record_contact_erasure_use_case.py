from app.contracts.contact_erasure_ledger import ContactErasureLedgerAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.business_closures.contact_erasure_ledger import (
    ContactErasureRecord,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import JobName

RECORD_CONTACT_ERASURE_JOB: JobName = JobName("record_contact_erasure")


class RecordContactErasureUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    Queued job "record_contact_erasure" (the batch worker, which holds the
    ledger's bucket key): an owner's erasure of a customer copied into the
    ledger outside the database (`ContactErasureLedgerAdapterContract`),
    ids and the moment only. The bucket failing raises, so the queue
    retries with backoff and finally shows it among the dead jobs; writing
    a record again changes nothing.
    """

    def __init__(self, ledger: ContactErasureLedgerAdapterContract) -> None:
        self._ledger: ContactErasureLedgerAdapterContract = ledger

    def run(self, input_data: QueuedJobInput) -> JobReport:
        record = ContactErasureRecord.model_validate_json(str(input_data.payload))
        if record.business_id != input_data.business_id:
            raise ValidationFailedError(
                "A contact erasure job names another business than its record."
            )

        self._ledger.record(record)
        return JobReport(processed_count=ProcessedItemCount(1))
