"""Routers of the referral and partner program (migration 1150)."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.admin_partner_routes import build_admin_partner_router
from app.gateways.http.referral_routes import build_referral_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_referral_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """An owner's invitation, a partner's portal, the admin's partners."""

    referrals = operators.referrals
    return [
        build_referral_router(
            current_user=current_user,
            get_referral_program=referrals.get_referral_program_operator(),
            set_powered_by=referrals.set_powered_by_operator(),
            get_partner_portal=referrals.get_partner_portal_operator(),
            list_partner_referrals=referrals.list_partner_referrals_operator(),
            list_partner_commissions=referrals.list_partner_commissions_operator(),
        ),
        build_admin_partner_router(
            current_user=current_user,
            list_partners=referrals.list_partners_operator(),
            create_partner=referrals.create_partner_operator(),
            update_partner=referrals.update_partner_operator(),
            add_partner_code=referrals.add_partner_code_operator(),
            get_payout_report=referrals.get_payout_report_operator(),
            mark_payout_paid=referrals.mark_payout_paid_operator(),
        ),
    ]
