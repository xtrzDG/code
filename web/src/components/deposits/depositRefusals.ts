import type { ReasonMessages } from "@/api/errors";

/** Why the API refused a deposit change (`reasons[].code`, DepositRefusalCode), in words. */
export const DEPOSIT_REFUSAL_MESSAGES: ReasonMessages = {
  link_not_https: () => ({ key: "deposits.pages.refusals.linkNotHttps" }),
  link_invalid: () => ({ key: "deposits.pages.refusals.linkInvalid" }),
  template_invalid: () => ({ key: "deposits.pages.refusals.templateInvalid" }),
  no_payment_link: () => ({ key: "deposits.pages.refusals.noPaymentLink" }),
  deposits_off: () => ({ key: "deposits.pages.refusals.depositsOff" }),
  currency_mismatch: () => ({ key: "deposits.pages.refusals.currencyMismatch" }),
  status_changed: () => ({ key: "deposits.pages.refusals.statusChanged" }),
};
