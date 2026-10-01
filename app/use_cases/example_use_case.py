from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.example_dto import ExampleImmutableDTO, ExampleMutableDTO


class ExampleUseCase(UseCaseContract[ExampleMutableDTO, ExampleImmutableDTO]):
    def run(self, input_data: ExampleMutableDTO) -> ExampleImmutableDTO:
        return ExampleImmutableDTO(
            count=input_data.count,
            deterministic_id=input_data.deterministic_id,
            deterministic_prefixed_id=input_data.deterministic_prefixed_id,
            is_enabled=input_data.is_enabled,
            name=input_data.name,
            random_id=input_data.random_id,
            random_prefixed_id=input_data.random_prefixed_id,
            ratio=input_data.ratio,
        )
