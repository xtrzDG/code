"use client";

import type { Schema } from "@/api/types";
import { Badge, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { useClientFormat } from "../../_lib/useClientFormat";
import { INVOICE_KIND_LABELS, INVOICE_STATUS_LABELS } from "../labels";

/** The client's invoices with their period, amount and status. */
export function InvoicesCard({ invoices, timeZone }: { invoices: Schema<"AdminInvoiceView">[]; timeZone: string }) {
  const { t } = useI18n();
  const { date, money } = useClientFormat(timeZone);
  return (
    <Card title={t("admin.detail.invoicesTitle")} padded={invoices.length === 0}>
      {invoices.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("admin.detail.noInvoices")}</p>
      ) : (
        <ul className="divide-y divide-line">
          {invoices.map((invoice) => (
            <li key={invoice.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 sm:px-6">
              <div className="text-sm">
                <p className="font-medium text-ink">{t(INVOICE_KIND_LABELS[invoice.kind])}</p>
                <p className="text-xs text-ink-muted">
                  {t("billing.dateRange", { start: date(invoice.period_start), end: date(invoice.period_end) })}
                </p>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium">{money(invoice.amount.amount_minor, invoice.amount.currency_code)}</span>
                <Badge tone={invoice.status === "paid" ? "success" : invoice.status === "void" ? "neutral" : invoice.status === "failed" ? "danger" : "warning"}>
                  {t(INVOICE_STATUS_LABELS[invoice.status])}
                </Badge>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
