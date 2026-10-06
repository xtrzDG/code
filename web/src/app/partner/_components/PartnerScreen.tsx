"use client";

import type { Schema } from "@/api/types";
import { Alert, Card, ErrorState, LoadingRegion, PageHeader, SkeletonCard } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatMoney, formatNumber } from "@/lib/format";
import { basisPointsToPercent } from "@/lib/referrals/referralLinks";

import { usePartnerPortal } from "../_lib/usePartnerPortal";
import { PartnerLinks } from "./PartnerLinks";
import { PartnerBusinesses, PartnerCommissions } from "./PartnerLists";

type CommissionTotalView = Schema<"CommissionTotalView">;

/**
 * /partner: a partner's links (with a QR code for each place they share
 * them), the businesses those links brought, and the commission of every
 * invoice those businesses paid, before tax.
 */
export function PartnerScreen() {
  const { t, locale } = useI18n();
  const portal = usePartnerPortal();
  const view = portal.data;

  if (portal.error && !view) {
    return (
      <Card>
        <ErrorState error={portal.error} onRetry={portal.reload} />
      </Card>
    );
  }
  if (!view) {
    return <PartnerSkeleton />;
  }
  const rate = formatNumber(basisPointsToPercent(view.commission_rate_basis_points) / 100, locale, { style: "percent", maximumFractionDigits: 2 });
  return (
    <>
      <PageHeader title={t("partnerPortal.title")} description={t("partnerPortal.description")} />
      <div className="space-y-6">
        {view.status === "paused" ? <Alert tone="warning">{t("partnerPortal.paused")}</Alert> : null}
        <Card title={t("partnerPortal.totals.title")} description={t("partnerPortal.rate", { rate })}>
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Tile label={t("partnerPortal.totals.businesses")} value={formatNumber(view.referred_businesses, locale)} />
            <Tile label={t("partnerPortal.totals.paying")} value={formatNumber(view.paid_businesses, locale)} />
            <Tile label={t("partnerPortal.totals.accrued")} value={sumOf(view.totals ?? [], "accrued", locale) ?? "—"} />
            <Tile label={t("partnerPortal.totals.paid")} value={sumOf(view.totals ?? [], "paid", locale) ?? "—"} />
          </dl>
        </Card>
        <PartnerLinks codes={view.codes ?? []} />
        <PartnerBusinesses />
        <PartnerCommissions />
        <p className="text-xs text-ink-subtle">{t("partnerPortal.legal")}</p>
      </div>
    </>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line px-4 py-3">
      <dt className="text-xs text-ink-subtle">{label}</dt>
      <dd className="mt-1 text-lg font-semibold text-ink tabular-nums">{value}</dd>
    </div>
  );
}

/** The totals of one status, one amount per currency ("₾103.40 · €20.00"); null when there are none. */
function sumOf(totals: readonly CommissionTotalView[], status: CommissionTotalView["status"], locale: string): string | null {
  const amounts = totals.filter((total) => total.status === status && total.amount_minor > 0);
  return amounts.length === 0
    ? null
    : amounts.map((total) => formatMoney(total.amount_minor, total.currency_code, locale)).join(" · ");
}

/** The portal while it loads (also the route's loading.tsx). */
export function PartnerSkeleton() {
  const { t } = useI18n();
  return (
    <LoadingRegion label={t("partnerPortal.loading")}>
      <div className="space-y-6">
        <SkeletonCard lines={3} />
        <SkeletonCard lines={4} />
        <SkeletonCard lines={4} />
      </div>
    </LoadingRegion>
  );
}
