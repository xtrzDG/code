"use client";

import { useState } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCard } from "@/components/icons";
import { Badge, Button, Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { Facts } from "@/components/workspace/Facts";
import { useI18n } from "@/i18n/client";

import {
  PROVIDER_NAMES,
  cardActionText,
  cardBrandName,
  cardExpiryState,
  cardExpiryText,
  type PaymentCardView,
  type PaymentMethodView,
} from "../_lib/paymentMethod";
import type { PaymentMethodState } from "../_lib/usePaymentMethod";
import { PaymentRetryStatus } from "./PaymentRetryStatus";

/**
 * "Card for payments": the card the automatic payments go to (network,
 * last digits, expiry), the payment service that keeps it, where the
 * retries of a declined payment stand, and "Save card" / "Update card".
 */
export function PaymentMethodCard({
  state,
  canManage,
  isTrial,
}: {
  state: PaymentMethodState;
  canManage: boolean;
  isTrial: boolean;
}) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const { method, isOpening, openCardPage } = state;
  const view = method.data;
  const canSave = Boolean(canManage && view?.can_save_card);

  return (
    <Card
      id="billing-card"
      aria-label={t("billingCard.title")}
      title={t("billingCard.title")}
      description={t("billingCard.description")}
      footer={
        view && canSave ? (
          <Button
            size="sm"
            variant={view.card && cardExpiryState(view.card, new Date()) !== "expired" ? "secondary" : "primary"}
            onClick={openCardPage}
            isLoading={isOpening}
            loadingText={t("billingCard.opening")}
          >
            {t(cardActionText(view))}
          </Button>
        ) : undefined
      }
    >
      {method.error && !view ? (
        <ErrorState error={method.error} onRetry={method.reload} className="py-4" />
      ) : !view ? (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonText lines={3} />
        </LoadingRegion>
      ) : (
        <div className="space-y-5">
          {view.card ? <SavedCard card={view.card} /> : <NoCard view={view} isTrial={isTrial} />}
          <Facts
            items={[
              { label: t("billingCard.facts.provider"), value: PROVIDER_NAMES[view.provider] },
              view.card ? { label: t("billingCard.facts.savedAt"), value: format.date(view.card.saved_at) } : null,
            ]}
          />
          {view.retry ? <PaymentRetryStatus retry={view.retry} /> : null}
          {canSave ? <p className="text-sm text-ink-muted">{t("billingCard.noCharge")}</p> : null}
          {canManage && !view.can_save_card && view.retry ? <p className="text-sm text-ink-muted">{t("billingCard.payToSave")}</p> : null}
        </div>
      )}
    </Card>
  );
}

/** The saved card drawn as a card: network, masked number, expiry and whether it still works. */
function SavedCard({ card }: { card: PaymentCardView }) {
  const { t } = useI18n();
  const [now] = useState(() => new Date());
  const brand = cardBrandName(card.brand);
  const expiry = cardExpiryText(card);
  const state = cardExpiryState(card, now);

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="flex aspect-[1.586] w-44 shrink-0 flex-col justify-between rounded-xl border border-line-strong bg-surface-muted p-3 shadow-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-xs font-semibold tracking-wide text-ink">{brand ?? " "}</span>
            <IconCard aria-hidden className="size-4 shrink-0 text-accent" />
          </div>
          <div>
            {card.last_digits ? (
              <p className="font-mono text-sm text-ink tabular-nums" dir="ltr">
                <span className="sr-only">{t("billingCard.endingIn", { digits: card.last_digits })}</span>
                <span aria-hidden="true">•••• {card.last_digits}</span>
              </p>
            ) : null}
            <p className="mt-1 font-mono text-xs text-ink-muted tabular-nums" dir="ltr">
              {expiry ?? " "}
            </p>
          </div>
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <p className="text-base font-semibold text-ink">
            {brand}
            {brand && card.last_digits ? " " : null}
            {card.last_digits ? <bdi dir="ltr">•••• {card.last_digits}</bdi> : null}
          </p>
          <div className="flex flex-wrap items-center gap-2 text-sm text-ink-muted">
            <span>{expiry ? t("billingCard.expires", { date: expiry }) : t("billingCard.noExpiry")}</span>
            {state === "expired" ? <Badge tone="danger">{t("billingCard.expiryStates.expired")}</Badge> : null}
            {state === "expiring" ? <Badge tone="warning">{t("billingCard.expiryStates.expiring")}</Badge> : null}
          </div>
        </div>
      </div>
      {state === "expired" ? <p className="text-sm text-ink-muted">{t("billingCard.expiredHint")}</p> : null}
      {state === "expiring" ? <p className="text-sm text-ink-muted">{t("billingCard.expiringHint")}</p> : null}
    </div>
  );
}

/** No card details: none saved yet, or one saved before the platform kept its details. */
function NoCard({ view, isTrial }: { view: PaymentMethodView; isTrial: boolean }) {
  const { t } = useI18n();
  if (view.has_auto_debit) {
    return <p className="text-sm text-ink-muted">{t("billingCard.cardWithoutDetails", { provider: PROVIDER_NAMES[view.provider] })}</p>;
  }
  return (
    <div className="flex items-start gap-3">
      <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-accent-soft text-accent-ink">
        <IconCard aria-hidden className="size-5" />
      </span>
      <div className="min-w-0">
        <p className="font-medium text-ink">{t("billingCard.noCard")}</p>
        <p className="mt-0.5 text-sm text-ink-muted">{t(isTrial ? "billingCard.noCardTrial" : "billingCard.noCardPaid")}</p>
      </div>
    </div>
  );
}
