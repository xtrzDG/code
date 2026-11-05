"""Reading Facebook Login's answers: tokens, their permissions, pages."""

from app.clients.meta.meta_graph_readers import (
    read_instagram_username,
    read_object_id,
    read_page_username,
)
from app.schemas.dto.channels.meta_provider import (
    MetaGrantedScope,
    MetaPageChoice,
    MetaTokenGrants,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.channels.strings import MetaPageName
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaPermissionName,
)
from app.schemas.typings.meta_connection.strings import (
    MetaAccessToken,
    MetaPageAccessToken,
)
from app.utilities.channels.json_values import (
    JsonObject,
    read_flag,
    read_object,
    read_objects,
    read_strings,
    read_text,
)


def read_access_token(body: JsonObject) -> MetaAccessToken:
    """The `access_token` of a token answer; Meta always sends one."""

    token: str | None = read_text(body, "access_token")
    if token is None:
        raise ExternalServiceError("Meta answered the sign-in without a token.")

    return MetaAccessToken(token)


def read_token_grants(body: JsonObject) -> MetaTokenGrants:
    """
    `debug_token`'s permissions, each with the objects its granular scope
    names. A token Meta calls invalid is refused.
    """

    data: JsonObject = read_object(body, "data") or {}
    if not read_flag(data, "is_valid"):
        raise ValidationFailedError("Meta says the sign-in's token does not work.")

    targets: dict[str, list[MetaObjectId]] = {}
    for granular in read_objects(data, "granular_scopes"):
        permission: str | None = read_text(granular, "scope")
        if permission is not None:
            targets.setdefault(permission, []).extend(
                target
                for raw_id in read_strings(granular, "target_ids")
                if (target := as_object_id(raw_id)) is not None
            )

    names: list[str] = read_strings(data, "scopes")
    names.extend(name for name in targets if name not in names)
    return MetaTokenGrants(
        scopes=[
            MetaGrantedScope(
                permission=permission, target_ids=targets.get(str(permission), [])
            )
            for name in names
            if (permission := as_permission(name)) is not None
        ]
    )


def read_page_choice(page: JsonObject) -> MetaPageChoice | None:
    """One page of `me/accounts` (None without a usable id)."""

    page_id: MetaObjectId | None = read_object_id(page, "id")
    if page_id is None:
        return None

    name: str | None = read_text(page, "name")
    instagram: JsonObject | None = read_object(page, "instagram_business_account")
    return MetaPageChoice(
        page_id=page_id,
        name=None if name is None else MetaPageName(name),
        username=read_page_username(page),
        instagram_account_id=(
            None if instagram is None else read_object_id(instagram, "id")
        ),
        instagram_username=(
            None if instagram is None else read_instagram_username(instagram)
        ),
    )


def read_page_access_token(page: JsonObject) -> MetaPageAccessToken | None:
    token: str | None = read_text(page, "access_token")
    return None if token is None else MetaPageAccessToken(token)


def read_next_cursor(body: JsonObject) -> str | None:
    """The `after` cursor of a list's next page (None: it was the last)."""

    paging: JsonObject = read_object(body, "paging") or {}
    if read_text(paging, "next") is None:
        return None

    cursors: JsonObject = read_object(paging, "cursors") or {}
    return read_text(cursors, "after")


def as_object_id(raw_id: str) -> MetaObjectId | None:
    try:
        return MetaObjectId(raw_id)
    except ValueError:
        return None


def as_permission(name: str) -> MetaPermissionName | None:
    try:
        return MetaPermissionName(name)
    except ValueError:
        return None
