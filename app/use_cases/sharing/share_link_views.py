"""The share links view of a business (the sharing use cases build it)."""

from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    ChannelRepoContract,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.sharing import ShareLinksView
from app.schemas.typings.sharing.constrained_strings import (
    BusinessPublicSlug,
    HostedChatUrl,
    ShareSourceTag,
)
from app.utilities.channels.channel_links import build_hosted_chat_url
from app.utilities.sharing.share_links import build_share_links


def build_share_links_view(
    channel_repo: ChannelRepoContract,
    business_profile_repo: BusinessProfileRepoContract,
    app_settings: AppSettings,
    business: BusinessDocument,
    slug: BusinessPublicSlug,
    source: ShareSourceTag | None,
) -> ShareLinksView:
    """The hosted page's address and every channel's link, tagged."""

    profile: BusinessProfileDocument | None = business_profile_repo.get_by_business(
        business.id
    )
    hosted_chat_url: HostedChatUrl | None = (
        None
        if app_settings.cabinet_base_url is None
        else build_hosted_chat_url(app_settings.cabinet_base_url, str(slug), source)
    )
    return ShareLinksView(
        business_id=business.id,
        slug=slug,
        hosted_chat_url=hosted_chat_url,
        source=source,
        links=build_share_links(
            channel_repo.list_by_business(business.id),
            profile,
            hosted_chat_url,
            source,
        ),
    )
