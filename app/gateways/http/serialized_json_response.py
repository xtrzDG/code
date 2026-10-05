"""
A route's JSON answer serialized in the route itself, for the hot routes.

FastAPI validates a DTO a sync route returns once more before serializing
it, and does so in a second hop to a request thread. A route that returns
`serialized_json_response(dto)` skips both: the DTO was validated when it
was built, and the answer is the one FastAPI would send (the same bytes,
`application/json`, the same headers in the same order). The route still
declares `response_model=` for the API description.
"""

from collections.abc import Mapping

from base_pydantic_schemas import ImmutableDTO
from fastapi import Response

JSON_MEDIA_TYPE: str = "application/json"


def serialized_json_response(
    body: ImmutableDTO,
    headers: Mapping[str, str],
) -> Response:
    """`body` as FastAPI's JSON answer (200), then `headers` as a route sets them."""

    response = Response(
        content=body.__pydantic_serializer__.to_json(body, by_alias=True),
        media_type=JSON_MEDIA_TYPE,
    )
    response.headers.update(headers)
    return response
