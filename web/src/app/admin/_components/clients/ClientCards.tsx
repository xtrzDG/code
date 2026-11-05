"use client";

import Link from "next/link";

import { IconChevronRight } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { countryFlag } from "@/lib/countries";
import { formatMoney } from "@/lib/format";

import { adminClientPath, type AdminClientSummary } from "../../_lib/clients";
import { HealthBadge, IssueChips, Margin, ProviderCost } from "../ClientBits";
import { PLAN_LABELS, SUBSCRIPTION_LABELS } from "../labels";
import { UsageSummary } from "./UsageSummary";

/** The clients as cards linking to their details (narrow screens). */
export function ClientCards({ clients, nicheName }: { clients: AdminClientSummary[]; nicheName: (key: string) => string }) {
  const { t, locale } = useI18n();
  return (
    <ul className="divide-y divide-line border-t border-line lg:hidden">
      {clients.map((client) => (
        <li key={client.business_id}>
          <Link
            href={adminClientPath(client.business_id)}
            className="flex items-start gap-3 px-5 py-4 hover:bg-surface-muted/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus sm:px-6"
            aria-label={t("admin.openDetails", { name: client.name })}
          >
            <div className="min-w-0 flex-1 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-ink" dir="auto" data-user-content>
                  {client.name}
                </span>
                <HealthBadge status={client.health_status} />
              </div>
              <p className="text-xs text-ink-muted">
                <span aria-hidden>{countryFlag(client.country_code)} </span>
                {[
                  nicheName(client.niche_key),
                  t(PLAN_LABELS[client.plan_key]),
                  client.subscription_status ? t(SUBSCRIPTION_LABELS[client.subscription_status]) : t("admin.noSubscription"),
                ].join(" · ")}
              </p>
              <IssueChips issues={client.health_issues ?? []} limit={3} />
              <UsageSummary client={client} />
              <dl className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <dt className="text-ink-subtle">{t("admin.columns.cost")}</dt>
                  <dd className="font-medium">
                    <ProviderCost cost={client.cost} />
                  </dd>
                </div>
                <div>
                  <dt className="text-ink-subtle">{t("admin.columns.revenue")}</dt>
                  <dd className="font-medium">
                    {formatMoney(client.cost.revenue.amount_minor, client.cost.revenue.currency_code, locale)}
                  </dd>
                </div>
                <div>
                  <dt className="text-ink-subtle">{t("admin.columns.margin")}</dt>
                  <dd className="font-medium">
                    <Margin cost={client.cost} />
                  </dd>
                </div>
              </dl>
            </div>
            <IconChevronRight className="mt-1 size-5 shrink-0 text-ink-subtle rtl:-scale-x-100" aria-hidden />
          </Link>
        </li>
      ))}
    </ul>
  );
}
