"use client";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCalendar, IconLink, IconPlug } from "@/components/icons";
import { Badge, ButtonLink, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { businessPath } from "@/lib/navigation";
import { STATE_TONES, type IntegrationKind, type IntegrationView } from "@/lib/resourceCalendar";

const ICONS: Readonly<Record<IntegrationKind, typeof IconPlug>> = {
  google_calendar: IconCalendar,
  ical_import: IconCalendar,
  ical_export: IconLink,
  cal_com: IconPlug,
};

const NAMES: Readonly<Record<IntegrationKind, MessageKey>> = {
  google_calendar: "calendarSync.integrations.kinds.google_calendar",
  ical_import: "calendarSync.integrations.kinds.ical_import",
  ical_export: "calendarSync.integrations.kinds.ical_export",
  cal_com: "calendarSync.integrations.kinds.cal_com",
};

const ABOUT: Readonly<Record<IntegrationKind, MessageKey>> = {
  google_calendar: "calendarSync.integrations.about.google_calendar",
  ical_import: "calendarSync.integrations.about.ical_import",
  ical_export: "calendarSync.integrations.about.ical_export",
  cal_com: "calendarSync.integrations.about.cal_com",
};

function IntegrationRow({ item }: { item: IntegrationView }) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const Icon = ICONS[item.kind];
  const resources = item.resource_count ?? 0;
  const attention = item.attention_count ?? 0;
  const facts = [
    resources > 0 ? tp("calendarSync.integrations.resources", resources) : null,
    item.last_synced_at ? t("calendarSync.integrations.lastSynced", { time: format.dateTime(item.last_synced_at) }) : null,
  ].filter((fact): fact is string => fact !== null);
  return (
    <li className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start sm:gap-4 sm:px-6">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-surface-muted text-ink-muted" aria-hidden>
        <Icon className="size-5" />
      </span>
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium text-ink">{t(NAMES[item.kind])}</p>
          <Badge tone={STATE_TONES[item.state]}>{t(`calendarSync.integrations.states.${item.state}`)}</Badge>
        </div>
        <p className="text-sm text-ink-muted">{t(ABOUT[item.kind])}</p>
        {facts.length > 0 ? <p className="text-sm text-ink-subtle">{facts.join(" · ")}</p> : null}
        {attention > 0 ? <p className="text-sm text-warning">{tp("calendarSync.integrations.attention", attention)}</p> : null}
      </div>
      {item.kind === "google_calendar" && item.state === "off" ? (
        <ButtonLink href={businessPath(business.id, "assistant/channels")} variant="secondary" size="sm" className="self-start">
          {t("calendarSync.integrations.connectGoogle")}
        </ButtonLink>
      ) : null}
    </li>
  );
}

/** Every integration with its state, how many resources use it and when it last read. */
export function IntegrationsCard({ items }: { items: readonly IntegrationView[] }) {
  const { t } = useI18n();
  return (
    <Card padded={false} title={t("calendarSync.integrations.title")} description={t("calendarSync.integrations.description")}>
      <ul className="divide-y divide-line">
        {items.map((item) => (
          <IntegrationRow key={item.kind} item={item} />
        ))}
      </ul>
    </Card>
  );
}
