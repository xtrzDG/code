"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { Badge, Card, EmptyState } from "@/components/ui";
import { IconFile } from "@/components/workspace/icons";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { INVOICE_STATUS_TONES, sortInvoices, type InvoiceStatus, type InvoiceView } from "../_lib/billing";

const STATUS_LABELS: Record<InvoiceStatus, MessageKey> = {
  issued: "billing.invoices.status.issued",
  paid: "billing.invoices.status.paid",
  failed: "billing.invoices.status.failed",
  void: "billing.invoices.status.void",
};

const KIND_LABELS: Record<InvoiceView["kind"], MessageKey> = {
  service_period: "billing.invoices.kinds.service_period",
  setup_fee: "billing.invoices.kinds.setup_fee",
};

/** Invoices with their status, period and amount in the invoice currency. */
export function InvoicesCard({ invoices }: { invoices: readonly InvoiceView[] | undefined }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const sorted = sortInvoices(invoices);

  return (
    <Card title={t("billing.invoices.title")} padded={sorted.length === 0}>
      {sorted.length === 0 ? (
        <EmptyState
          className="py-6"
          icon={<IconFile className="size-6" />}
          title={t("billing.invoices.emptyTitle")}
          description={t("billing.invoices.emptyDescription")}
        />
      ) : (
        <ul className="divide-y divide-line">
          {sorted.map((invoice) => (
            <li key={invoice.id} className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2 px-5 py-4 sm:px-6">
              <div className="min-w-0 flex-1 basis-56">
                <p className="text-sm font-medium text-ink">
                  {t(KIND_LABELS[invoice.kind])}
                  <span className="text-ink-subtle"> · </span>
                  <span className="font-normal text-ink-muted">
                    {t("billing.dateRange", { start: format.date(invoice.period_start), end: format.date(invoice.period_end) })}
                  </span>
                </p>
                <p className="mt-0.5 text-sm break-words text-ink-muted" dir="auto">
                  {invoice.description}
                </p>
                <p className="mt-0.5 text-xs text-ink-subtle">{t("billing.invoices.issuedOn", { date: format.date(invoice.issued_at) })}</p>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1.5 text-right">
                <p className="text-sm font-semibold text-ink">
                  {format.money(invoice.amount.money.amount_minor, invoice.amount.money.currency_code)}
                  {invoice.amount.is_estimated ? (
                    <span className="ml-1 text-xs font-normal text-ink-subtle">({t("billing.invoices.estimated")})</span>
                  ) : null}
                </p>
                <Badge tone={INVOICE_STATUS_TONES[invoice.status]}>{t(STATUS_LABELS[invoice.status])}</Badge>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
