"""
The business an evaluation dataset plays against, built the way an owner
builds it: the business with its owner, the niche's starter answers
applied by the product's own use case (hours, booking rules, the first
resource, ready FAQ answers), the offer examples priced by the dataset,
the owner's answers to the open questions, and finally an assistant
version assembled like the owner's "assemble". The Tbilisi demo
restaurant (the demo builders) can stand in for a starter business.

Every scenario sample gets a fresh business, so bookings of one scenario
never change what another one sees.
"""

from dataclasses import dataclass
from decimal import Decimal

from typed_time_provider import Microseconds

from app.containers.app import AppContainer
from app.contracts.storage import StorageScopeContract
from app.registries.demo.demo_foundation_parts import knowledge_item
from app.registries.demo.tbilisi_restaurant.restaurant_foundation import (
    build_restaurant_foundation,
)
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.profiles import (
    BusinessAddress,
    BusinessContacts,
    BusinessProfileDocument,
)
from app.schemas.domain.users import UserDocument
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
)
from app.schemas.dto.demo_data import DemoFoundationRequest
from app.schemas.dto.setup.starter_answers import (
    ApplyStarterAnswersCommand,
    ApplyStarterAnswersRequest,
)
from app.schemas.dto.setup.starter_catalog import StarterAnswers
from app.schemas.typings.businesses.strings import AddressText, BusinessName, CityName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.money.money_math import build_money_from_major_units
from scripts.eval_harness.booked_up_days import book_up
from scripts.eval_harness.catalog_seeding import build_catalog
from scripts.eval_harness.dataset_models import BusinessSpec

STARTER_SEED: str = "starter"
DEMO_RESTAURANT_SEED: str = "demo_tbilisi_restaurant"
# Owners write their answers and price list in English in the datasets.
ANSWERS_LANGUAGE: LanguageTag = LanguageTag("en")
OWNER_PHONE: E164PhoneNumber = E164PhoneNumber("+995555000001")


@dataclass(frozen=True)
class SeededBusiness:
    """A stored business and the assistant version its scenarios talk to."""

    business: BusinessDocument
    version: AssistantVersionDocument


