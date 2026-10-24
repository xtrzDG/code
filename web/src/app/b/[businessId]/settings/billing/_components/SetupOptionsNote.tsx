"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { SubscriptionView } from "../_lib/billing";
import { setupState } from "../_lib/setupOptions";

/**
 * The billing page's word on the setup (`#setup-options`, where the
 * "done for you" reminder leads): who sets the assistant up for this
 * subscription, or how to choose when subscribing.
 */
export function SetupOptionsNote({ subscription }: { subscription: SubscriptionView | null | undefined }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const state = setupState(subscription);

  const text =
    state?.kind === "done_for_you"
      ? state.requestedAt
        ? t("billing.setupOptions.note.requested", { date: format.date(state.requestedAt) })
        : t("billing.setupOptions.note.doneForYou")
      : state?.kind === "self_serve"
        ? t("billing.setupOptions.note.selfServe")
        : t("billing.setupOptions.note.choose");

  return (
    <Card id="setup-options" className="scroll-mt-6" title={t("billing.setupOptions.note.title")}>
      <p className="text-sm text-ink-muted">{text}</p>
    </Card>
  );
}
