"use client";

import { IconCheckCircle } from "@/components/icons";
import { Badge, Card, EmptyState } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { SEVERITY_TONES, groupAlerts, type AlertState } from "../../_lib/system";
import { useSystemFormat } from "./useSystemFormat";

const SEVERITY_EDGES = {
  sev1: "border-s-danger",
  sev2: "border-s-warning",
  sev3: "border-s-info",
} as const;

/**
 * The platform alerts (ops/alerts/*.yaml): those firing now, most severe
 * first, then those resolved within a day. The rule's name is translated;
 * its technical detail stays as the job wrote it.
 */
export function AlertsCard({ alerts }: { alerts: readonly AlertState[] }) {
  const { t } = useI18n();
  const { firing, resolved } = groupAlerts(alerts);
  return (
    <Card aria-label={t("adminSystem.alerts.title")} title={t("adminSystem.alerts.title")} description={t("adminSystem.alerts.description")}>
      <div className="space-y-5">
        {firing.length === 0 ? (
          <EmptyState
            icon={<IconCheckCircle className="size-6 text-success" />}
            title={t("adminSystem.alerts.allClear")}
            description={t("adminSystem.alerts.allClearDescription")}
          />
        ) : (
          <ul className="space-y-3" aria-live="polite">
            {firing.map((alert) => (
              <AlertRow key={alert.code} alert={alert} />
            ))}
          </ul>
        )}
        {resolved.length > 0 ? (
          <section aria-label={t("adminSystem.alerts.resolvedTitle")} className="space-y-3">
            <h3 className="text-sm font-medium text-ink-muted">{t("adminSystem.alerts.resolvedTitle")}</h3>
            <ul className="space-y-3">
              {resolved.map((alert) => (
                <AlertRow key={alert.code} alert={alert} />
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </Card>
  );
}

function AlertRow({ alert }: { alert: AlertState }) {
  const { t, tp } = useI18n();
  const format = useSystemFormat();
  const isFiring = alert.status === "firing";
  return (
    <li
      className={cn(
        "space-y-2 rounded-xl border border-s-4 border-line p-4",
        isFiring ? cn("bg-surface", SEVERITY_EDGES[alert.severity]) : "border-s-line bg-surface-muted/40",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={isFiring ? SEVERITY_TONES[alert.severity] : "neutral"}>{t(`adminSystem.severity.${alert.severity}`)}</Badge>
        <h3 className="min-w-0 font-medium text-ink">{t(`adminSystem.alerts.codes.${alert.code}`)}</h3>
        <span className="text-sm text-ink-muted">{format.alertFigure(alert)}</span>
      </div>
      <p className="text-sm break-words text-ink-muted" lang="en" dir="ltr">
        {alert.detail}
      </p>
      <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-subtle">
        <span>
          {isFiring
            ? t("adminSystem.alerts.firingSince", { time: format.when(alert.fired_at) })
            : t("adminSystem.alerts.resolvedAt", { time: format.when(alert.resolved_at) })}
        </span>
        <span>
          {alert.notification_count > 0 ? tp("adminSystem.alerts.sent", alert.notification_count) : t("adminSystem.alerts.notSent")}
        </span>
        <span className="min-w-0 break-all">
          {t("adminSystem.alerts.runbook")}: <code className="font-mono">{alert.runbook}</code>
        </span>
      </p>
    </li>
  );
}
