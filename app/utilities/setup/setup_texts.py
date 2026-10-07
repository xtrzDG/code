"""
Owner-facing texts of the guided setup: every step's title and description
and every action's label, read from the owner text catalog in each cabinet
language (`setup.*` in app/registries/localization/texts/<language>.json).
"""

from app.schemas.constants.setup import SetupActionTarget, SetupStepCode
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import owner_text

STEP_TITLES: dict[SetupStepCode, LocalizedText] = {
    code: owner_text(f"setup.steps.{code.value}.title") for code in SetupStepCode
}

STEP_DESCRIPTIONS: dict[SetupStepCode, LocalizedText] = {
    code: owner_text(f"setup.steps.{code.value}.description") for code in SetupStepCode
}

ACTION_LABELS: dict[SetupActionTarget, LocalizedText] = {
    target: owner_text(f"setup.actions.{target.value}") for target in SetupActionTarget
}

APPLY_CHANGES_AGAIN_LABEL: LocalizedText = owner_text("setup.apply_changes_again")
