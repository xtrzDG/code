"use client";

import { Card, LoadingRegion, PageHeader, SkeletonCard } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { ChainsCard } from "./ChainsCard";
import { PlatformLogCard } from "./PlatformLogCard";

/**
 * /admin/audit: the daily tamper check of every audit log and the
 * platform's own log (docs/operations/runbooks/audit-chain-broken.md and
 * audit-anomaly.md say what to do with them). The log names every
 * person's sign-ins with their addresses, so only admins who may read the
 * security log (`view_security_log`) get it; the others read why.
 */
export function AuditScreen({ showSecurityLog }: { showSecurityLog: boolean }) {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t("adminAudit.title")} description={t("adminAudit.description")} />
      <div className="space-y-6">
        <ChainsCard />
        {showSecurityLog ? (
          <PlatformLogCard />
        ) : (
          <Card aria-label={t("adminAudit.log.title")} title={t("adminAudit.log.title")}>
            <p className="text-sm text-ink-muted">{t("adminAudit.log.restricted")}</p>
          </Card>
        )}
      </div>
    </>
  );
}

/** The two cards while the page loads (the route's loading.tsx). */
export function AuditSkeleton() {
  const { t } = useI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <div className="space-y-6">
        <SkeletonCard lines={4} />
        <SkeletonCard lines={6} />
      </div>
    </LoadingRegion>
  );
}
