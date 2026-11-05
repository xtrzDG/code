"""One step of the guided setup as the cabinet shows it."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.constants.setup import SetupStepCode, SetupStepStatus
from app.schemas.dto.setup.apply_changes import SetupActionView
from app.schemas.typings.setup.booleans import IsSetupStepRequired
from app.schemas.typings.setup.constrained_integers import SetupStepMinutes
from app.schemas.typings.setup.strings import SetupStepDescription, SetupStepTitle


class SetupStepView(ImmutableDTO):
    """
    One step of the guided setup. `missing` names what the profile still
    lacks for it (profile gap kinds); `minutes` is how long it usually
    takes. Optional steps (`is_required` False) may be skipped.
    """

    code: SetupStepCode
    status: SetupStepStatus
    is_required: IsSetupStepRequired
    title: SetupStepTitle
    description: SetupStepDescription
    minutes: SetupStepMinutes
    action: SetupActionView
    missing: list[ProfileGapKind] = Field(default_factory=list[ProfileGapKind])
