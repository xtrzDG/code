"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Badge, Button, Card, EmptyState, ErrorState, Field, LoadingBlock, Select, Table, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { shortId } from "@/components/workspace/helpers";
import { InlineError } from "@/components/workspace/InlineError";
import { IconList } from "@/components/workspace/icons";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import {
  AUDIT_ACTION_TONES,
  AUDIT_PAGE_SIZE,
  actorLabel,
  hasMoreAudit,
  nextAuditLimit,
  type AuditAction,
  type AuditLogEntry,
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

/** Operations on personal data, newest first, 50 at a time. */
export function AuditTab() {
  const { t, tDynamic } = useI18n();
  const format = useBusinessFormat();
  const { business } = useBusiness();
  const [limit, setLimit] = useState(AUDIT_PAGE_SIZE);
  const [action, setAction] = useState<AuditAction | "">("");

  const log = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/audit-log", {
        params: { path: { business_id: business.id }, query: { limit: String(limit) } },
      }),
    [business.id, limit],
  );

  const entries = log.data ?? [];
  const filtered = action ? entries.filter((entry) => entry.action === action) : entries;

  const entityText = (entry: AuditLogEntry) => tDynamic(`settings.audit.entities.${entry.entity}`, entry.entity);
  const actorText = (entry: AuditLogEntry) =>
    actorLabel(entry.actor_id, business.members) ??
    (entry.action === "admin_access"
      ? t("settings.audit.platform")
      : entry.actor_id
        ? shortId(entry.actor_id)
        : t("settings.audit.system"));

  if (log.error?.code === "access_denied") {
    return (
      <Card title={t("settings.audit.title")}>
        <OwnerOnlyState className="py-4" />
      </Card>
    );
  }

  return (
    <Card
      title={t("settings.audit.title")}
      description={t("settings.audit.description")}
      padded={false}
      actions={
        <Field label={t("settings.audit.filter")} className="w-48">
          {(control) => (
            <Select {...control} value={action} onChange={(event) => setAction(event.target.value as AuditAction | "")}>
              <option value="">{t("settings.audit.allActions")}</option>
              {ACTIONS.map((value) => (
                <option key={value} value={value}>
                  {t(ACTION_LABELS[value])}
                </option>
              ))}
            </Select>
          )}
        </Field>
      }
    >
      {log.error && !log.data ? (
        <ErrorState error={log.error} onRetry={log.reload} />
      ) : !log.data ? (
        <LoadingBlock label={t("common.loading")} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<IconList className="size-6" />}
          title={t("settings.audit.empty")}
          description={entries.length > 0 ? t("settings.audit.emptyFiltered") : undefined}
        />
      ) : (
        <>
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
                {filtered.map((entry) => (
                  <Tr key={entry.id}>
                    <Td className="whitespace-nowrap text-ink-muted">{format.dateTime(entry.occurred_at)}</Td>
                    <Td>
                      <Badge tone={AUDIT_ACTION_TONES[entry.action]}>{t(ACTION_LABELS[entry.action])}</Badge>
                    </Td>
                    <Td>
                      {entityText(entry)}
                      {entry.entity_id ? (
                        <span className="ml-2 font-mono text-xs text-ink-subtle" title={entry.entity_id}>
                          {shortId(entry.entity_id)}
                        </span>
                      ) : null}
                    </Td>
                    <Td dir="auto">{actorText(entry)}</Td>
                    <Td className="font-mono text-xs text-ink-muted">{entry.ip_address ?? "—"}</Td>
                  </Tr>
                ))}
              </TBody>
            </Table>
          </div>
          <ul className="divide-y divide-line md:hidden">
            {filtered.map((entry) => (
              <li key={entry.id} className="space-y-1 px-5 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Badge tone={AUDIT_ACTION_TONES[entry.action]}>{t(ACTION_LABELS[entry.action])}</Badge>
                  <span className="text-xs text-ink-subtle">{format.dateTime(entry.occurred_at)}</span>
                </div>
                <p className="text-sm text-ink">
                  {entityText(entry)}
                  {entry.entity_id ? <span className="ml-2 font-mono text-xs text-ink-subtle">{shortId(entry.entity_id)}</span> : null}
                </p>
                <p className="text-xs text-ink-muted" dir="auto">
                  {actorText(entry)}
                  {entry.ip_address ? ` · ${entry.ip_address}` : ""}
                </p>
              </li>
            ))}
          </ul>
        </>
      )}
      {log.data ? (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3 sm:px-6">
          <p className="text-xs text-ink-subtle">{t("settings.audit.shown", { count: entries.length })}</p>
          {log.error ? <InlineError error={log.error} className="w-full" /> : null}
          {hasMoreAudit(entries.length, limit) ? (
            <Button variant="secondary" size="sm" isLoading={log.isLoading} onClick={() => setLimit((current) => nextAuditLimit(current))}>
              {t("workspace.loadMore")}
            </Button>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}
