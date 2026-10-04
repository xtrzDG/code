"use client";

import { Alert, Badge, Card, TBody, THead, Td, Th, Tr } from "@/components/ui";
import { Facts } from "@/components/workspace/Facts";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { ScrollingTable } from "../metrics/ScrollingTable";
import {
  RUN_STATE_TONES,
  backupState,
  drillState,
  largestTables,
  tableName,
  type AdminSystem,
  type MaintenanceRun,
  type RunState,
} from "../../_lib/system";
import { RUN_STATE_NAMES, useSystemFormat } from "./useSystemFormat";

/** The database's size and its largest tables, from the catalog (no table is scanned). */
export function DatabaseCard({ totalBytes, tables }: { totalBytes: number | null | undefined; tables: AdminSystem["tables"] }) {
  const { t } = useI18n();
  const format = useSystemFormat();
  const title = t("adminSystem.database.title");
  const shown = largestTables(tables);
  return (
    <Card aria-label={title} title={title} description={t("adminSystem.database.description")} padded={false}>
      {totalBytes === null || totalBytes === undefined ? (
        <p className="p-5 text-sm text-ink-muted">{t("adminSystem.database.unmeasured")}</p>
      ) : (
        <>
          <div className="border-b border-line px-5 py-4">
            <Facts items={[{ label: t("adminSystem.database.total"), value: format.bytes(totalBytes) }]} />
          </div>
          <ScrollingTable caption={t("adminSystem.database.largest")}>
            <THead>
              <Tr>
                <Th>{t("adminSystem.database.table")}</Th>
                <Th align="right">{t("adminSystem.database.size")}</Th>
                <Th align="right">{t("adminSystem.database.rows")}</Th>
              </Tr>
            </THead>
            <TBody>
              {shown.map((table) => (
                <Tr key={table.table}>
                  <Td className="font-mono text-xs">{tableName(table.table)}</Td>
                  <Td align="right" className="whitespace-nowrap">
                    {format.bytes(table.total_bytes)}
                  </Td>
                  <Td align="right" className="text-ink-muted">
                    {format.number(table.row_estimate)}
                  </Td>
                </Tr>
              ))}
            </TBody>
          </ScrollingTable>
        </>
      )}
    </Card>
  );
}

const HINTS: Partial<Record<`${"backup" | "drill"}.${RunState}`, MessageKey>> = {
  "backup.overdue": "adminSystem.backups.hints.backupOverdue",
  "backup.missing": "adminSystem.backups.hints.backupMissing",
  "drill.overdue": "adminSystem.backups.hints.drillOverdue",
  "drill.missing": "adminSystem.backups.hints.drillMissing",
};

/** The last off-site backup and the last restore drill, as the CLIs recorded them. */
export function BackupsCard({ system }: { system: AdminSystem }) {
  const { t } = useI18n();
  const title = t("adminSystem.backups.title");
  return (
    <Card aria-label={title} title={title} description={t("adminSystem.backups.description")}>
      <div className="space-y-5">
        <RunSummary which="backup" label={t("adminSystem.backups.backup")} run={system.last_backup} state={backupState(system)} />
        <RunSummary
          which="drill"
          label={t("adminSystem.backups.drill")}
          run={system.last_restore_drill}
          state={drillState(system)}
        />
      </div>
    </Card>
  );
}

function RunSummary({
  which,
  label,
  run,
  state,
}: {
  which: "backup" | "drill";
  label: string;
  run: MaintenanceRun | null | undefined;
  state: RunState;
}) {
  const { t } = useI18n();
  const format = useSystemFormat();
  const hint = HINTS[`${which}.${state}`];
  return (
    <section aria-label={label} className="space-y-3">
      <h3 className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
        {label}
        <Badge tone={RUN_STATE_TONES[state]}>{t(RUN_STATE_NAMES[state])}</Badge>
      </h3>
      {run ? (
        <Facts
          columns={2}
          items={[
            { label: t("adminSystem.backups.finished"), value: format.when(run.finished_at) },
            run.archive_size !== null && run.archive_size !== undefined
              ? { label: t("adminSystem.backups.archive"), value: format.bytes(run.archive_size) }
              : null,
            run.row_count !== null && run.row_count !== undefined
              ? { label: t("adminSystem.backups.rows"), value: format.number(run.row_count) }
              : null,
            run.release ? { label: t("adminSystem.backups.release"), value: <span className="font-mono text-xs">{run.release}</span> } : null,
          ]}
        />
      ) : (
        <p className="text-sm text-ink-muted">{t("adminSystem.backups.none")}</p>
      )}
      {run?.error ? (
        <Alert tone="danger" title={t("adminSystem.backups.error")}>
          <span lang="en" dir="ltr" className="break-words">
            {run.error}
          </span>
        </Alert>
      ) : null}
      {hint ? <p className="text-sm text-warning">{t(hint)}</p> : null}
    </section>
  );
}
