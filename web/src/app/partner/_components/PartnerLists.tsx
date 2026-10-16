"use client";

import type { Schema } from "@/api/types";
import { Badge, Button, Card, ErrorState, LoadingRegion, SkeletonRows } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryName } from "@/lib/countries";
import { formatDate, formatMoney } from "@/lib/format";

import { usePartnerCommissions, usePartnerReferrals } from "../_lib/usePartnerPortal";

/** Commission months and dates are UTC: one payout month for everyone. */
const TIME_ZONE = "UTC";

type PartnerReferralView = Schema<"PartnerReferralView">;
type CommissionEntryView = Schema<"CommissionEntryView">;

/** The businesses the partner's links brought, newest first. */
export function PartnerBusinesses() {
  const { t, locale } = useI18n();
  const page = usePartnerReferrals();
  const items = page.items ?? [];
  return (
    <Card title={t("partnerPortal.businesses.title")} padded={false}>
      <PagedList
        error={page.error}
        isLoading={!page.items}
        isEmpty={items.length === 0}
        emptyText={t("partnerPortal.businesses.empty")}
        hasMore={page.hasMore}
        isLoadingMore={page.isLoadingMore}
        onMore={page.loadMore}
        onRetry={page.reload}
      >
        {items.map((item) => (
          <BusinessRow key={item.business_id} item={item} locale={locale} />
        ))}
      </PagedList>
    </Card>
  );
}

function BusinessRow({ item, locale }: { item: PartnerReferralView; locale: string }) {
  const { t } = useI18n();
  const date = (value: number) => formatDate(value, { locale, timeZone: TIME_ZONE });
  return (
    <li className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-5 py-3" data-testid="partner-business">
      <div className="min-w-0">
        <p className="truncate font-medium text-ink">{item.business_name ?? t("partnerPortal.businesses.unnamed")}</p>
        <p className="text-xs text-ink-subtle">
          {[item.country_code ? countryName(item.country_code, locale) : null, `${t("partnerPortal.businesses.signedUp")} ${date(item.referred_at)}`]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>
      <p className="text-sm text-ink-muted">
        {t("partnerPortal.businesses.firstPaid")}:{" "}
        {item.first_paid_at ? date(item.first_paid_at) : t("partnerPortal.businesses.notYet")}
      </p>
    </li>
  );
}

/** The partner's commission on each paid invoice, newest first. */
export function PartnerCommissions() {
  const { t, locale } = useI18n();
  const page = usePartnerCommissions();
  const items = page.items ?? [];
  return (
    <Card title={t("partnerPortal.commissions.title")} padded={false}>
      <PagedList
        error={page.error}
        isLoading={!page.items}
        isEmpty={items.length === 0}
        emptyText={t("partnerPortal.commissions.empty")}
        hasMore={page.hasMore}
        isLoadingMore={page.isLoadingMore}
        onMore={page.loadMore}
        onRetry={page.reload}
      >
        {items.map((item) => (
          <CommissionRow key={item.id} item={item} locale={locale} />
        ))}
      </PagedList>
    </Card>
  );
}

function CommissionRow({ item, locale }: { item: CommissionEntryView; locale: string }) {
  const { t } = useI18n();
  return (
    <li className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-5 py-3" data-testid="partner-commission">
      <div className="min-w-0">
        <p className="truncate font-medium text-ink">{item.business_name ?? t("partnerPortal.businesses.unnamed")}</p>
        <p className="text-xs text-ink-subtle">
          {item.month} · {t("partnerPortal.commissions.base")} {formatMoney(item.base_minor, item.currency_code, locale)}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <span className="font-semibold text-ink tabular-nums">{formatMoney(item.amount_minor, item.currency_code, locale)}</span>
        <Badge tone={item.status === "paid" ? "success" : "neutral"}>{t(`partnerPortal.commissions.statuses.${item.status}`)}</Badge>
      </div>
    </li>
  );
}

function PagedList({
  error,
  isLoading,
  isEmpty,
  emptyText,
  hasMore,
  isLoadingMore,
  onMore,
  onRetry,
  children,
}: {
  error: unknown;
  isLoading: boolean;
  isEmpty: boolean;
  emptyText: string;
  hasMore: boolean;
  isLoadingMore: boolean;
  onMore: () => void;
  onRetry: () => void;
  children: React.ReactNode;
}) {
  const { t } = useI18n();
  if (error && isLoading) {
    return (
      <div className="p-5">
        <ErrorState error={error} onRetry={onRetry} />
      </div>
    );
  }
  if (isLoading) {
    return (
      <LoadingRegion label={t("partnerPortal.loading")}>
        <div className="p-5">
          <SkeletonRows rows={3} />
        </div>
      </LoadingRegion>
    );
  }
  if (isEmpty) {
    return <p className="px-5 py-4 text-sm text-ink-muted">{emptyText}</p>;
  }
  return (
    <>
      <ul className="divide-y divide-line">{children}</ul>
      {hasMore ? (
        <div className="border-t border-line p-3 text-center">
          <Button variant="ghost" size="sm" isLoading={isLoadingMore} onClick={onMore}>
            {t("partnerPortal.showMore")}
          </Button>
        </div>
      ) : null}
    </>
  );
}
