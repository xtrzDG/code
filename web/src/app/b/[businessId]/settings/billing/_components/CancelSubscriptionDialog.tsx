"use client";

import { useId, useState } from "react";

import type { ApiError } from "@/api/errors";
import { useBusinessFormat } from "@/components/business/BusinessContext";
import { Button, Field, Fieldset, InlineError, Modal, Radio, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { CANCELLATION_REASON_LABELS } from "@/lib/subscriptionLifecycle";

import type { BillingOverview } from "../_lib/billing";
import {
  CANCELLATION_DETAILS_MAX,
  CANCELLATION_REASONS,
  allowedPauseMonths,
  cancellationDetails,
  offerFor,
  type CancellationReason,
  type RetentionOfferKind,
} from "../_lib/lifecycle";
import type { SubscriptionLifecycleActions } from "../_lib/useSubscriptionLifecycle";
import { RetentionOfferPanel } from "./RetentionOfferPanel";

const TAKEN: Record<RetentionOfferKind, MessageKey> = {
  pause: "billingLifecycle.offers.taken.pause",
  downgrade: "billingLifecycle.offers.taken.downgrade",
  credit: "billingLifecycle.offers.taken.credit",
};

/** An offer the API refuses now (taken meanwhile, or the subscription changed) reads as "nothing to offer". */
const ERROR_OVERRIDES = { conflict: "billingLifecycle.errors.offerGone" } as const;

/**
 * Cancelling asks why first (a reason, the owner's own words), then shows
 * what the reason brings instead (a pause, a cheaper plan, a credit) with
 * "No, cancel anyway". A reason with nothing to offer cancels right away.
 */
export function CancelSubscriptionDialog({
  open,
  onClose,
  overview,
  actions,
}: {
  open: boolean;
  onClose: () => void;
  overview: BillingOverview | undefined;
  actions: SubscriptionLifecycleActions;
}) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  const formId = useId();
  const [step, setStep] = useState<"reason" | "offer">("reason");
  const [reason, setReason] = useState<CancellationReason | null>(null);
  const [details, setDetails] = useState("");
  const [months, setMonths] = useState(1);
  const [error, setError] = useState<ApiError | null>(null);
  // Each opening starts from the question.
  const [wasOpen, setWasOpen] = useState(open);
  if (wasOpen !== open) {
    setWasOpen(open);
    if (open) {
      setStep("reason");
      setReason(null);
      setDetails("");
      setMonths(1);
      setError(null);
    }
  }

  const lifecycle = actions.lifecycle.data;
  const offer = offerFor(lifecycle, reason);
  const isPending = actions.isPending;
  const periodEnd = overview?.subscription?.period_end;

  const cancel = async () => {
    if (reason === null) {
      return;
    }
    setError(null);
    const result = await actions.cancel.run({
      reason,
      details: cancellationDetails(details),
      declined_offer: step === "offer" && offer ? offer.kind : null,
    });
    if (result.ok) {
      onClose();
      actions.applied(result.data, t("billing.dialogs.cancelled"));
    } else {
      setError(result.error);
    }
  };

  const accept = async () => {
    if (reason === null || offer === null) {
      return;
    }
    setError(null);
    const pauseMonths = allowedPauseMonths(months, offer.pause_months ?? 1);
    const result = await actions.acceptOffer.run({
      reason,
      kind: offer.kind,
      ...(offer.kind === "pause" ? { pause_months: pauseMonths } : {}),
    });
    if (result.ok) {
      onClose();
      actions.applied(result.data, t(TAKEN[offer.kind]));
    } else {
      setError(result.error);
    }
  };

  const acceptLabel = (() => {
    switch (offer?.kind) {
      case "pause":
        return tp("billingLifecycle.offers.pause.confirm", allowedPauseMonths(months, offer.pause_months ?? 1));
      case "downgrade":
        return t("billingLifecycle.offers.downgrade.confirm", { plan: offer.plan_name ?? "" });
      case "credit":
        return t("billingLifecycle.offers.credit.confirm");
      default:
        return "";
    }
  })();

  const footer =
    step === "offer" && offer ? (
      <>
        <Button variant="ghost" onClick={() => setStep("reason")} disabled={isPending}>
          {t("billingLifecycle.cancel.back")}
        </Button>
        <Button variant="danger-ghost" onClick={() => void cancel()} disabled={isPending} isLoading={actions.cancel.isPending}>
          {t("billingLifecycle.cancel.cancelAnyway")}
        </Button>
        <Button onClick={() => void accept()} disabled={isPending} isLoading={actions.acceptOffer.isPending} autoFocus>
          {acceptLabel}
        </Button>
      </>
    ) : (
      <>
        <Button variant="secondary" onClick={onClose} disabled={isPending} autoFocus>
          {t("billing.dialogs.cancelKeep")}
        </Button>
        {offer ? (
          <Button type="submit" form={formId} disabled={reason === null}>
            {t("billingLifecycle.cancel.continue")}
          </Button>
        ) : (
          <Button
            type="submit"
            form={formId}
            variant="danger"
            disabled={reason === null || isPending}
            isLoading={actions.cancel.isPending}
          >
            {t("billing.dialogs.cancelConfirm")}
          </Button>
        )}
      </>
    );

  return (
    <Modal
      open={open}
      onClose={isPending ? () => undefined : onClose}
      title={step === "offer" && offer ? t("billingLifecycle.cancel.offerTitle") : t("billing.dialogs.cancelTitle")}
      size="md"
      footer={footer}
    >
      {step === "offer" && offer ? (
        <div className="space-y-4 text-sm">
          <RetentionOfferPanel
            offer={offer}
            pause={lifecycle?.pause}
            months={allowedPauseMonths(months, offer.pause_months ?? 1)}
            onMonthsChange={setMonths}
            disabled={isPending}
          />
          <InlineError error={error} overrides={ERROR_OVERRIDES} />
        </div>
      ) : (
        <form
          id={formId}
          noValidate
          className="space-y-5 text-sm"
          onSubmit={(event) => {
            event.preventDefault();
            if (reason === null || isPending) {
              return;
            }
            if (offer) {
              setError(null);
              setStep("offer");
            } else {
              void cancel();
            }
          }}
        >
          <Fieldset legend={t("billingLifecycle.cancel.reasonLegend")} hint={t("billingLifecycle.cancel.reasonHint")}>
            <div className="grid gap-2.5 sm:grid-cols-2">
              {CANCELLATION_REASONS.map((choice) => (
                <Radio
                  key={choice}
                  name={`${formId}-reason`}
                  value={choice}
                  checked={reason === choice}
                  onChange={() => setReason(choice)}
                  disabled={isPending}
                  label={t(CANCELLATION_REASON_LABELS[choice])}
                />
              ))}
            </div>
          </Fieldset>
          <Field label={t("billingLifecycle.cancel.detailsLabel")} optionalLabel={t("common.optional")}>
            {(control) => (
              <Textarea
                {...control}
                rows={3}
                value={details}
                maxLength={CANCELLATION_DETAILS_MAX}
                placeholder={t("billingLifecycle.cancel.detailsPlaceholder")}
                disabled={isPending}
                onChange={(event) => setDetails(event.target.value)}
              />
            )}
          </Field>
          {periodEnd ? (
            <p className="text-ink-muted">{t("billing.dialogs.cancelDescription", { date: format.date(periodEnd) })}</p>
          ) : null}
          <InlineError error={error} overrides={ERROR_OVERRIDES} />
        </form>
      )}
    </Modal>
  );
}
