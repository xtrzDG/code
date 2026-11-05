from app.contracts.invoicing import TaxPolicyRegistryContract
from app.registries.billing.tax_policy_catalog import STANDARD_VAT_RATES
from app.schemas.configurations.seller_settings import SellerSettings
from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.dto.invoicing import TaxBuyer, TaxDecision
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.invoicing.constrained_integers import TaxRateBasisPoints

NO_TAX: TaxRateBasisPoints = TaxRateBasisPoints(0)


class TaxPolicyRegistry(TaxPolicyRegistryContract):
    """
    VAT of the seller's invoices (SELLER_COUNTRY_CODE,
    PLATFORM_VAT_REGISTERED):

    - a seller not registered for VAT charges none (NOT_REGISTERED);
    - a registered seller adds its country's standard rate for buyers in
      that country (Georgia: 18 %, STANDARD);
    - buyers abroad pay no VAT of the seller's country: a business with a
      tax number accounts for it itself (REVERSE_CHARGE, said on the
      invoice), anyone else is supplied outside the seller's country
      (OUTSIDE_SCOPE).

    The wording printed for each treatment wants an accountant's sign-off
    (docs/LAUNCH.md).
    """

    def __init__(self, seller: SellerSettings) -> None:
        self._seller: SellerSettings = seller
        self._standard_rate: TaxRateBasisPoints | None = STANDARD_VAT_RATES.get(
            seller.country_code
        )
        if seller.is_vat_registered and self._standard_rate is None:
            raise ValidationFailedError(
                f"PLATFORM_VAT_REGISTERED: no VAT rate is known for "
                f"SELLER_COUNTRY_CODE={seller.country_code}."
            )

    def decide(self, buyer: TaxBuyer) -> TaxDecision:
        if not self._seller.is_vat_registered or self._standard_rate is None:
            return TaxDecision(
                treatment=TaxTreatment.NOT_REGISTERED, rate_basis_points=NO_TAX
            )

        if buyer.country_code == self._seller.country_code:
            return TaxDecision(
                treatment=TaxTreatment.STANDARD,
                rate_basis_points=self._standard_rate,
            )

        return TaxDecision(
            treatment=(
                TaxTreatment.REVERSE_CHARGE
                if buyer.has_tax_id
                else TaxTreatment.OUTSIDE_SCOPE
            ),
            rate_basis_points=NO_TAX,
        )
