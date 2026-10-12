"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { IconList } from "@/components/icons";
import { LoadMore } from "@/components/insights/common";
import { Badge, Card, EmptyState, ErrorState, Field, Select, SkeletonText, Table, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  PLATFORM_AUDIT_PAGE_SIZE,
  platformAuditQuery,
  platformEntityKey,
  SECURITY_EVENT_TONES,
  SECURITY_EVENTS,
  shortReference,
  type AuditSecurityEvent,
  type PlatformAuditEntry,
  type PlatformAuditLogPage,
} from "../../_lib/audit";
import { useSystemFormat } from "../system/useSystemFormat";

/**
 * The platform's own audit log: entries that name no business (failed
 * sign-ins, lockouts, sign-outs, key rotations), newest first, filtered by
 * security event on the server. A sign-in code's address is a digest.
 */
export function PlatformLogCard() {
  const { t } = useI18n();
  const [event, setEvent] = useState<AuditSecurityEvent | "">("");
  const log = useCursorPage<PlatformAuditEntry, PlatformAuditLogPage>(
    queryKeys.admin.auditLog(event),
    (page) => api.GET("/v1/admin/audit-log", { params: { query: platformAuditQuery(event, page) } }),
    { pageSize: PLATFORM_AUDIT_PAGE_SIZE, staleMs: 0 },
  );
  const entries = log.items ?? [];
  const title = t("adminAudit.log.title");

  return (
    <Card aria-label={title} title={title} description={t("adminAudit.log.description")} padded={false}>
      <div role="search" aria-label={t("adminAudit.log.filters")} className="border-b border-line px-5 py-4 sm:px-6">
        <Field label={t("adminAudit.log.event")} className="max-w-xs">
          {(control) => (
            <Select {...control} value={event} onChange={(change) => setEvent(change.target.value as AuditSecurityEvent | "")}>
              <option value="">{t("adminAudit.log.allEvents")}</option>
              {SECURITY_EVENTS.map((value) => (
                <option key={value} value={value}>
                  {t(`adminAudit.events.${value}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
      {log.error && entries.length === 0 ? (
        <div className="p-5">
          <ErrorState error={log.error} onRetry={log.reload} />
        </div>
      ) : log.isLoading && entries.length === 0 ? (
        <div className="p-5">
          <SkeletonText lines={6} />
        </div>
      ) : entries.length === 0 ? (
        <EmptyState icon={<IconList className="size-6" />} title={event ? t("adminAudit.log.emptyFiltered") : t("adminAudit.log.empty")} />
      ) : (
        <div aria-busy={log.isPlaceholder || log.isFetching}>
          <PlatformLogTable entries={entries} caption={title} />
          <LoadMore hasMore={log.hasMore} isLoading={log.isLoadingMore} error={log.moreError} onMore={log.loadMore} />
        </div>
      )}
    </Card>
  );
}

function PlatformLogTable({ entries, caption }: { entries: readonly PlatformAuditEntry[]; caption: string }) {
  const { t, tDynamic } = useI18n();
  const format = useSystemFormat();
  const eventBadge = (entry: PlatformAuditEntry) =>
    entry.security_event ? (
      <Badge tone={SECURITY_EVENT_TONES[entry.security_event]}>{t(`adminAudit.events.${entry.security_event}`)}</Badge>
    ) : (
      <Badge tone="neutral">{tDynamic(`settings.audit.actions.${entry.action}`, entry.action)}</Badge>
    );
  const entityText = (entity: string) => tDynamic(platformEntityKey(entity), entity);
  const reference = (value: string | null | undefined) =>
    value ? (
      <span className="ms-2 font-mono text-xs text-ink-subtle" title={value}>
        {shortReference(value)}
      </span>
    ) : null;
  // A wrong code for an address nobody owns names no one; anything else without a person ran by itself.
  const who = (entry: PlatformAuditEntry) =>
    entry.actor_id ? (
      <span className="font-mono text-xs">{shortReference(entry.actor_id)}</span>
    ) : entry.action === "login" ? (
      t("adminAudit.log.unknownPerson")
    ) : (
      t("adminAudit.log.system")
    );

  return (
    <>
      <div className="hidden md:block">
        <Table caption={caption}>
          <THead>
            <Tr>
              <Th>{t("adminAudit.log.when")}</Th>
              <Th>{t("adminAudit.log.event")}</Th>
              <Th>{t("adminAudit.log.what")}</Th>
              <Th>{t("adminAudit.log.who")}</Th>
              <Th>{t("adminAudit.log.address")}</Th>
              <Th align="right">{t("adminAudit.log.entry")}</Th>
            </Tr>
          </THead>
          <TBody>
            {entries.map((entry) => (
              <Tr key={entry.id}>
                <Td className="whitespace-nowrap text-ink-muted">{format.when(entry.occurred_at)}</Td>
                <Td>{eventBadge(entry)}</Td>
                <Td>
                  {entityText(entry.entity)}
                  {reference(entry.entity_id)}
                </Td>
                <Td>{who(entry)}</Td>
                <Td className="font-mono text-xs text-ink-muted">{entry.ip_address ?? "—"}</Td>
                <Td align="right" className="font-mono text-xs text-ink-muted">
                  {entry.chain_position ? format.number(entry.chain_position) : "—"}
                </Td>
              </Tr>
            ))}
          </TBody>
        </Table>
      </div>
      <ul className="divide-y divide-line md:hidden">
        {entries.map((entry) => (
          <li key={entry.id} className="space-y-1 px-5 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              {eventBadge(entry)}
              <span className="text-xs text-ink-subtle">{format.when(entry.occurred_at)}</span>
            </div>
            <p className="text-sm text-ink">
              {entityText(entry.entity)}
              {reference(entry.entity_id)}
            </p>
            <p className="text-xs text-ink-muted">
              {who(entry)}
              {entry.ip_address ? ` · ${entry.ip_address}` : ""}
            </p>
          </li>
        ))}
      </ul>
    </>
  );
}
