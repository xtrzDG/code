"""Assembly sources of a seeded business and a table view of its facts."""

from app.schemas.domain.assistants import BusinessFact
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.assistants.assembly_sources import BusinessFactsSource
from app.schemas.typings.bookings.constrained_strings import LocalDate
from tests.assembly.testbed import AssemblyTestbed

TODAY: LocalDate = LocalDate("2026-10-01")


def build_source(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
    today: LocalDate = TODAY,
) -> BusinessFactsSource:
    profile: BusinessProfileDocument | None = testbed.profile_repo.get_by_business(
        business.id
    )
    assert profile is not None
    return BusinessFactsSource(
        business=business,
        profile=profile,
        niche=testbed.niche_registry.get(business.niche_key),
        country=testbed.country_registry.get(business.country_code),
        language_profiles=[
            testbed.language_registry.get(language) for language in business.languages
        ],
        knowledge_items=testbed.knowledge_repo.list_by_business(business.id),
        resources=testbed.resource_repo.list_by_business(business.id),
        schedule_exceptions=testbed.exception_repo.list_by_business(business.id),
        today=today,
    )


def as_table(facts: list[BusinessFact]) -> dict[str, tuple[str, str]]:
    return {str(fact.key): (str(fact.label), str(fact.value)) for fact in facts}
