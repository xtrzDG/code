"""
The API fuzz run: one started workshop per worker with a signed-in owner
of one restaurant. `-m api_fuzz` runs it alone (its own CI job); the
default run includes it.
"""

from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE, sign_in_and_create_restaurant

FUZZ_MARK: str = "api_fuzz"
SECONDS_BETWEEN_CODES: int = 31


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", f"{FUZZ_MARK}: the hypothesis run over every API operation"
    )


@dataclass
class FuzzTarget:
    workshop: Workshop
    token: str
    business_id: str

    def headers(self) -> dict[str, str]:
        return bearer(self.token)

    def keep_signed_in(self) -> None:
        """A fuzzed sign-out or deletion ends the session: sign in again."""

        if (
            self.workshop.client.get("/v1/me", headers=self.headers()).status_code
            == 401
        ):
            # Past the wait between two login codes of one number.
            self.workshop.clock.advance(SECONDS_BETWEEN_CODES)
            self.token, _ = self.workshop.sign_in_with_phone(GEORGIAN_OWNER_PHONE)


@pytest.fixture(scope="module")
def fuzz_target() -> Iterator[FuzzTarget]:
    workshop = start_workshop()
    with workshop.client:
        token, _, business_id = sign_in_and_create_restaurant(workshop)
        yield FuzzTarget(workshop=workshop, token=token, business_id=business_id)
