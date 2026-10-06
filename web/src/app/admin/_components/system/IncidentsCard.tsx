"use client";

import { IconPlus, IconShield } from "@/components/icons";
import { LoadMore } from "@/components/insights/common";
import { Badge, Button, Card, EmptyState, ErrorState, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { listFormat } from "@/lib/intl/formatters";
import { languageName } from "@/lib/format";

import type { Incident } from "../../_lib/incidentForm";
import { SEVERITY_TONES } from "../../_lib/system";
import type { useIncidents } from "../../_lib/useIncidents";
import { useSystemFormat } from "./useSystemFormat";

type IncidentLog = ReturnType<typeof useIncidents>["incidents"];

/** The incident log, newest first, with "Record incident". */
export function IncidentsCard({ incidents, onRecord }: { incidents: IncidentLog; onRecord: () => void }) {
  const { t } = useI18n();
  const title = t("adminSystem.incidents.title");
  const items = incidents.items;
  return (
    <Card
      aria-label={title}
      title={title}
      description={t("adminSystem.incidents.description")}
      actions={
        <Button variant="secondary" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={onRecord}>
          {t("adminSystem.incidents.record")}
        </Button>
      }
    >
      {incidents.error && !items ? (
        <ErrorState error={incidents.error} onRetry={incidents.reload} />
      ) : !items ? (
        <SkeletonText lines={3} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<IconShield className="size-6" />}
          title={t("adminSystem.incidents.none")}
          description={t("adminSystem.incidents.noneDescription")}
        />
      ) : (
        <>
          <ul className="divide-y divide-line">
            {items.map((incident) => (
              <IncidentRow key={incident.id} incident={incident} />
            ))}
          </ul>
          <LoadMore hasMore={incidents.hasMore} isLoading={incidents.isLoadingMore} error={incidents.moreError} onMore={incidents.loadMore} />
        </>
      )}
    </Card>
  );
}

function IncidentRow({ incident }: { incident: Incident }) {
  const { t, tp, locale } = useI18n();
  const format = useSystemFormat();
  const languages = listFormat(locale, { type: "conjunction" }).format(
    incident.notice_languages.map((language) => languageName(language, locale)),
  );
  return (
    <li className="space-y-2 py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={SEVERITY_TONES[incident.severity]}>{t(`adminSystem.severity.${incident.severity}`)}</Badge>
        <Badge tone={incident.kind === "data_breach" ? "danger" : "neutral"}>{t(`adminSystem.incidents.kinds.${incident.kind}`)}</Badge>
        <Badge tone={incident.status === "open" ? "warning" : "success"}>{t(`adminSystem.incidents.status.${incident.status}`)}</Badge>
      </div>
      <h3 className="font-medium break-words text-ink" dir="auto" data-user-content>
        {incident.title}
      </h3>
      <p className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-muted">
        <span>{t("adminSystem.incidents.started", { time: format.when(incident.started_at) })}</span>
        <span>{t("adminSystem.incidents.detected", { time: format.when(incident.detected_at) })}</span>
        <span>{tp("adminSystem.incidents.businesses", incident.affected_business_ids.length)}</span>
        {incident.kind === "data_breach" ? (
          <span>
            {incident.notified_owner_count > 0
              ? tp("adminSystem.incidents.notified", incident.notified_owner_count)
              : t("adminSystem.incidents.notNotified")}
          </span>
        ) : null}
        {incident.notice_languages.length > 0 ? <span>{t("adminSystem.incidents.languages", { languages })}</span> : null}
      </p>
    </li>
  );
}
