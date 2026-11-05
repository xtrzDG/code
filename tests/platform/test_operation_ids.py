"""The operationId of a route: `<first tag>_<route function name>`."""

from fastapi import APIRouter, FastAPI

from app.gateways.http.operation_ids import readable_operation_id, snake_case


def build_described_application() -> FastAPI:
    application = FastAPI(generate_unique_id_function=readable_operation_id)
    tagged = APIRouter(tags=["Platform status", "admin"])
    untagged = APIRouter()

    @tagged.get("/v1/announcements")
    def list_announcements() -> list[str]:
        return []

    @tagged.post("/v1/announcements/{announcement_id}/resolve")
    def resolve_announcement_route(announcement_id: str) -> str:
        return announcement_id

    @untagged.get("/v1/ping")
    def ping() -> str:
        return "pong"

    application.include_router(tagged)
    application.include_router(untagged)
    return application


def test_ids_join_the_first_tag_and_the_function_name() -> None:
    paths = build_described_application().openapi()["paths"]

    assert paths["/v1/announcements"]["get"]["operationId"] == (
        "platform_status_list_announcements"
    )
    assert paths["/v1/announcements/{announcement_id}/resolve"]["post"][
        "operationId"
    ] == ("platform_status_resolve_announcement")
    assert paths["/v1/ping"]["get"]["operationId"] == "api_ping"


def test_snake_case_folds_spaces_hyphens_and_capitals() -> None:
    assert snake_case("Return visits") == "return_visits"
    assert snake_case("public-demos") == "public_demos"
    assert snake_case("--calendar  feeds--") == "calendar_feeds"
