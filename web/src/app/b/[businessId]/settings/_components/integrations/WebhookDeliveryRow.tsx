"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Badge, Button, InlineError, Spinner, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { DELIVERY_TONES, eventLabelKey, prettyPayload, type WebhookDeliveryView } from "@/lib/apiIntegrations";

/**
 * One delivery of the log: the event, its state and last answer, the exact
 * request body on demand (it holds customer data, so it is read only when
 * asked, and the read is audited), and "Send again" for a failed one.
 */
export function WebhookDeliveryRow({
  delivery,
  onRetried,
}: {
  delivery: WebhookDeliveryView;
  onRetried: (delivery: WebhookDeliveryView) => void;
}) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const format = useBusinessFormat();
  const { business } = useBusiness();
  const [isOpen, setIsOpen] = useState(false);
  const path = { business_id: business.id, delivery_id: delivery.id };
  const detail = useQuery(
    ["integrations", business.id, "webhookDelivery", delivery.id],
    () => api.GET("/v1/businesses/{business_id}/webhook-deliveries/{delivery_id}", { params: { path } }),
    { enabled: isOpen, staleMs: 60_000 },
  );
  const retry = useMutation(() => api.POST("/v1/businesses/{business_id}/webhook-deliveries/{delivery_id}/retry", { params: { path } }));

  const sendAgain = async () => {
    const result = await retry.run();
    if (result.ok) {
      toast.success(t("apiIntegrations.deliveries.retried"));
      onRetried(result.data);
    }
  };

  const facts = [
    tp("apiIntegrations.deliveries.attempts", delivery.attempts),
    delivery.last_status_code ? t("apiIntegrations.deliveries.httpStatus", { code: delivery.last_status_code }) : null,
    delivery.status === "pending" && delivery.next_attempt_at
      ? t("apiIntegrations.deliveries.nextAttempt", { time: format.dateTime(delivery.next_attempt_at) })
      : null,
  ].filter((fact): fact is string => fact !== null);
  const bodyId = `delivery-body-${delivery.id}`;

  return (
    <li className="space-y-2 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={DELIVERY_TONES[delivery.status]}>{t(`apiIntegrations.deliveries.statuses.${delivery.status}`)}</Badge>
        <span className="font-medium text-ink">{t(eventLabelKey(delivery.event_type))}</span>
        {delivery.is_test ? <Badge tone="neutral">{t("apiIntegrations.deliveries.test")}</Badge> : null}
        <span className="ms-auto text-sm text-ink-subtle">{format.dateTime(delivery.created_at)}</span>
      </div>
      <p className="text-sm text-ink-muted">{facts.join(" · ")}</p>
      {delivery.last_problem && delivery.status !== "delivered" ? (
        <p className="text-sm text-danger">{t(`apiIntegrations.deliveries.problems.${delivery.last_problem}`)}</p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button variant="ghost" size="sm" aria-expanded={isOpen} aria-controls={bodyId} onClick={() => setIsOpen((open) => !open)}>
          {t(isOpen ? "apiIntegrations.deliveries.hideBody" : "apiIntegrations.deliveries.showBody")}
        </Button>
        {delivery.status === "failed" && !delivery.is_test ? (
          <Button variant="secondary" size="sm" isLoading={retry.isPending} onClick={() => void sendAgain()}>
            {t("apiIntegrations.deliveries.retry")}
          </Button>
        ) : null}
      </div>
      {isOpen ? (
        <div id={bodyId}>
          {detail.data ? (
            <pre
              dir="ltr"
              aria-label={t("apiIntegrations.deliveries.body")}
              className="max-h-72 overflow-auto rounded-lg border border-line bg-surface-muted p-3 font-mono text-xs whitespace-pre-wrap break-all text-ink"
            >
              {prettyPayload(detail.data.payload)}
            </pre>
          ) : detail.error ? (
            <InlineError error={detail.error} />
          ) : (
            <Spinner size="sm" />
          )}
        </div>
      ) : null}
    </li>
  );
}
