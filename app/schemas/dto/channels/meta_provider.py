"""What Meta's Graph API tells the self-serve connection of a business."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.channels.strings import MetaPageName
from app.schemas.typings.meta_connection.booleans import HasLinkedInstagramAccount
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaPermissionName,
)
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.schemas.typings.sharing.constrained_strings import (
    InstagramUsername,
    MetaPageUsername,
)


class MetaAppCredentials(ImmutableDTO):
    """
    The platform's Meta app (META_APP_ID, META_APP_SECRET): codes are
    exchanged and tokens inspected in its name, and calls with a person's
    or business's token carry its `appsecret_proof`. Never logged.
    """

    app_id: PlatformIdentifier
    app_secret: PlatformSecret = Field(repr=False)


class MetaGrantedScope(ImmutableDTO):
    """
    One permission a token holds and, for a granular one, the objects it
    holds it for (`debug_token`'s `granular_scopes`: the WhatsApp Business
    Accounts of `whatsapp_business_management`, the pages of
    `pages_messaging`). Empty `target_ids`: the permission covers every
    object the person manages.
    """

    permission: MetaPermissionName
    target_ids: list[MetaObjectId] = Field(default_factory=list[MetaObjectId])


class MetaTokenGrants(ImmutableDTO):
    """What `debug_token` says a token may do."""

    scopes: list[MetaGrantedScope] = Field(default_factory=list[MetaGrantedScope])

    def targets_of(self, permission: MetaPermissionName) -> list[MetaObjectId]:
        """The objects a granular permission was granted for (none: not granted)."""

        return [
            target_id
            for scope in self.scopes
            if scope.permission == permission
            for target_id in scope.target_ids
        ]

    def has(self, permission: MetaPermissionName) -> bool:
        return any(scope.permission == permission for scope in self.scopes)


class MetaPageChoice(ImmutableDTO):
    """
    A Facebook page the signed-in owner manages, as the page picker offers
    it: its name and username, and the Instagram professional account
    linked to it (None: none is linked, so it cannot connect Instagram).
    """

    page_id: MetaObjectId
    name: MetaPageName | None = None
    username: MetaPageUsername | None = None
    instagram_account_id: MetaObjectId | None = None
    instagram_username: InstagramUsername | None = None

    @property
    def has_instagram(self) -> HasLinkedInstagramAccount:
        return self.instagram_account_id is not None
