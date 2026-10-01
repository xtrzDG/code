"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Badge, Button, Card, EmptyState, ErrorState, Field, Input, LoadingBlock, Select, Table, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { shortId, zonedDayStartUs } from "@/components/workspace/helpers";
import { InlineError } from "@/components/workspace/InlineError";
import { IconList } from "@/components/workspace/icons";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { useCursorList } from "@/components/workspace/useCursorList";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import {
  AUDIT_ACTION_TONES,
  AUDIT_PAGE_SIZE,
  EMPTY_AUDIT_FILTERS,
  actorLabel,
  auditQuery,
  hasAuditFilters,
  type AuditAction,
  type AuditFilters,
  type AuditLogEntry,
  type AuditLogPage,
} from "../_lib/settings";

const ACTION_LABELS: Record<AuditAction, MessageKey> = {
  view: "settings.audit.actions.view",
  create: "settings.audit.actions.create",
  update: "settings.audit.actions.update",
  delete: "settings.audit.actions.delete",
  export: "settings.audit.actions.export",
  admin_access: "settings.audit.actions.admin_access",
  login: "settings.audit.actions.login",
  retention_purge: "settings.audit.actions.retention_purge",
  publish_untested: "settings.audit.actions.publish_untested",
};

const ACTIONS = Object.keys(ACTION_LABELS) as AuditAction[];

