"use client";

import Link from "next/link";

import { Badge, Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { useViewerFormat } from "@/components/time/ViewerTimeZone";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatMoney, formatNumber } from "@/lib/format";
import { adminClientPath } from "@/lib/navigation";

import { budgetTone, isSpendSpike, microUsdToCents, spendingProviders, type PlatformSpend } from "../../_lib/spend";
import { useAdminSpend } from "../../_lib/useAdminSpend";

const BAR_TONES = { info: "bg-info", warning: "bg-warning", danger: "bg-danger" } as const;

/**
 * The overview's "Spend today" tile: the platform's provider spend of the
 * UTC day by provider, against the week before and the daily budget, and
 * the clients the spend guard has braked today. Hidden from a platform
 * admin whose role may not see it.
 */
export function SpendTile() {
  const { t } = useI18n();
  const spend = useAdminSpend();

  if (spend.error?.status === 403) {
    return null;
  }

  return (
    <Card
      title={t("adminSpend.title")}
      description={spend.data ? t("adminSpend.description", { day: spend.data.day }) : undefined}
      actions={spend.data && isSpendSpike(spend.data) ? <Badge tone="warning">{t("adminSpend.spike")}</Badge> : undefined}
    >
      {spend.error && !spend.data ? (
        <ErrorState error={spend.error} onRetry={spend.reload} />
      ) : !spend.data ? (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonText lines={4} />
        </LoadingRegion>
      ) : (
        <SpendBody spend={spend.data} />
      )}
    </Card>
  );
}

function SpendBody({ spend }: { spend: PlatformSpend }) {
  const { t, locale } = useI18n();
  const usd = (microUsd: number) => formatMoney(microUsdToCents(microUsd), "USD", locale);
  const providers = spendingProviders(spend);
  const percent = spend.budget_used_percent ?? null;

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div className="min-w-0 space-y-4">
        <div>
          <p className="text-xs font-medium text-ink-muted">{t("adminSpend.total")}</p>
          <p className="mt-1 text-3xl font-semibold text-ink tabular-nums">{usd(spend.total_micro_usd)}</p>
          <p className="mt-1 text-sm text-ink-muted">{t("adminSpend.weekMean", { amount: usd(spend.week_daily_mean_micro_usd) })}</p>
        </div>

        {percent !== null && spend.budget_micro_usd != null ? (
          <div className="space-y-1.5">
            <div
              role="progressbar"
              aria-label={t("adminSpend.budgetLabel")}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.min(percent, 100)}
              className="h-2 overflow-hidden rounded-full bg-surface-muted ring-1 ring-line/60"
            >
              <div className={cn("h-full rounded-full", BAR_TONES[budgetTone(percent)])} style={{ width: `${Math.min(percent, 100)}%` }} />
            </div>
            <p className="text-sm text-ink-muted">
              {t("adminSpend.budget", { percent: formatNumber(percent, locale), amount: usd(spend.budget_micro_usd) })}
            </p>
          </div>
        ) : (
          <p className="text-sm text-ink-muted">{t("adminSpend.noBudget")}</p>
        )}

        {providers.length > 0 ? (
          <dl aria-label={t("adminSpend.providersLabel")} className="divide-y divide-line rounded-xl border border-line">
            {providers.map((provider) => (
              <div key={provider.provider} className="flex items-baseline justify-between gap-3 px-3 py-2 text-sm">
                <dt className="min-w-0 text-ink-muted">{t(`adminSpend.providers.${provider.provider}`)}</dt>
                <dd className="font-medium text-ink tabular-nums">{usd(provider.spend_micro_usd)}</dd>
              </div>
            ))}
          </dl>
        ) : null}
      </div>

      <BrakedBusinesses spend={spend} usd={usd} />
    </div>
  );
}

function BrakedBusinesses({ spend, usd }: { spend: PlatformSpend; usd: (microUsd: number) => string }) {
  const { t } = useI18n();
  const viewer = useViewerFormat();
  const braked = spend.braked_businesses ?? [];

  return (
    <section aria-labelledby="admin-spend-braked" className="min-w-0 space-y-2">
      <h3 id="admin-spend-braked" className="text-sm font-medium text-ink">
        {t("adminSpend.brakedTitle")}
      </h3>
      {braked.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("adminSpend.brakedNone")}</p>
      ) : (
        <ul className="divide-y divide-line rounded-xl border border-line">
          {braked.map((mark) => (
            <li key={`${mark.business_id}:${mark.level}`} className="flex min-w-0 flex-wrap items-center justify-between gap-x-3 gap-y-1 px-3 py-2">
              <div className="min-w-0">
                <Link
                  href={adminClientPath(mark.business_id)}
                  dir="auto"
                  className="block truncate text-sm font-medium text-ink hover:text-accent hover:underline"
                >
                  {mark.business_name}
                </Link>
                <p className="text-xs text-ink-muted tabular-nums">
                  {t("adminSpend.brakedLine", {
                    spend: usd(mark.spend_micro_usd),
                    limit: usd(mark.limit_micro_usd),
                    time: viewer.time(mark.reached_at),
                  })}
                </p>
              </div>
              <Badge tone={mark.level === "hard_limit" ? "danger" : "warning"}>
                {t(mark.level === "hard_limit" ? "adminSpend.levels.hard_limit" : "adminSpend.levels.soft_limit")}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
