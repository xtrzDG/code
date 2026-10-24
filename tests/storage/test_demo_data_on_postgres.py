"""SEED_DEMO_DATA on Postgres: seeded once, kept as it is after a restart."""

from app.schemas.typings.platform.strings import DatabaseUrl
from tests.e2e.harness import bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.test_application_on_postgres import count_rows

DEMO_OWNER_EMAIL: str = "demo@example.com"
DEMO_BUSINESSES: list[str] = ["Mtsvane Ezo", "Studio Lindenblatt"]


def test_demo_data_is_seeded_once_into_postgres(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
    database_url: DatabaseUrl,
) -> None:
    environment: dict[str, str] = {
        **E2E_ENVIRONMENT,
        "DATABASE_URL": str(database_url),
        "SEED_DEMO_DATA": "true",
    }
    stored: list[dict[str, int]] = []
    for start in range(2):
        # Each start is a new process over the same database, a bit later.
        workshop = start_workshop(environment)
        workshop.clock.advance(start * 120)
        with workshop.client as client:
            token, _ = workshop.sign_in_with_email(DEMO_OWNER_EMAIL)
            businesses = client.get("/v1/businesses", headers=bearer(token)).json()

        assert sorted(business["name"] for business in businesses) == DEMO_BUSINESSES
        stored.append(
            {
                table: count_rows(postgres_server, database_name, table)
                for table in ("businesses", "conversations", "messages", "bookings")
            }
        )

    assert stored[0] == stored[1]
    assert stored[0]["businesses"] == 2
    assert stored[0]["conversations"] > 40
