"""Routers of the public site: the legal texts and the landing page's demos."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.legal_routes import build_legal_router
from app.gateways.http.public_demo_routes import build_public_demo_router


def build_public_site_routers(operators: OperatorsContainer) -> list[APIRouter]:
    """
    /v1/legal (terms, privacy policy, cookies, security, the sub-processor
    list and the overview) and /v1/public-demos (sandbox demos), all public.
    """

    legal = operators.legal
    public_demos = operators.public_demos
    return [
        build_legal_router(
            get_subprocessors_operator=legal.get_subprocessors_operator(),
            get_legal_document_operator=legal.get_legal_document_operator(),
            get_legal_overview_operator=legal.get_legal_overview_operator(),
        ),
        build_public_demo_router(
            list_public_demos_operator=public_demos.list_public_demos_operator(),
            public_demo_message_operator=public_demos.public_demo_message_operator(),
        ),
    ]
