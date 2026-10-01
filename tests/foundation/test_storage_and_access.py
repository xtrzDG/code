import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.containers.app import AppContainer
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.repositories.business_repositories import BusinessRepository
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.accounts.prefixed_id import OwnerId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)


def build_business(owner_id: OwnerId) -> BusinessDocument:
    return BusinessDocument(
        owner_id=owner_id,
        name=BusinessName("Trattoria Milano"),
        niche_key=NicheKey.RESTAURANT,
        country_code=CountryCode("IT"),
        timezone=TimezoneName("Europe/Rome"),
        currency_code=CurrencyCode("EUR"),
        owner_language=LanguageTag("it"),
        customer_languages=[LanguageTag("it"), LanguageTag("en")],
        plan_key=PlanKey.VOICE_AND_CHAT,
        data_region=DataRegion.EU,
    )


def test_collection_returns_independent_copies() -> None:
    repository = BusinessRepository(
        InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
    )
    business = build_business(OwnerId())
    repository.save(business)

    loaded = repository.get(business.id)
    assert loaded is not None
    loaded.name = BusinessName("Changed without save")

    reloaded = repository.get(business.id)
    assert reloaded is not None
    assert reloaded.name == "Trattoria Milano"


def test_owner_sees_own_business_and_not_foreign_one() -> None:
    repository = BusinessRepository(
        InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
    )
    owner_id = OwnerId()
    business = build_business(owner_id)
    repository.save(business)
    use_case = AuthorizeBusinessAccessUseCase(business_repo=repository)
    operator = PipelineOperator(
        OrchestratorPipeline(UseCaseOrchestrator(use_case)),
    )

    authorized = operator.operate(
        BusinessAccessRequest(owner_id=owner_id, business_id=business.id)
    )
    assert authorized.id == business.id

    with pytest.raises(NotFoundError):
        operator.operate(
            BusinessAccessRequest(owner_id=OwnerId(), business_id=business.id)
        )


def test_app_container_wires_repositories_as_singletons() -> None:
    app_container = AppContainer()

    first_repo = app_container.repositories.business_repo()
    second_repo = app_container.repositories.business_repo()

    assert first_repo is second_repo


def test_business_is_found_by_connected_channel_account() -> None:
    from app.schemas.constants.channels import ChannelKind
    from app.schemas.domain.businesses import ChannelConnection
    from app.schemas.typings.channels.strings import ChannelAccountId

    repository = BusinessRepository(
        InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
    )
    business = build_business(OwnerId())
    business.channels = [
        ChannelConnection(
            kind=ChannelKind.WHATSAPP,
            account_id=ChannelAccountId("109876543210"),
        )
    ]
    repository.save(business)

    found = repository.find_by_channel_account(
        ChannelKind.WHATSAPP,
        ChannelAccountId("109876543210"),
    )
    missing = repository.find_by_channel_account(
        ChannelKind.TELEGRAM,
        ChannelAccountId("109876543210"),
    )

    assert found is not None and found.id == business.id
    assert missing is None
