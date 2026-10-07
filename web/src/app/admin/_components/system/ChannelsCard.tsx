"use client";

import Link from "next/link";

import { Badge, Card } from "@/components/ui";
import { CHANNEL_NAMES } from "@/components/workspace/channelNames";
import { useI18n } from "@/i18n/client";

import { adminClientPath } from "../../_lib/clients";
import type { ChannelIssue } from "../../_lib/system";
import { useSystemFormat } from "./useSystemFormat";

/** Channels in ERROR (with their last error) and Meta tokens that run out within two weeks. */
export function ChannelsCard({
  inError,
  inErrorCount,
  expiring,
}: {
  inError: readonly ChannelIssue[];
  inErrorCount: number;
  expiring: readonly ChannelIssue[];
}) {
  const { t, tp } = useI18n();
  const hidden = inErrorCount - inError.length;
  return (
    <Card aria-label={t("adminSystem.channels.title")} title={t("adminSystem.channels.title")} description={t("adminSystem.channels.description")}>
      <div className="space-y-5">
        <section className="space-y-2">
          <h3 className="flex items-center gap-2 text-sm font-medium text-ink">
            {t("adminSystem.channels.inError")}
            <Badge tone={inErrorCount > 0 ? "danger" : "neutral"}>{inErrorCount}</Badge>
          </h3>
          {inError.length === 0 ? (
            <p className="text-sm text-ink-muted">{t("adminSystem.channels.noneInError")}</p>
          ) : (
            <ul className="divide-y divide-line rounded-xl border border-line">
              {inError.map((issue) => (
                <IssueRow key={issue.channel_id} issue={issue} kind="error" />
              ))}
            </ul>
          )}
          {hidden > 0 ? <p className="text-xs text-ink-subtle">{tp("adminSystem.channels.more", hidden)}</p> : null}
        </section>
        <section className="space-y-2">
          <h3 className="flex items-center gap-2 text-sm font-medium text-ink">
            {t("adminSystem.channels.expiring")}
            <Badge tone={expiring.length > 0 ? "warning" : "neutral"}>{expiring.length}</Badge>
          </h3>
          {expiring.length === 0 ? (
            <p className="text-sm text-ink-muted">{t("adminSystem.channels.noneExpiring")}</p>
          ) : (
            <ul className="divide-y divide-line rounded-xl border border-line">
              {expiring.map((issue) => (
                <IssueRow key={issue.channel_id} issue={issue} kind="expiring" />
              ))}
            </ul>
          )}
        </section>
      </div>
    </Card>
  );
}

function IssueRow({ issue, kind }: { issue: ChannelIssue; kind: "error" | "expiring" }) {
  const { t } = useI18n();
  const format = useSystemFormat();
  return (
    <li className="space-y-1 px-4 py-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-medium text-ink">{t(CHANNEL_NAMES[issue.kind])}</span>
        <Link
          href={adminClientPath(issue.business_id)}
          className="min-w-0 text-sm break-words text-accent-ink underline-offset-2 hover:underline"
          dir="auto"
          data-user-content={issue.business_name ? true : undefined}
        >
          {issue.business_name ?? t("adminSystem.channels.unnamed")}
        </Link>
        {kind === "expiring" && issue.is_expired ? <Badge tone="danger">{t("adminSystem.channels.expired")}</Badge> : null}
      </div>
      {kind === "error" ? (
        <>
          <p className="text-sm break-words text-ink-muted" lang="en" dir="ltr">
            {issue.last_error ?? t("adminSystem.channels.noErrorText")}
          </p>
          {issue.last_error_at ? (
            <p className="text-xs text-ink-subtle">{t("adminSystem.channels.errorSince", { time: format.when(issue.last_error_at) })}</p>
          ) : null}
        </>
      ) : (
        <p className={issue.is_expired ? "text-sm text-danger" : "text-sm text-warning"}>
          {t(issue.is_expired ? "adminSystem.channels.expiredAt" : "adminSystem.channels.expiresAt", {
            time: format.when(issue.credential_expires_at),
          })}
        </p>
      )}
    </li>
  );
}
