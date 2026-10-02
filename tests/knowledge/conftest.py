"""Fixtures of the knowledge route tests."""

import pytest

from tests.knowledge.routes_fixture import RoutesFixture, build_fixture


@pytest.fixture
def fixture() -> RoutesFixture:
    return build_fixture()
