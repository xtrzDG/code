"""Views of the value settings (the average check)."""

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.value_settings import (
    ValueSettingsDocument,
)
from app.schemas.dto.value.value_views import (
    ValueSettingsView,
)
from app.use_cases.insights.value.value_estimates import ValueEstimates
from app.utilities.value.value_keys import (
    value_settings_id_of,
)


def stored_settings_or_new(
    business: BusinessDocument,
    stored: ValueSettingsDocument | None,
) -> ValueSettingsDocument:
    if stored is not None:
        return stored

    return ValueSettingsDocument(
        id=value_settings_id_of(business.id), business_id=business.id
    )


def build_value_settings_view(
    business: BusinessDocument,
    settings: ValueSettingsDocument | None,
    estimates: ValueEstimates,
) -> ValueSettingsView:
    return ValueSettingsView(
        business_id=business.id,
        currency_code=business.currency_code,
        average_check_minor=None if settings is None else settings.average_check_minor,
        typical_check_minor=estimates.typical_check,
        value_basis=estimates.rates.basis,
    )
