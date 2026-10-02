"""The guided setup as the owner sees it: steps, actions, phone links, milestones."""

from collections.abc import Sequence

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.constants.setup import SetupActionTarget, SetupStepStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.setup import ActivationEventDocument
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.setup.apply_changes import SetupActionView
from app.schemas.dto.setup.setup_progress import (
    ActivationMilestoneView,
    PhoneTestLinkView,
    SetupStepView,
)
from app.schemas.typings.channels.constrained_strings import (
    PublicBaseUrl,
    TelegramBotUsername,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.setup.constrained_integers import SetupStepMinutes
from app.schemas.typings.setup.constrained_strings import PhoneTestUrl
from app.schemas.typings.setup.strings import (
    SetupActionLabel,
    SetupStepDescription,
    SetupStepTitle,
)
from app.utilities.setup.setup_steps import STEP_MINUTES, StepState
from app.utilities.setup.setup_texts import (
    ACTION_LABELS,
    STEP_DESCRIPTIONS,
    STEP_TITLES,
)

WIDGET_DEMO_PATH: str = "/widget/demo"
TELEGRAM_LINK_PREFIX: str = "https://t.me/"
SECURE_SCHEME: str = "https://"


def action_view(
    target: SetupActionTarget,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
    profile_step: ProfileWizardStep | None = None,
    label: LocalizedText | None = None,
) -> SetupActionView:
    """Where to act, with the button label in the owner's language."""

    return SetupActionView(
        target=target,
        profile_step=profile_step if target is SetupActionTarget.PROFILE else None,
        label=SetupActionLabel(
            resolver.resolve(label or ACTION_LABELS[target], language)
        ),
    )


def step_views(
    steps: Sequence[StepState],
    statuses: Sequence[SetupStepStatus],
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> list[SetupStepView]:
    return [
        SetupStepView(
            code=step.code,
            status=status,
            is_required=step.is_required,
            title=SetupStepTitle(resolver.resolve(STEP_TITLES[step.code], language)),
            description=SetupStepDescription(
                resolver.resolve(STEP_DESCRIPTIONS[step.code], language)
            ),
            minutes=SetupStepMinutes(STEP_MINUTES[step.code]),
            action=action_view(step.target, language, resolver, step.profile_step),
            missing=list(step.missing),
        )
        for step, status in zip(steps, statuses, strict=True)
    ]


def phone_test_links(
    business: BusinessDocument,
    channels: Sequence[ChannelDocument],
    app_base_url: PublicBaseUrl | None,
    is_live: bool,
) -> list[PhoneTestLinkView]:
    """
    Links the owner opens on their phone (or scans as a QR code) to write to
    their own assistant: the hosted website chat page (on a public HTTPS
    server) and the Telegram bot, for channels that are connected. They
    answer once the assistant is live.
    """

    links: list[PhoneTestLinkView] = []
    connected: dict[ChannelKind, ChannelDocument] = {
        channel.kind: channel
        for channel in channels
        if channel.status is ChannelStatus.CONNECTED
    }
    base: str | None = None if app_base_url is None else str(app_base_url).rstrip("/")
    if ChannelKind.WEB_CHAT in connected and base and base.startswith(SECURE_SCHEME):
        links.append(
            PhoneTestLinkView(
                channel=ChannelKind.WEB_CHAT,
                url=PhoneTestUrl(
                    f"{base}{WIDGET_DEMO_PATH}?business_id={business.id}"
                    f"&language={business.default_language}"
                ),
                is_answering=is_live,
            )
        )

    telegram: ChannelDocument | None = connected.get(ChannelKind.TELEGRAM)
    bot: TelegramBotUsername | None = (
        None if telegram is None else read_bot_username(telegram)
    )
    if bot is not None:
        links.append(
            PhoneTestLinkView(
                channel=ChannelKind.TELEGRAM,
                url=PhoneTestUrl(f"{TELEGRAM_LINK_PREFIX}{bot}"),
                is_answering=is_live,
            )
        )

    return links


def read_bot_username(channel: ChannelDocument) -> TelegramBotUsername | None:
    """The bot username a Telegram channel is connected with, if it is one."""

    if channel.external_id is None:
        return None

    try:
        return TelegramBotUsername(str(channel.external_id))
    except ValueError:
        return None


def milestone_views(
    events: Sequence[ActivationEventDocument],
) -> list[ActivationMilestoneView]:
    return [
        ActivationMilestoneView(
            kind=event.kind,
            occurred_at=event.occurred_at,
            celebrated_at=event.celebrated_at,
        )
        for event in events
    ]