class EvalBusinessSeeder:
    """Builds and stores evaluation businesses in one container."""

    def __init__(self, container: AppContainer) -> None:
        self._container: AppContainer = container
        self._scope: StorageScopeContract = container.utilities.storage_scope()
        self._owner: UserDocument = UserDocument(
            login_method=LoginMethod.PHONE,
            phone_number=OWNER_PHONE,
            locale=ANSWERS_LANGUAGE,
        )
        with self._scope.platform_wide():
            container.repositories.user_repo().save(self._owner)

    @property
    def owner_id(self) -> UserId:
        """The owner of every business this seeder builds (author of team notes)."""

        return self._owner.id

    def seed(self, niche: NicheKey, spec: BusinessSpec) -> SeededBusiness:
        """A fresh business of the niche with its assembled assistant version."""

        now: Microseconds = (
            self._container.time_provider.microsecond_wall_clock().now_unix()
        )
        if spec.seed == DEMO_RESTAURANT_SEED:
            business: BusinessDocument = self._seed_demo_restaurant(now)
        elif spec.seed == STARTER_SEED:
            business = self._seed_starter(niche, spec)
        else:
            raise ValueError(f"Unknown business seed {spec.seed!r}.")

        assemble = (
            self._container.use_cases.assistants.assemble_assistant_version_use_case
        )
        with self._scope.scoped_to_business(business.id):
            book_up(self._container, business, spec.booked_up, now)
            details = assemble().run(
                AssembleAssistantVersionCommand(
                    user_id=self._owner.id, business_id=business.id
                )
            )
            version: AssistantVersionDocument | None = (
                self._container.repositories.assistant_version_repo().get(
                    business.id, details.id
                )
            )

        if version is None:
            raise ValueError(f"The assembled version of {business.name} is missing.")

        return SeededBusiness(business=business, version=version)

    def _seed_demo_restaurant(self, now: Microseconds) -> BusinessDocument:
        foundation = build_restaurant_foundation(
            DemoFoundationRequest(
                owner_id=self._owner.id, staff_id=self._owner.id, now=now
            )
        )
        with self._scope.platform_wide():
            self._container.use_cases.demo.store_demo_foundation_use_case().run(
                foundation
            )

        return foundation.business

    def _seed_starter(self, niche: NicheKey, spec: BusinessSpec) -> BusinessDocument:
        languages: list[LanguageTag] = [LanguageTag(tag) for tag in spec.languages]
        business = BusinessDocument(
            name=BusinessName(spec.name),
            niche_key=niche,
            country_code=CountryCode(spec.country),
            city=CityName(spec.city),
            timezone=TimezoneName(spec.timezone),
            currency_code=CurrencyCode(spec.currency),
            languages=languages,
            default_language=languages[0],
            owner_language=ANSWERS_LANGUAGE,
            plan_key=PlanKey.VOICE_AND_CHAT,
            status=BusinessStatus.LIVE,
            data_region=DataRegion.EU,
            members=[
                BusinessMember(user_id=self._owner.id, role=BusinessMemberRole.OWNER)
            ],
        )
        repositories = self._container.repositories
        with self._scope.scoped_to_business(business.id):
            repositories.business_repo().save(business)
            self._container.use_cases.setup.apply_starter_answers_use_case().run(
                ApplyStarterAnswersCommand(
                    user_id=self._owner.id,
                    business_id=business.id,
                    request=ApplyStarterAnswersRequest(language=ANSWERS_LANGUAGE),
                )
            )
            self._complete_profile(business, spec)
            self._add_offers_and_answers(business, spec)

        return business

    def _complete_profile(self, business: BusinessDocument, spec: BusinessSpec) -> None:
        """The address and public phone the starter answers leave to the owner."""

        profile_repo = self._container.repositories.business_profile_repo()
        profile: BusinessProfileDocument | None = profile_repo.get_by_business(
            business.id
        )
        if profile is None:
            raise ValueError(f"Applying the starter answers left {business.name} bare.")

        if spec.address:
            profile.address = BusinessAddress(text=AddressText(spec.address))

        profile.contacts = BusinessContacts(
            public_phone_number=E164PhoneNumber(spec.phone),
            handoff_phone_number=E164PhoneNumber(spec.phone),
        )
        profile_repo.save(profile)

    def _add_offers_and_answers(
        self, business: BusinessDocument, spec: BusinessSpec
    ) -> None:
        """Priced offer examples and the owner's answers to open questions."""

        starters: StarterAnswers = (
            self._container.registries.starter_answer_registry().get(
                business.niche_key, business.country_code
            )
        )
        now: Microseconds = (
            self._container.time_provider.microsecond_wall_clock().now_unix()
        )
        knowledge_repo = self._container.repositories.knowledge_item_repo()
        for offer in starters.offers:
            price: str | None = spec.prices.get(str(offer.key))
            if price is None:
                continue

            money = build_money_from_major_units(Decimal(price), business.currency_code)
            knowledge_repo.save(
                knowledge_item(
                    business,
                    offer.kind,
                    str(offer.titles.values[ANSWERS_LANGUAGE]),
                    since=now,
                    price_minor=int(money.amount_minor),
                    duration_minutes=(
                        None
                        if offer.duration_minutes is None
                        else int(offer.duration_minutes)
                    ),
                )
            )

        if spec.catalog is not None and starters.offers:
            for item in build_catalog(
                business, spec.catalog, starters.offers[0].kind, now
            ):
                knowledge_repo.save(item)

        for faq in starters.faq:
            answer: str | None = spec.answers.get(str(faq.key))
            if faq.answers is not None or answer is None:
                continue

            knowledge_repo.save(
                knowledge_item(
                    business,
                    KnowledgeItemKind.FAQ,
                    str(faq.questions.values[ANSWERS_LANGUAGE]),
                    since=now,
                    body=answer,
                )
            )
