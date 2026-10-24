/**
 * Words of the subscription lifecycle shared by the owner's cancel dialog
 * (Settings → Billing) and the platform's Metrics page: why owners cancel
 * and the kinds of offer made instead.
 */

import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

/** "other" names a plural form in the dictionaries, so that reason has its own key. */
export const CANCELLATION_REASON_LABELS: Record<Schema<"CancellationReason">, MessageKey> = {
  seasonal_break: "billingLifecycle.reasons.seasonal_break",
  not_enough_use: "billingLifecycle.reasons.not_enough_use",
  too_expensive: "billingLifecycle.reasons.too_expensive",
  answer_quality: "billingLifecycle.reasons.answer_quality",
  missing_feature: "billingLifecycle.reasons.missing_feature",
  switched_provider: "billingLifecycle.reasons.switched_provider",
  closing_business: "billingLifecycle.reasons.closing_business",
  other: "billingLifecycle.reasons.somethingElse",
};

export const RETENTION_OFFER_LABELS: Record<Schema<"RetentionOfferKind">, MessageKey> = {
  pause: "billingLifecycle.offerKinds.pause",
  downgrade: "billingLifecycle.offerKinds.downgrade",
  credit: "billingLifecycle.offerKinds.credit",
};
