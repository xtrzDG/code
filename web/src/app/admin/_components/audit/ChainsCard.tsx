"use client";

import Link from "next/link";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { Card, ErrorState, SkeletonText } from "@/components/ui";
import { AuditChainSummary, useChainProblemText } from "@/components/workspace/AuditChainSummary";
import { Facts } from "@/components/workspace/Facts";
import { useI18n } from "@/i18n/client";

import type { BrokenAuditChain } from "../../_lib/audit";
import { adminClientPath } from "../../_lib/clients";
import { useSystemFormat } from "../system/useSystemFormat";

/**
 * The daily tamper check of every audit log: the platform's own, how many
 * business logs were found unchanged and changed, and the changed ones
 * with the entry and the problem (each links to its client).
 */
export function ChainsCard() {
  const { t } = useI18n();
  const format = useSystemFormat();
  const chains = useQuery(queryKeys.admin.auditChains(), () => api.GET("/v1/admin/audit-log/chains"), { staleMs: 0 });
  const data = chains.data;
  const title = t("adminAudit.chains.title");

  return (
    <Card aria-label={title} title={title}>
      {chains.error && !data ? (
        <ErrorState error={chains.error} onRetry={chains.reload} />
      ) : !data ? (
        <SkeletonText lines={4} />
      ) : (
        <div className="space-y-5">
          <AuditChainSummary view={data.platform} title={t("adminAudit.chains.platform")} formatWhen={(micros) => format.when(micros)} />
          <Facts
            items={[
              { label: t("adminAudit.chains.intact"), value: format.number(data.intact_chains) },
              { label: t("adminAudit.chains.broken"), value: format.number(data.broken_chains) },
            ]}
          />
          {data.broken && data.broken.length > 0 ? (
            <BrokenChains chains={data.broken} />
          ) : (
            <p className="text-sm text-ink-muted">{t("adminAudit.chains.allIntact")}</p>
          )}
        </div>
      )}
    </Card>
  );
}

function BrokenChains({ chains }: { chains: readonly BrokenAuditChain[] }) {
  const { t } = useI18n();
  const format = useSystemFormat();
  const problemText = useChainProblemText();
  return (
    <section aria-label={t("adminAudit.chains.brokenList")} className="space-y-2">
      <h3 className="text-sm font-medium text-ink">{t("adminAudit.chains.brokenList")}</h3>
      <ul className="divide-y divide-line rounded-xl border border-danger/25">
        {chains.map((chain) => (
          <li key={chain.business_id ?? "platform"} className="grid gap-1 px-4 py-3 text-sm sm:grid-cols-[minmax(0,1fr)_auto] sm:gap-x-4">
            <div className="min-w-0">
              {chain.business_id ? (
                <Link href={adminClientPath(chain.business_id)} className="font-mono text-xs break-all text-accent underline-offset-2 hover:underline">
                  {chain.business_id}
                </Link>
              ) : (
                <span className="font-medium">{t("adminAudit.chains.platformName")}</span>
              )}
              <p className="text-danger">
                {t("adminAudit.chains.entry")} {chain.broken_position ? format.number(chain.broken_position) : "—"}: {problemText(chain.problem)}
              </p>
            </div>
            <p className="text-xs text-ink-subtle sm:text-end">
              {t("adminAudit.chains.checked")} {format.when(chain.checked_at)}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
