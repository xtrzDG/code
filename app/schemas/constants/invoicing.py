from enum import StrEnum


class TaxTreatment(StrEnum):
    """
    How value added tax applies to one invoice (TaxPolicyRegistry decides):

    - NOT_REGISTERED: the seller is not registered for VAT
      (PLATFORM_VAT_REGISTERED is off), so no VAT is charged.
    - STANDARD: a buyer in the seller's country pays the country's VAT on
      top of the price (Georgia: 18 %).
    - REVERSE_CHARGE: a business abroad with a tax number accounts for the
      VAT itself; the invoice says so and charges none.
    - OUTSIDE_SCOPE: a buyer abroad without a tax number; the service is
      supplied outside the seller's country and carries none of its VAT.
    """

    NOT_REGISTERED = "not_registered"
    STANDARD = "standard"
    REVERSE_CHARGE = "reverse_charge"
    OUTSIDE_SCOPE = "outside_scope"


class BillingDocumentKind(StrEnum):
    """
    The PDF an invoice is printed as: the INVOICE (a bill, numbered, with
    the tax lines) or, once it is paid, its payment RECEIPT.
    """

    INVOICE = "invoice"
    RECEIPT = "receipt"
