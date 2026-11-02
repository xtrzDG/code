"""Keep abc order.

Example:
    is_price_estimated: IsPriceEstimated = False
"""

HasLocalPriceBook = bool
IsAutoDebitActive = bool
IsCardSetupAvailable = bool
IsClientDiscountActive = bool
IsDerivedExchangeRate = bool
IsExchangeRateStale = bool
# A provider's answer is about an order's first payment, not its latest.
IsFirstPayment = bool
IsInitialPaymentSettled = bool
IsPaymentRetry = bool
IsPriceEstimated = bool
# A provider's answer is about the payment the order records (not a newer one).
IsRecordedPayment = bool
IsRefundDue = bool
IsSetupFeeIncluded = bool
IsSetupFeeOnly = bool
IsSetupFeeWaived = bool
IsSubscriptionCreated = bool
IsTrialAvailable = bool
IsTrialCardPromptDue = bool
IsTrialStartedAtGoLive = bool
IsTrialStartingAtGoLive = bool
# Keep abc order for all non example types, if possible.
