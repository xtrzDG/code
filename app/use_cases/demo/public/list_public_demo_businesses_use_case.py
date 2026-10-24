from app.contracts.public_demos import PublicDemoDirectoryRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.public_demo import PublicDemoBusinessIds, PublicDemoListQuery


class ListPublicDemoBusinessesUseCase(
    UseCaseContract[PublicDemoListQuery, PublicDemoBusinessIds]
):
    """
    The demo businesses of the landing page (PUBLIC_DEMO_BUSINESS_IDS, or
    the development demo businesses), in their order. Reads no tenant data.
    """

    def __init__(self, public_demo_directory: PublicDemoDirectoryRegistryContract):
        self._directory: PublicDemoDirectoryRegistryContract = public_demo_directory

    def run(self, input_data: PublicDemoListQuery) -> PublicDemoBusinessIds:
        del input_data
        return PublicDemoBusinessIds(business_ids=self._directory.list_business_ids())
