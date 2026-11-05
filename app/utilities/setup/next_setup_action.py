"""The one action the setup card and the progress ring point the owner to."""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.setup import SetupActionTarget
from app.schemas.dto.setup.apply_changes import ApplyChangesView, SetupActionView
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.setup.setup_steps import StepState
from app.utilities.setup.setup_texts import APPLY_CHANGES_AGAIN_LABEL
from app.utilities.setup.setup_views import action_view


def next_setup_action(
    next_step: StepState | None,
    apply: ApplyChangesView,
    is_live: bool,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> SetupActionView:
    """
    Once live, changes customers do not get yet come before the optional
    steps still open; then the next step; then the Overview.
    """

    if is_live and apply.has_unapplied_changes and not apply.is_in_progress:
        return action_view(
            SetupActionTarget.APPLY_CHANGES,
            language,
            resolver,
            label=APPLY_CHANGES_AGAIN_LABEL,
        )

    if next_step is not None:
        return action_view(next_step.target, language, resolver, next_step.profile_step)

    return action_view(SetupActionTarget.OVERVIEW, language, resolver)