/** Operations on personal data, newest first, 50 at a time, filtered on the server. */
export function AuditTab() {
  const { t, tDynamic } = useI18n();
  const format = useBusinessFormat();
  const { business } = useBusiness();
  const [filters, setFilters] = useState<AuditFilters>(EMPTY_AUDIT_FILTERS);
  const query = auditQuery(filters, (day) => zonedDayStartUs(day, format.timeZone));

  const log = useCursorList<AuditLogEntry, AuditLogPage>(
    (cursor) =>
      api.GET("/v1/businesses/{business_id}/audit-log", {
        params: {
          path: { business_id: business.id },
          query: { ...query, limit: String(AUDIT_PAGE_SIZE), ...(cursor ? { cursor } : {}) },
        },
      }),
    (entry) => entry.id,
    [business.id, filters.action, filters.entity, filters.actorId, filters.from, filters.to, format.timeZone],
  );

  const update = (patch: Partial<AuditFilters>) => setFilters((current) => ({ ...current, ...patch }));
  const entityText = (entity: string) => tDynamic(`settings.audit.entities.${entity}`, entity);
  const actorName = (actorId: string | null | undefined, action?: AuditAction) =>
    actorLabel(actorId, business.members) ??
    (action === "admin_access" ? t("settings.audit.platform") : actorId ? shortId(actorId) : t("settings.audit.system"));
  const entries = log.items;
  const page = log.firstPage;
  const isFiltered = hasAuditFilters(filters);

  if (log.error?.code === "access_denied") {
    return (
      <Card title={t("settings.audit.title")}>
        <OwnerOnlyState className="py-4" />
      </Card>
    );
  }

  return (
    <Card title={t("settings.audit.title")} description={t("settings.audit.description")} padded={false}>
      <div
        role="search"
        aria-label={t("settings.auditFilters.label")}
        className="grid gap-4 border-b border-line px-5 py-4 sm:grid-cols-2 sm:px-6 lg:grid-cols-5"
      >
        <Field label={t("settings.audit.filter")}>
          {(control) => (
            <Select {...control} value={filters.action} onChange={(event) => update({ action: event.target.value as AuditAction | "" })}>
              <option value="">{t("settings.audit.allActions")}</option>
              {ACTIONS.map((value) => (
                <option key={value} value={value}>
                  {t(ACTION_LABELS[value])}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("settings.auditFilters.entity")}>
          {(control) => (
            <Select {...control} value={filters.entity} onChange={(event) => update({ entity: event.target.value })}>
              <option value="">{t("settings.auditFilters.allEntities")}</option>
              {(page?.entities ?? []).map((entity) => (
                <option key={entity} value={entity}>
                  {entityText(entity)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("settings.auditFilters.actor")}>
          {(control) => (
            <Select {...control} value={filters.actorId} onChange={(event) => update({ actorId: event.target.value })}>
              <option value="">{t("settings.auditFilters.allActors")}</option>
              {(page?.actor_ids ?? []).map((actorId) => (
                <option key={actorId} value={actorId}>
                  {actorLabel(actorId, business.members) ?? t("settings.auditFilters.otherPerson", { id: shortId(actorId) })}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("settings.auditFilters.from")}>
          {(control) => (
            <Input {...control} type="date" value={filters.from} max={filters.to || undefined} onChange={(event) => update({ from: event.target.value })} />
          )}
        </Field>
        <Field label={t("settings.auditFilters.to")}>
          {(control) => (
            <Input {...control} type="date" value={filters.to} min={filters.from || undefined} onChange={(event) => update({ to: event.target.value })} />
          )}
        </Field>
      </div>

      {isFiltered ? (
        <div className="flex justify-end border-b border-line px-5 py-2 sm:px-6">
          <Button variant="ghost" size="sm" onClick={() => setFilters(EMPTY_AUDIT_FILTERS)}>
            {t("settings.auditFilters.clear")}
          </Button>
        </div>
      ) : null}

      {log.error && entries.length === 0 ? (
        <ErrorState error={log.error} onRetry={log.reload} />
      ) : log.isLoading && entries.length === 0 ? (
        <LoadingBlock label={t("common.loading")} />
      ) : entries.length === 0 ? (
        <EmptyState
          icon={<IconList className="size-6" />}
          title={isFiltered ? t("settings.auditFilters.emptyFiltered") : t("settings.audit.empty")}
        />
      ) : (
        <div aria-busy={log.isLoading}>
          <div className="hidden md:block">
            <Table caption={t("settings.audit.title")}>
              <THead>
                <Tr>
                  <Th>{t("settings.audit.when")}</Th>
                  <Th>{t("settings.audit.action")}</Th>
                  <Th>{t("settings.audit.what")}</Th>
                  <Th>{t("settings.audit.who")}</Th>
                  <Th>{t("settings.audit.ip")}</Th>
                </Tr>
              </THead>
              <TBody>
                {entries.map((entry) => (
                  <Tr key={entry.id}>
                    <Td className="whitespace-nowrap text-ink-muted">{format.dateTime(entry.occurred_at)}</Td>
                    <Td>
                      <Badge tone={AUDIT_ACTION_TONES[entry.action]}>{t(ACTION_LABELS[entry.action])}</Badge>
                    </Td>
                    <Td>
                      {entityText(entry.entity)}
                      {entry.entity_id ? (
                        <span className="ml-2 font-mono text-xs text-ink-subtle" title={entry.entity_id}>
                          {shortId(entry.entity_id)}
                        </span>
                      ) : null}
                    </Td>
                    <Td dir="auto">{actorName(entry.actor_id, entry.action)}</Td>
                    <Td className="font-mono text-xs text-ink-muted">{entry.ip_address ?? "—"}</Td>
                  </Tr>
                ))}
              </TBody>
            </Table>
          </div>
          <ul className="divide-y divide-line md:hidden">
            {entries.map((entry) => (
              <li key={entry.id} className="space-y-1 px-5 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Badge tone={AUDIT_ACTION_TONES[entry.action]}>{t(ACTION_LABELS[entry.action])}</Badge>
                  <span className="text-xs text-ink-subtle">{format.dateTime(entry.occurred_at)}</span>
                </div>
                <p className="text-sm text-ink">
                  {entityText(entry.entity)}
                  {entry.entity_id ? <span className="ml-2 font-mono text-xs text-ink-subtle">{shortId(entry.entity_id)}</span> : null}
                </p>
                <p className="text-xs text-ink-muted" dir="auto">
                  {actorName(entry.actor_id, entry.action)}
                  {entry.ip_address ? ` · ${entry.ip_address}` : ""}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
      {entries.length > 0 ? (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3 sm:px-6">
          <p className="text-xs text-ink-subtle" aria-live="polite">
            {t("settings.auditFilters.shown", { count: entries.length })}
          </p>
          <InlineError error={log.moreError} className="w-full" />
          {log.hasMore ? (
            <Button variant="secondary" size="sm" isLoading={log.isLoadingMore} onClick={log.loadMore}>
              {t("workspace.loadMore")}
            </Button>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}
