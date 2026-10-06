from app.contracts.data_tasks import DataTaskBatchAdapterContract
from app.schemas.dto.data_tasks import DataTaskBatchRequest, DataTaskBatchResult
from app.schemas.typings.storage.constrained_integers import DocumentCount


class InMemoryDataTaskBatchAdapter(DataTaskBatchAdapterContract):
    """
    The data tasks without a database: in-process collections write every
    document in the current shape and compute their lookups from the
    documents themselves, so there is never an old row to rewrite or an
    empty column to fill. Every walk ends after its first batch.
    """

    def run_batch(self, request: DataTaskBatchRequest) -> DataTaskBatchResult:
        del request
        return DataTaskBatchResult(scanned=DocumentCount(0), changed=DocumentCount(0))
