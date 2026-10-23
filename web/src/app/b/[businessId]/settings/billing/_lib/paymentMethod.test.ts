import { describe, expect, it } from "vitest";

import type { BillingNotice } from "./billing";
import {
  cardActionText,
  cardBrandName,
  cardExpiryState,
  cardExpiryText,
  cardReturnUrl,
  cardSaveNoteText,
  isCardConfirmed,
  isCardPromptShown,
  maskedCardNumber,
  retryStatusText,
  trialPromptBodyText,
  withoutTrialNotice,
  type PaymentCardView,
  type PaymentMethodView,
} from "./paymentMethod";

const MINUTE_US = 60 * 1_000_000;
const NOW_US = 1_792_479_600_000_000;

const card = (overrides: Partial<PaymentCardView> = {}): PaymentCardView => ({
  brand: "VISA",
  last_digits: "4242",
  expiry_month: 4,
  expiry_year: 2031,
  saved_at: NOW_US,
  ...overrides,
});

const method = (overrides: Partial<PaymentMethodView> = {}): PaymentMethodView => ({
  provider: "flitt",
  card: null,
  has_auto_debit: false,
  can_save_card: true,
  trial_ends_at: NOW_US + 4 * 24 * 60 * MINUTE_US,
  is_trial_card_prompt_due: false,
  retry: null,
  ...overrides,
});

describe("the saved card", () => {
  it("names card networks as they write them and keeps unknown ones", () => {
    expect(cardBrandName("VISA")).toBe("Visa");
    expect(cardBrandName("mastercard")).toBe("Mastercard");
    expect(cardBrandName("American Express")).toBe("American Express");
    expect(cardBrandName("AMEX")).toBe("American Express");
    expect(cardBrandName("ArCa")).toBe("ArCa");
    expect(cardBrandName("  ")).toBeNull();
    expect(cardBrandName(null)).toBeNull();
  });

  it("shows the last digits and the expiry as printed on cards", () => {
    expect(maskedCardNumber(card())).toBe("•••• 4242");
    expect(maskedCardNumber(card({ last_digits: null }))).toBeNull();
    expect(cardExpiryText(card())).toBe("04/31");
    expect(cardExpiryText(card({ expiry_month: 12, expiry_year: 2030 }))).toBe("12/30");
    expect(cardExpiryText(card({ expiry_month: null }))).toBeNull();
  });

  it("works through the last day of its expiry month and warns a month ahead", () => {
    const october = new Date(2026, 9, 22);
    expect(cardExpiryState(card({ expiry_month: 9, expiry_year: 2026 }), october)).toBe("expired");
    expect(cardExpiryState(card({ expiry_month: 10, expiry_year: 2026 }), october)).toBe("expiring");
    expect(cardExpiryState(card({ expiry_month: 11, expiry_year: 2026 }), october)).toBe("expiring");
    expect(cardExpiryState(card({ expiry_month: 12, expiry_year: 2026 }), october)).toBe("valid");
    expect(cardExpiryState(card({ expiry_month: 1, expiry_year: 2027 }), new Date(2026, 11, 31))).toBe("expiring");
    expect(cardExpiryState(card({ expiry_year: null }), october)).toBe("unknown");
  });

  it("asks to save a card first and to update a saved one", () => {
    expect(cardActionText(method())).toBe("billingCard.save");
    expect(cardActionText(method({ card: card() }))).toBe("billingCard.update");
  });
});

describe("retries of a declined payment", () => {
  it("says how the last try went", () => {
    expect(retryStatusText({ last_attempt: 2, last_outcome: "declined", next_retry_at: NOW_US })).toBe(
      "billingCard.retry.outcomes.declined",
    );
    expect(retryStatusText({ last_attempt: 1, last_outcome: "not_possible" })).toBe("billingCard.retry.outcomes.not_possible");
  });

  it("says the payment was declined before the first try", () => {
    expect(retryStatusText({ last_attempt: null, last_outcome: null, next_retry_at: NOW_US })).toBe("billingCard.retry.declined");
  });
});

describe("the trial's card prompt", () => {
  const notices: BillingNotice[] = [
    { kind: "trial", endsAt: NOW_US, daysLeft: 4 },
    { kind: "unpaid", count: 1 },
  ];

  it("replaces the trial notice once due, so the page asks once", () => {
    const due = method({ is_trial_card_prompt_due: true });
    expect(isCardPromptShown(due)).toBe(true);
    expect(withoutTrialNotice(notices, due)).toEqual([{ kind: "unpaid", count: 1 }]);
  });

  it("keeps the trial notice before day 10, when no card can be saved, or before the card loads", () => {
    expect(withoutTrialNotice(notices, method())).toEqual(notices);
    expect(withoutTrialNotice(notices, method({ is_trial_card_prompt_due: true, can_save_card: false }))).toEqual(notices);
    expect(withoutTrialNotice(notices, undefined)).toEqual(notices);
  });
});

describe("back from the provider's page", () => {
  it("counts a card saved shortly before the owner came back as the new one", () => {
    expect(isCardConfirmed(method({ card: card({ saved_at: NOW_US - 5 * MINUTE_US }) }), NOW_US)).toBe(true);
    expect(isCardConfirmed(method({ card: card({ saved_at: NOW_US + MINUTE_US }) }), NOW_US)).toBe(true);
    expect(isCardConfirmed(method({ card: card({ saved_at: NOW_US - 31 * MINUTE_US }) }), NOW_US)).toBe(false);
    expect(isCardConfirmed(method(), NOW_US)).toBe(false);
    expect(isCardConfirmed(undefined, NOW_US)).toBe(false);
  });

  it("returns to this billing page", () => {
    expect(cardReturnUrl("https://app.example.com/", "/b/business_1/settings/billing")).toBe(
      "https://app.example.com/b/business_1/settings/billing?card=return",
    );
  });
});

describe("what saving the card charges", () => {
  const fee = { amount_minor: 44_300, currency_code: "GEL" };

  it("names the trial's setup fee the card's page charges, or nothing charged", () => {
    expect(cardSaveNoteText(method())).toBe("billingCard.noCharge");
    expect(cardSaveNoteText(method({ setup_fee_due: fee }))).toBe("billingCard.setupFeeNow");
  });

  it("asks for the card with the setup fee named when there is one", () => {
    expect(trialPromptBodyText(method())).toBe("billingCard.trialPrompt.body");
    expect(trialPromptBodyText(method({ setup_fee_due: fee }))).toBe("billingCard.trialPrompt.bodyWithSetupFee");
  });
});
