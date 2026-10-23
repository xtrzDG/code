"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { Alert, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { daysUntil } from "../_lib/billing";
import { isCardConfirmed, isCardPromptShown, trialPromptBodyText, type PaymentMethodView } from "../_lib/paymentMethod";

/**
 * From day 10 of a trial without a card: how many days are left and
 * "Save card", so the assistant keeps answering when the trial ends.
 */
export function TrialCardPrompt({
  view,
  nowUs,
  canManage,
  isOpening,
  onSave,
}: {
  view: PaymentMethodView | undefined;
  nowUs: number;
  canManage: boolean;
  isOpening: boolean;
  onSave: () => void;
}) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  if (!view || !isCardPromptShown(view) || !view.trial_ends_at) {
    return null;
  }
  return (
    <Alert tone="info" title={tp("billingCard.trialPrompt.title", daysUntil(view.trial_ends_at, nowUs))}>
      <p>
        {t(trialPromptBodyText(view), {
          date: format.date(view.trial_ends_at),
          amount: view.setup_fee_due ? format.money(view.setup_fee_due.amount_minor, view.setup_fee_due.currency_code) : "",
        })}
      </p>
      {canManage ? (
        <div className="mt-3">
          <Button size="sm" onClick={onSave} isLoading={isOpening} loadingText={t("billingCard.opening")}>
            {t("billingCard.save")}
          </Button>
        </div>
      ) : null}
    </Alert>
  );
}

/**
 * Back from the provider's page: the card is being confirmed, then saved.
 * The page asks again every few seconds until the new card shows.
 */
export function CardReturnNotice({
  view,
  returnedAtUs,
  onClose,
}: {
  view: PaymentMethodView | undefined;
  returnedAtUs: number;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const isSaved = isCardConfirmed(view, returnedAtUs);
  return (
    <Alert tone={isSaved ? "success" : "info"} title={t(isSaved ? "billingCard.returned.savedTitle" : "billingCard.returned.title")}>
      <p role="status">{t(isSaved ? "billingCard.returned.saved" : "billingCard.returned.pending")}</p>
      <div className="mt-3">
        <Button size="sm" variant="secondary" onClick={onClose}>
          {t("common.close")}
        </Button>
      </div>
    </Alert>
  );
}
