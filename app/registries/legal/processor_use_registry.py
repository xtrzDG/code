from app.contracts.processor_uses import ProcessorUseRegistryContract
from app.registries.legal.processor_use_catalog import PROCESSOR_USES
from app.schemas.dto.processor_uses import ProcessorUse


class ProcessorUseRegistry(ProcessorUseRegistryContract):
    """
    The data flows to outside providers kept in code
    (`processor_use_catalog.py`), each flow once.
    """

    def __init__(self, uses: tuple[ProcessorUse, ...] = PROCESSOR_USES) -> None:
        flows: list[str] = [use.flow.value for use in uses]
        duplicates: set[str] = {flow for flow in flows if flows.count(flow) > 1}
        if duplicates:
            raise ValueError(f"Processor uses declared twice: {sorted(duplicates)}")

        self._uses: tuple[ProcessorUse, ...] = uses

    def list_uses(self) -> list[ProcessorUse]:
        return list(self._uses)
