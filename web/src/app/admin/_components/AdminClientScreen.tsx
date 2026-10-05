"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useNiches } from "@/api/catalog";
import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { IconArrowLeft, IconExternal } from "@/components/icons";
import { Button, ButtonLink, Card, ErrorState, LoadingRegion, PageHeader } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryFlag, countryName } from "@/lib/countries";
import { ADMIN_PATH, businessPath } from "@/lib/navigation";

import { AdminClientSkeleton } from "./AdminSkeletons";
import { ClientUsageCard } from "./client/ClientUsageCard";
import { CostCard } from "./client/CostCard";
import { FailedAutotestsCard } from "./client/FailedAutotestsCard";
import { InvoicesCard } from "./client/InvoicesCard";
import { OpenCabinetDialog } from "./client/OpenCabinetDialog";
import { OverviewCard } from "./client/OverviewCard";
import { PaymentsCard } from "./client/PaymentsCard";
import { QualityCard } from "./client/QualityCard";
import { ReplyGuardCard } from "./client/ReplyGuardCard";
import { ReplySpeedCard } from "./client/ReplySpeedCard";
import { HealthBadge, IssueChips } from "./ClientBits";

/** /admin/clients/[businessId]: one client's health explained, and an audited way into their cabinet. */
export function AdminClientScreen({ businessId }: { businessId: string }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const niches = useNiches();
  const [isConfirming, setConfirming] = useState(false);
  const [openError, setOpenError] = useState<ApiError | null>(null);

  const detail = useQuery(queryKeys.admin.client(businessId), () =>
    api.GET("/v1/admin/clients/{business_id}", { params: { path: { business_id: businessId } } }),
  );
  const open = useMutation(
    (reason: string) =>
      api.POST("/v1/admin/clients/{business_id}/open", { params: { path: { business_id: businessId } }, body: { reason } }),
    { errorToast: false },
  );

  const onOpen = async (reason: string) => {
    const result = await open.run(reason);
    if (result.ok) {
      router.push(businessPath(result.data.business_id, "overview"));
    } else {
      setOpenError(result.error);
    }
  };

  const data = detail.data;
  const summary = data?.summary;
  const nicheName = (key: string) => niches.data?.niches.find((niche) => niche.key === key)?.name ?? key;

  return (
    <>
      <ButtonLink href={ADMIN_PATH} variant="ghost" size="sm" className="mb-4 -ml-3" leadingIcon={<IconArrowLeft className="size-4" aria-hidden />}>
        {t("admin.detail.back")}
      </ButtonLink>

      {detail.error && !data ? (
        <Card>
          <ErrorState error={detail.error} onRetry={detail.reload} />
        </Card>
      ) : !data || !summary ? (
        <LoadingRegion label={t("common.loading")}>
          <AdminClientSkeleton />
        </LoadingRegion>
      ) : (
        <>
          <PageHeader
            eyebrow={
              <>
                <span aria-hidden>{countryFlag(summary.country_code)} </span>
                {[countryName(summary.country_code, locale), nicheName(summary.niche_key)].join(" · ")}
              </>
            }
            title={<span dir="auto">{summary.name}</span>}
            actions={
              <Button
                leadingIcon={<IconExternal className="size-4" aria-hidden />}
                onClick={() => {
                  setOpenError(null);
                  setConfirming(true);
                }}
              >
                {t("admin.detail.openCabinet")}
              </Button>
            }
          />

          <div className="space-y-6">
            <Card title={t("admin.detail.issuesTitle")} actions={<HealthBadge status={summary.health_status} />}>
              {(summary.health_issues ?? []).length > 0 ? (
                <IssueChips issues={summary.health_issues ?? []} />
              ) : (
                <p className="text-sm text-ink-muted">{t("admin.detail.noIssues")}</p>
              )}
            </Card>

            <div className="grid gap-6 xl:grid-cols-3">
              <OverviewCard summary={summary} timeZone={data.timezone} />
              <ClientUsageCard summary={summary} />
            </div>

            <ReplySpeedCard summary={summary} />
            <ReplyGuardCard summary={summary} />
            <QualityCard businessId={businessId} timeZone={data.timezone} />
            <CostCard summary={summary} timeZone={data.timezone} />
            <FailedAutotestsCard tests={data.failed_autotests ?? []} />

            <div className="grid gap-6 xl:grid-cols-2">
              <InvoicesCard invoices={data.invoices ?? []} timeZone={data.timezone} />
              <PaymentsCard payments={data.payments ?? []} timeZone={data.timezone} />
            </div>
          </div>

          <OpenCabinetDialog
            open={isConfirming}
            name={summary.name}
            isPending={open.isPending}
            error={openError}
            onClose={() => setConfirming(false)}
            onOpen={onOpen}
          />
        </>
      )}
    </>
  );
}
