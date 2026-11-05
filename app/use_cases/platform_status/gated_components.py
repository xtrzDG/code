"""
The status components storage may name yet (REL-06): payments is shown
from this release, but it is written into the day records and the
announcements only once its release gate opens (`status_payments`), when
the release before reads the value too.
"""

from collections.abc import Iterable, Sequence

from app.schemas.constants.platform_status import StatusComponent
from app.schemas.dto.release_gates import ReleaseGate
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.storage.release_gates import is_gate_open
from app.utilities.storage.status_release_gates import PAYMENTS_STATUS_GATE


def stored_components(
    gates: Sequence[ReleaseGate] | None = None,
) -> tuple[StatusComponent, ...]:
    """Every component a stored record may name now, in their order."""

    return tuple(
        component
        for component in StatusComponent
        if component is not StatusComponent.PAYMENTS
        or is_gate_open(PAYMENTS_STATUS_GATE, gates)
    )


def require_announceable(
    components: Iterable[StatusComponent],
    gates: Sequence[ReleaseGate] | None = None,
) -> None:
    """
    Raises:
        ValidationFailedError: an announcement names a component storage
            may not name yet (payments, until the next release).
    """

    allowed: tuple[StatusComponent, ...] = stored_components(gates)
    if any(component not in allowed for component in components):
        raise ValidationFailedError(
            "The payments component can be named in announcements from the "
            "next release; name the components it affects among the others."
        )
