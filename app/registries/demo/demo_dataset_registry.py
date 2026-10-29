from app.contracts.demo_data import DemoDatasetRegistryContract
from app.contracts.registries import PlanRegistryContract
from app.registries.demo.berlin_salon.salon_activity import build_salon_activity
from app.registries.demo.berlin_salon.salon_foundation import build_salon_foundation
from app.registries.demo.tbilisi_restaurant.restaurant_activity import (
    build_restaurant_activity,
)
from app.registries.demo.tbilisi_restaurant.restaurant_foundation import (
    build_restaurant_foundation,
)
from app.schemas.constants.demo import DemoBusinessKey
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import UserDocument
from app.schemas.dto.demo_data import (
    DemoAccounts,
    DemoActivityRequest,
    DemoBusinessActivity,
    DemoBusinessFoundation,
    DemoFoundationRequest,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.strings import UserDisplayName

# The demo owner signs in with this phone or e-mail; in development the
# login code is printed in the API log.
DEMO_OWNER_PHONE_NUMBER: E164PhoneNumber = E164PhoneNumber("+995555000001")
DEMO_OWNER_EMAIL: EmailAddress = EmailAddress("demo@example.com")
DEMO_STAFF_PHONE_NUMBER: E164PhoneNumber = E164PhoneNumber("+995555000002")
DEMO_STAFF_EMAIL: EmailAddress = EmailAddress("staff.demo@example.com")


class DemoDatasetRegistry(DemoDatasetRegistryContract):
    """
    The development demo catalog: a Georgian restaurant in Tbilisi (five
    customer languages, every channel, a running trial) and a beauty salon
    in Berlin (German and English, paid in euros), owned by one demo owner,
    with the restaurant's hall manager as staff.
    """

    def __init__(self, plan_registry: PlanRegistryContract) -> None:
        self._plan_registry: PlanRegistryContract = plan_registry

    def describe_accounts(self) -> DemoAccounts:
        return DemoAccounts(
            owner=UserDocument(
                login_method=LoginMethod.PHONE,
                phone_number=DEMO_OWNER_PHONE_NUMBER,
                email=DEMO_OWNER_EMAIL,
                country_code=CountryCode("GE"),
                locale=LanguageTag("ru"),
                display_name=UserDisplayName("Давид Гелашвили"),
                is_verified=True,
            ),
            staff=UserDocument(
                login_method=LoginMethod.PHONE,
                phone_number=DEMO_STAFF_PHONE_NUMBER,
                email=DEMO_STAFF_EMAIL,
                country_code=CountryCode("GE"),
                locale=LanguageTag("ru"),
                display_name=UserDisplayName("Тамар Абашидзе"),
                is_verified=True,
            ),
        )

    def build_foundations(
        self,
        request: DemoFoundationRequest,
    ) -> list[DemoBusinessFoundation]:
        return [
            build_restaurant_foundation(request),
            build_salon_foundation(request),
        ]

    def build_activity(self, request: DemoActivityRequest) -> DemoBusinessActivity:
        match request.foundation.key:
            case DemoBusinessKey.TBILISI_RESTAURANT:
                return build_restaurant_activity(request, self._plan_registry)
            case DemoBusinessKey.BERLIN_SALON:
                return build_salon_activity(request, self._plan_registry)
