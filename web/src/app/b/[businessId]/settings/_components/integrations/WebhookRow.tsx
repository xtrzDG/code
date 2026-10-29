"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { Badge, OverflowMenu, type MenuAction } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { ENDPOINT_TONES, eventLabelKey, type WebhookEndpointView } from "@/lib/apiIntegrations";

export type WebhookAction = "edit" | "pause" | "resume" | "test" | "rotate" | "deliveries" | "delete";

/** One webhook: where it sends, what, how its deliveries go, and its actions. */
export function WebhookRow({
  endpoint,
  onAction,
}: {
  endpoint: WebhookEndpointView;
  onAction: (action: WebhookAction, endpoint: WebhookEndpointView) => void;
}) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  const failures = endpoint.consecutive_failures ?? 0;
  const actions: MenuAction[] = [
    { key: "deliveries", label: t("apiIntegrations.webhooks.actions.deliveries"), onSelect: () => onAction("deliveries", endpoint) },
    { key: "test", label: t("apiIntegrations.webhooks.actions.test"), onSelect: () => onAction("test", endpoint) },
    { key: "edit", label: t("apiIntegrations.webhooks.actions.edit"), onSelect: () => onAction("edit", endpoint) },
    endpoint.status === "active"
      ? { key: "pause", label: t("apiIntegrations.webhooks.actions.pause"), onSelect: () => onAction("pause", endpoint) }
      : {
          key: "resume",
          label: t(endpoint.status === "disabled" ? "apiIntegrations.webhooks.actions.turnOn" : "apiIntegrations.webhooks.actions.resume"),
          onSelect: () => onAction("resume", endpoint),
        },
    { key: "rotate", label: t("apiIntegrations.webhooks.actions.rotate"), onSelect: () => onAction("rotate", endpoint) },
    { key: "delete", label: t("apiIntegrations.webhooks.actions.delete"), onSelect: () => onAction("delete", endpoint), tone: "danger" },
  ];

  return (
    <li className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start sm:gap-4 sm:px-6">
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <p className="min-w-0 font-medium text-ink">{endpoint.label ?? t("apiIntegrations.webhooks.title")}</p>
          <Badge tone={ENDPOINT_TONES[endpoint.status]}>{t(`apiIntegrations.webhooks.statuses.${endpoint.status}`)}</Badge>
          {endpoint.origin === "api" ? <Badge tone="neutral">{t("apiIntegrations.webhooks.origins.api")}</Badge> : null}
        </div>
        <p dir="ltr" className="font-mono text-sm break-all text-ink-muted [unicode-bidi:plaintext]">
          {endpoint.url}
        </p>
        <p className="text-sm text-ink-subtle">
          <span>{tp("apiIntegrations.webhooks.eventCount", endpoint.event_types.length)}: </span>
          {endpoint.event_types.map((eventType) => t(eventLabelKey(eventType))).join(", ")}
        </p>
        <p className="text-sm text-ink-subtle">
          {endpoint.last_success_at
            ? t("apiIntegrations.webhooks.lastSuccess", { time: format.dateTime(endpoint.last_success_at) })
            : t("apiIntegrations.webhooks.neverDelivered")}
          {" · "}
          {t("apiIntegrations.webhooks.secretHint", { hint: endpoint.secret_hint })}
        </p>
        {failures > 0 && endpoint.status !== "disabled" ? (
          <p className="text-sm text-warning">{tp("apiIntegrations.webhooks.failures", failures)}</p>
        ) : null}
        {endpoint.status === "disabled" && endpoint.disabled_at ? (
          <p className="text-sm text-danger">
            {t("apiIntegrations.webhooks.disabled", { time: format.dateTime(endpoint.disabled_at) })}
          </p>
        ) : null}
      </div>
      <OverflowMenu label={t("apiIntegrations.webhooks.actions.menu")} actions={actions} placement="bottom" className="self-start" />
    </li>
  );
}
