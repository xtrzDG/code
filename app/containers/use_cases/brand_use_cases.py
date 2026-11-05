from dependency_injector.providers import Factory

from app.containers.use_cases.brand_content_use_cases import (
    BrandContentUseCasesContainer,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.brands.brand_commands import (
    AddBrandLocationCommand,
    BrandQuery,
    ChangeBrandMemberCommand,
    CreateBrandCommand,
    DeleteBrandCommand,
    InviteBrandMemberCommand,
    LeaveBrandCommand,
    RemoveBrandLocationCommand,
    RemoveBrandMemberCommand,
    RenameBrandCommand,
)
from app.schemas.dto.brands.brand_views import BrandView
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.brands import (
    add_brand_location_use_case as add_location,
)
from app.use_cases.brands import (
    change_brand_member_use_case as change_member,
)
from app.use_cases.brands import (
    create_brand_use_case as create_brand,
)
from app.use_cases.brands import (
    delete_brand_use_case as delete_brand,
)
from app.use_cases.brands import (
    get_brand_use_case as get_brand,
)
from app.use_cases.brands import (
    invite_brand_member_use_case as invite_member,
)
from app.use_cases.brands import (
    leave_brand_use_case as leave_brand,
)
from app.use_cases.brands import (
    list_my_brands_use_case as list_brands,
)
from app.use_cases.brands import (
    remove_brand_location_use_case as remove_location,
)
from app.use_cases.brands import (
    remove_brand_member_use_case as remove_member,
)
from app.use_cases.brands import (
    rename_brand_use_case as rename_brand,
)

Base = BrandContentUseCasesContainer


class BrandUseCasesContainer(BrandContentUseCasesContainer):
    """
    Brands, chains of locations run by one team (R17-BRANDS, 1192): the
    brand and its locations and its team, on top of the shared knowledge
    and "New location from…" (`BrandContentUseCasesContainer`). Location
    data is read and written through the location's own access check, in
    its own storage scope.
    """

    list_my_brands_use_case: Factory[UseCaseContract[UserId, list[BrandView]]] = (
        Factory(
            list_brands.ListMyBrandsUseCase,
            brand_repo=Base.repos.brand_repo,
            business_repo=Base.repos.business_repo,
            user_repo=Base.repos.user_repo,
            brand_view_transformer=Base.views,
        )
    )
    get_brand_use_case: Factory[UseCaseContract[BrandQuery, BrandView]] = Factory(
        get_brand.GetBrandUseCase,
        authorize_brand_access=Base.brand_access,
        business_repo=Base.repos.business_repo,
        user_repo=Base.repos.user_repo,
        brand_view_transformer=Base.views,
    )
    create_brand_use_case: Factory[UseCaseContract[CreateBrandCommand, BrandView]] = (
        Factory(
            create_brand.CreateBrandUseCase,
            brand_repo=Base.repos.brand_repo,
            business_repo=Base.repos.business_repo,
            user_repo=Base.repos.user_repo,
            audit_log_repo=Base.repos.audit_log_repo,
            brand_view_transformer=Base.views,
            session_assurance=Base.utilities.session_assurance,
            wall_clock=Base.clock,
        )
    )
    rename_brand_use_case: Factory[UseCaseContract[RenameBrandCommand, BrandView]] = (
        Factory(
            rename_brand.RenameBrandUseCase,
            authorize_brand_access=Base.brand_access,
            brand_repo=Base.repos.brand_repo,
            business_repo=Base.repos.business_repo,
            user_repo=Base.repos.user_repo,
            brand_view_transformer=Base.views,
            wall_clock=Base.clock,
        )
    )
    delete_brand_use_case: Factory[UseCaseContract[DeleteBrandCommand, None]] = Factory(
        delete_brand.DeleteBrandUseCase,
        authorize_brand_access=Base.brand_access,
        brand_repo=Base.repos.brand_repo,
        brand_knowledge_item_repo=Base.repos.brand_knowledge_item_repo,
        business_repo=Base.repos.business_repo,
    )
    add_brand_location_use_case: Factory[
        UseCaseContract[AddBrandLocationCommand, BrandView]
    ] = Factory(
        add_location.AddBrandLocationUseCase,
        authorize_brand_access=Base.brand_access,
        business_repo=Base.repos.business_repo,
        user_repo=Base.repos.user_repo,
        audit_log_repo=Base.repos.audit_log_repo,
        brand_view_transformer=Base.views,
        step_up=Base.utilities.step_up_guard,
        session_assurance=Base.utilities.session_assurance,
        wall_clock=Base.clock,
    )
    remove_brand_location_use_case: Factory[
        UseCaseContract[RemoveBrandLocationCommand, None]
    ] = Factory(
        remove_location.RemoveBrandLocationUseCase,
        authorize_brand_access=Base.brand_access,
        brand_repo=Base.repos.brand_repo,
        business_repo=Base.repos.business_repo,
        audit_log_repo=Base.repos.audit_log_repo,
        step_up=Base.utilities.step_up_guard,
        wall_clock=Base.clock,
    )
    leave_brand_use_case: Factory[UseCaseContract[LeaveBrandCommand, None]] = Factory(
        leave_brand.LeaveBrandUseCase,
        authorize_business_access=Base.business_access,
        brand_repo=Base.repos.brand_repo,
        business_repo=Base.repos.business_repo,
        audit_log_repo=Base.repos.audit_log_repo,
        step_up=Base.utilities.step_up_guard,
        wall_clock=Base.clock,
    )
    invite_brand_member_use_case: Factory[
        UseCaseContract[InviteBrandMemberCommand, BrandView]
    ] = Factory(
        invite_member.InviteBrandMemberUseCase,
        authorize_brand_access=Base.brand_access,
        brand_repo=Base.repos.brand_repo,
        business_repo=Base.repos.business_repo,
        user_repo=Base.repos.user_repo,
        phone_number_parser=Base.utilities.phone_number_parser,
        audit_log_repo=Base.repos.audit_log_repo,
        brand_view_transformer=Base.views,
        step_up=Base.utilities.step_up_guard,
        wall_clock=Base.clock,
    )
    change_brand_member_use_case: Factory[
        UseCaseContract[ChangeBrandMemberCommand, BrandView]
    ] = Factory(
        change_member.ChangeBrandMemberUseCase,
        authorize_brand_access=Base.brand_access,
        brand_repo=Base.repos.brand_repo,
        business_repo=Base.repos.business_repo,
        user_repo=Base.repos.user_repo,
        audit_log_repo=Base.repos.audit_log_repo,
        brand_view_transformer=Base.views,
        step_up=Base.utilities.step_up_guard,
        wall_clock=Base.clock,
    )
    remove_brand_member_use_case: Factory[
        UseCaseContract[RemoveBrandMemberCommand, None]
    ] = Factory(
        remove_member.RemoveBrandMemberUseCase,
        authorize_brand_access=Base.brand_access,
        brand_repo=Base.repos.brand_repo,
        business_repo=Base.repos.business_repo,
        audit_log_repo=Base.repos.audit_log_repo,
        step_up=Base.utilities.step_up_guard,
        wall_clock=Base.clock,
    )
