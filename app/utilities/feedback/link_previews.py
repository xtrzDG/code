"""
Requests that are not a customer opening a link: messengers and social
networks fetch a link as soon as it is sent to draw its preview, and
crawlers follow it. Such a visit to a review link is redirected like any
other but not counted. The in-app browsers people open links in (Instagram,
Facebook, Telegram) are browsers and count.
"""

LINK_PREVIEW_AGENT_MARKERS: tuple[str, ...] = (
    "telegrambot",
    "whatsapp",
    "facebookexternalhit",
    "facebookcatalog",
    "meta-externalagent",
    "twitterbot",
    "slackbot",
    "discordbot",
    "linkedinbot",
    "skypeuripreview",
    "googlebot",
    "bingbot",
    "applebot",
    "yandexbot",
    "embedly",
    "vkshare",
    "bot/",
    "crawler",
    "spider",
    "preview",
)


def is_link_preview_agent(user_agent: str | None) -> bool:
    """A request from a link-preview fetcher or crawler, by its User-Agent."""

    if user_agent is None or user_agent.strip() == "":
        return True

    agent: str = user_agent.casefold()
    return any(marker in agent for marker in LINK_PREVIEW_AGENT_MARKERS)
