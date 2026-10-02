"use client";

import Link from "next/link";

import { Table, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryFlag, countryName } from "@/lib/countries";
import { formatMoney } from "@/lib/format";

import { adminClientPath, type AdminClientSummary } from "../../_lib/clients";
import { HealthBadge, IssueChips, Margin, ProviderCost } from "../ClientBits";
import { BUSINESS_STATUS_LABELS, PLAN_LABELS, SUBSCRIPTION_LABELS } from "../labels";
import { UsageSummary } from "./UsageSummary";

/** The clients as a table (wide screens). */
export function ClientsTable({ clients, nicheName }: { clients: AdminClientSummary[]; nicheName: (key: string) => string }) {
  const { t, locale } = useI18n();
  return (
    <div className="hidden border-t border-line lg:block">
      <Table caption={t("pages.admin.title")}>
        <THead>
          <Tr>
            <Th>{t("admin.columns.client")}</Th>
            <Th>{t("admin.columns.health")}</Th>
            <Th>{t("admin.columns.plan")}</Th>
            <Th>{t("admin.columns.usage")}</Th>
            <Th align="right">{t("admin.columns.cost")}</Th>
            <Th align="right">{t("admin.columns.revenue")}</Th>
            <Th align="right">{t("admin.columns.margin")}</Th>
          </Tr>
        </THead>
        <TBody>
          {clients.map((client) => (
            <Tr key={client.business_id}>
              <Td>
                <Link href={adminClientPath(client.business_id)} className="font-medium text-ink hover:text-accent hover:underline" dir="auto">
                  {client.name}
                </Link>
                <p className="mt-0.5 text-xs text-ink-muted">
                  <span aria-hidden>{countryFlag(client.country_code)} </span>
                  {[countryName(client.country_code, locale), nicheName(client.niche_key)].join(" · ")}
                </p>
                <p className="mt-1 text-xs text-ink-subtle">{t(BUSINESS_STATUS_LABELS[client.business_status])}</p>
              </Td>
              <Td className="max-w-64">
                <div className="space-y-1.5">
                  <HealthBadge status={client.health_status} />
                  <IssueChips issues={client.health_issues ?? []} limit={3} />
                </div>
              </Td>
              <Td>
                <p>{t(PLAN_LABELS[client.plan_key])}</p>
                <p className="mt-0.5 text-xs text-ink-muted">
                  {client.subscription_status ? t(SUBSCRIPTION_LABELS[client.subscription_status]) : t("admin.noSubscription")}
                </p>
              </Td>
              <Td>
                <UsageSummary client={client} />
              </Td>
              <Td align="right" className="whitespace-nowrap">
                <ProviderCost cost={client.cost} />
              </Td>
              <Td align="right" className="whitespace-nowrap">
                {formatMoney(client.cost.revenue.amount_minor, client.cost.revenue.currency_code, locale)}
              </Td>
              <Td align="right" className="whitespace-nowrap">
                <Margin cost={client.cost} />
              </Td>
            </Tr>
          ))}
        </TBody>
      </Table>
    </div>
  );
}
