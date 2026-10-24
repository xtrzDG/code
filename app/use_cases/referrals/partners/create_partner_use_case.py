from typed_time_provider import Microseconds

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.referral_repositories import (
    PartnerRepoContract,
    ReferralCodeRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.dto.referrals.partner_admin import (
    CreatePartnerCommand,
    CreatePartnerRequest,
    PartnerAdminView,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.use_cases.referrals.partner_summaries import PartnerReaders
from app.use_cases.referrals.partners.partner_admin_gate import (
    PARTNER_ENTITY,
    PartnerAdminGate,
)
from app.use_cases.referrals.partners.partner_admin_views import (
    build_partner_admin_view,
)
from app.use_cases.referrals.partners.partner_codes import (
    claim_partner_code,
    require_free_code,
)
from app.utilities.referrals.referral_identity import partner_id_for
from app.utilities.security.email_addresses import parse_email_address


class CreatePartnerUseCase(UseCaseContract[CreatePartnerCommand, PartnerAdminView]):
    """
    POST /v1/admin/partners (MANAGE_CLIENT_BILLING): a new partner (an
    agency or a consultant) with the phone number (any country) or e-mail
    they sign in with, their commission rate and first code. The person
    is a partner from their next sign-in; the partner's id derives from
    that destination, so a person is one partner (409 when they already
    are, 409 `code_taken` for a code in use). Audited (CREATE partner).
    """

    def __init__(
        self,
        gate: PartnerAdminGate,
        partner_repo: PartnerRepoContract,
        referral_code_repo: ReferralCodeRepoContract,
        phone_number_parser: PhoneNumberParserContract,
        readers: PartnerReaders,
    ) -> None:
        self._gate: PartnerAdminGate = gate
        self._partner_repo: PartnerRepoContract = partner_repo
        self._codes: ReferralCodeRepoContract = referral_code_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._readers: PartnerReaders = readers

    def run(self, input_data: CreatePartnerCommand) -> PartnerAdminView:
        admin: UserDocument = self._gate.admit(
            input_data.user_id, PlatformAdminPermission.MANAGE_CLIENT_BILLING
        )
        request: CreatePartnerRequest = input_data.request
        now: Microseconds = self._gate.now()
        partner: PartnerDocument = self._build_partner(request, admin, now)
        require_free_code(self._codes, request.code)
        if not self._partner_repo.add(partner):
            raise ConflictError("This person is already a partner.")

        claim_partner_code(self._codes, partner.id, request.code, now)
        self._gate.record(
            admin,
            AuditAction.CREATE,
            PARTNER_ENTITY,
            partner.id,
            input_data.client_ip_address,
        )
        return build_partner_admin_view(partner, self._readers)

    def _build_partner(
        self, request: CreatePartnerRequest, admin: UserDocument, now: Microseconds
    ) -> PartnerDocument:
        if request.phone_number is not None and request.email is None:
            phone: PhoneNumberDetails = self._phone_number_parser.parse(
                request.phone_number, request.country_hint
            )
            return PartnerDocument(
                id=partner_id_for(f"phone:{phone.e164}"),
                name=request.name,
                login_method=LoginMethod.PHONE,
                phone_number=phone.e164,
                commission_rate_basis_points=request.commission_rate_basis_points,
                added_by=admin.id,
                created_at=now,
                updated_at=now,
            )

        if request.email is not None and request.phone_number is None:
            email = parse_email_address(request.email)
            return PartnerDocument(
                id=partner_id_for(f"email:{email}"),
                name=request.name,
                login_method=LoginMethod.EMAIL,
                email=email,
                commission_rate_basis_points=request.commission_rate_basis_points,
                added_by=admin.id,
                created_at=now,
                updated_at=now,
            )

        raise ValidationFailedError("Enter either a phone number or an e-mail.")
