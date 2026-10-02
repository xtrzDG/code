"""HTTP routes of the niche catalog and the business profile wizard."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.language_negotiation import (
    negotiate_language,
    parse_language_parameter,
)
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_json_body,
    parse_path_identifier,
    read_raw_request_body,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.niches import NicheKey, ProfileWizardStep
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.profiles.business_profile import (
    BusinessProfileQuery,
    BusinessProfileView,
    ProfileInput,
    SaveProfileCommand,
)
from app.schemas.dto.profiles.niche_catalog import (
    NicheCatalogQuery,
    NicheCatalogView,
    NicheDetailsView,
    NicheTemplateQuery,
)
from app.schemas.dto.profiles.profile_gaps import ProfileGapsQuery, ProfileGapsView
from app.schemas.dto.profiles.profile_steps import (
    BookingRulesStepInput,
    ChannelsStepInput,
    ContactsAndHoursStepInput,
    FaqAndHandoffStepInput,
    NicheAndLanguagesStepInput,
    OfferStepInput,
    ProfileStepInput,
    ProfileStepSaveResult,
    SaveProfileStepCommand,
)
from app.schemas.dto.profiles.profile_wizard import (
    ProfileWizardQuery,
    ProfileWizardView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId

type BusinessAccessOperator = OperatorContract[BusinessAccessRequest, BusinessDocument]

STEP_INPUT_TYPES: tuple[type[BaseModel], ...] = (
    NicheAndLanguagesStepInput,
    ContactsAndHoursStepInput,
    OfferStepInput,
    BookingRulesStepInput,
    FaqAndHandoffStepInput,
    ChannelsStepInput,
)

read_profile_input = build_json_body_dependency(ProfileInput)


def build_profile_router(
    current_user: CurrentUserDependency,
    business_access_operator: BusinessAccessOperator,
    list_niche_templates_operator: OperatorContract[
        NicheCatalogQuery, NicheCatalogView
    ],
    get_niche_template_operator: OperatorContract[NicheTemplateQuery, NicheDetailsView],
    get_profile_wizard_operator: OperatorContract[
        ProfileWizardQuery, ProfileWizardView
    ],
    get_business_profile_operator: OperatorContract[
        BusinessProfileQuery, BusinessProfileView
    ],
    save_profile_operator: OperatorContract[SaveProfileCommand, BusinessProfileView],
    save_profile_step_operator: OperatorContract[
        SaveProfileStepCommand, ProfileStepSaveResult
    ],
    compute_profile_gaps_operator: OperatorContract[ProfileGapsQuery, ProfileGapsView],
) -> APIRouter:
    """
    Routes of the niche catalog (public) and the profile wizard (cabinet).

    Owners and staff read the profile, the wizard and the gaps; only owners
    change the profile, because it defines how the assistant behaves.
    Texts follow `?language=`, then Accept-Language (catalog) or the owner's
    language (cabinet), then English.
    """

    router: APIRouter = APIRouter(tags=["profile"])

    def authorize(
        user_id: UserId,
        raw_business_id: str,
        required_role: BusinessMemberRole | None = None,
    ) -> BusinessDocument:
        business_id: BusinessId = parse_path_identifier(
            raw_business_id,
            BusinessId,
            "Business",
        )
        return business_access_operator.operate(
            BusinessAccessRequest(
                user_id=user_id,
                business_id=business_id,
                required_role=required_role,
            )
        )

    @router.get("/v1/catalog/niches")
    def list_niches(
        language: Annotated[str | None, Query()] = None,
        accept_language: Annotated[str | None, Header()] = None,
    ) -> NicheCatalogView:
        return list_niche_templates_operator.operate(
            NicheCatalogQuery(
                language=catalog_language(language, accept_language),
            )
        )

    @router.get("/v1/catalog/niches/{niche_key}")
    def get_niche(
        niche_key: str,
        language: Annotated[str | None, Query()] = None,
        accept_language: Annotated[str | None, Header()] = None,
    ) -> NicheDetailsView:
        return get_niche_template_operator.operate(
            NicheTemplateQuery(
                niche_key=parse_path_identifier(niche_key, NicheKey, "Niche"),
                language=catalog_language(language, accept_language),
            )
        )

    @router.get("/v1/businesses/{business_id}/profile/wizard")
    def get_profile_wizard(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: Annotated[str | None, Query()] = None,
    ) -> ProfileWizardView:
        business: BusinessDocument = authorize(user_id, business_id)
        return get_profile_wizard_operator.operate(
            ProfileWizardQuery(
                business_id=business.id,
                language=parse_language_parameter(language),
            )
        )

    @router.get("/v1/businesses/{business_id}/profile")
    def get_profile(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> BusinessProfileView:
        business: BusinessDocument = authorize(user_id, business_id)
        return get_business_profile_operator.operate(
            BusinessProfileQuery(business_id=business.id)
        )

    @router.put(
        "/v1/businesses/{business_id}/profile",
        openapi_extra=describe_json_body(ProfileInput),
    )
    def save_profile(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        profile: Annotated[ProfileInput, Depends(read_profile_input)],
    ) -> BusinessProfileView:
        business: BusinessDocument = authorize(
            user_id,
            business_id,
            BusinessMemberRole.OWNER,
        )
        return save_profile_operator.operate(
            SaveProfileCommand(
                business_id=business.id,
                actor_id=user_id,
                profile=profile,
            )
        )

    @router.put(
        "/v1/businesses/{business_id}/profile/steps/{step}",
        openapi_extra=describe_json_body(*STEP_INPUT_TYPES),
    )
    def save_profile_step(
        business_id: str,
        step: str,
        user_id: Annotated[UserId, Depends(current_user)],
        raw_body: Annotated[bytes, Depends(read_raw_request_body)],
    ) -> ProfileStepSaveResult:
        business: BusinessDocument = authorize(
            user_id,
            business_id,
            BusinessMemberRole.OWNER,
        )
        wizard_step: ProfileWizardStep = parse_path_identifier(
            step,
            ProfileWizardStep,
            "Wizard step",
        )
        return save_profile_step_operator.operate(
            SaveProfileStepCommand(
                business_id=business.id,
                actor_id=user_id,
                step_input=parse_step_input(wizard_step, raw_body),
            )
        )

    @router.get("/v1/businesses/{business_id}/profile/gaps")
    def get_profile_gaps(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: Annotated[str | None, Query()] = None,
    ) -> ProfileGapsView:
        business: BusinessDocument = authorize(user_id, business_id)
        return compute_profile_gaps_operator.operate(
            ProfileGapsQuery(
                business_id=business.id,
                language=parse_language_parameter(language),
            )
        )

    return router


def catalog_language(
    raw_language: str | None,
    accept_language: str | None,
) -> LanguageTag | None:
    """`?language=` first, then the browser's Accept-Language."""

    return parse_language_parameter(raw_language) or negotiate_language(accept_language)


def parse_step_input(step: ProfileWizardStep, raw_body: bytes) -> ProfileStepInput:
    """The body of a wizard step as that step's input DTO."""

    match step:
        case ProfileWizardStep.NICHE_AND_LANGUAGES:
            return parse_json_body(NicheAndLanguagesStepInput, raw_body)
        case ProfileWizardStep.CONTACTS_AND_HOURS:
            return parse_json_body(ContactsAndHoursStepInput, raw_body)
        case ProfileWizardStep.OFFER:
            return parse_json_body(OfferStepInput, raw_body)
        case ProfileWizardStep.BOOKING_RULES:
            return parse_json_body(BookingRulesStepInput, raw_body)
        case ProfileWizardStep.FAQ_AND_HANDOFF:
            return parse_json_body(FaqAndHandoffStepInput, raw_body)
        case ProfileWizardStep.CHANNELS:
            return parse_json_body(ChannelsStepInput, raw_body)
