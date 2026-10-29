"""
Readable, stable operationIds for the API description (docs/api-versioning.md).

Every operation is named `<tag>_<route function name>` in snake_case, for
example `admin_list_clients` or `operations_post_booking`: the first tag of
the route (its router's), spaces and hyphens turned into underscores, then
the name of the Python function that answers it, without a trailing
`_route` (a few route functions carry it so they do not shadow the operator
they call). SDK generators turn these ids into method names, so an id is a
public name: renaming a route function or moving it under another tag is a
breaking change of the description (the `api-breaking` label and an entry
in docs/API_CHANGELOG.md). `tests/platform/test_api_contract.py` checks that
every id is unique and snake_case.
"""

import re

from fastapi.routing import APIRoute

UNTAGGED_PREFIX: str = "api"
ROUTE_FUNCTION_SUFFIX: str = "_route"
NOT_SNAKE_CASE: re.Pattern[str] = re.compile(r"[^a-z0-9]+")


def snake_case(text: str) -> str:
    """Lowercase words joined by single underscores ("Platform status" -> ...)."""

    return NOT_SNAKE_CASE.sub("_", text.lower()).strip("_")


def readable_operation_id(route: APIRoute) -> str:
    """The operationId of a route: `<first tag>_<route function name>`."""

    tag: str = str(route.tags[0]) if route.tags else UNTAGGED_PREFIX
    function_name: str = route.name.removesuffix(ROUTE_FUNCTION_SUFFIX)
    return f"{snake_case(tag)}_{snake_case(function_name)}"
