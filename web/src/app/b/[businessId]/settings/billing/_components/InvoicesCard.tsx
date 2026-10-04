"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { Badge, Button, Card, EmptyState } from "@/components/ui";
import { IconDownload, IconFile } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { INVOICE_STATUS_TONES, sortInvoices, type InvoiceStatus, type InvoiceView } from "../_lib/billing";
import { canDownloadInvoice, formatTaxRate } from "../_lib/billingDetails";
import { useBillingDocumentDownload } from "../_lib/useBillingDocumentDownload";

const STATUS_LABELS: Record<InvoiceStatus, MessageKey> = {
  issued: "billing.invoices.status.issued",
  paid: "billing.invoices.status.paid",
  failed: "billing.invoices.status.failed",
  void: "billing.invoices.status.void",
};

const KIND_LABELS: Record<InvoiceView["kind"], MessageKey> = {
  service_period: "billing.invoices.kinds.service_period",
  setup_fee: "billing.invoices.kinds.setup_fee",
  usage_overage: "billing.invoices.kinds.usage_overage",
};

/**
 * Invoices with their number, status, period and amount in the invoice
 * currency (with the VAT in it), and the invoice and receipt as PDFs.
 */
export function InvoicesCard({ invoices }: { invoices: readonly InvoiceView[] | undefined }) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const documents = useBillingDocumentDownload();
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
          {sorted.map((invoice) => {
            const name = invoice.number ?? format.date(invoice.issued_at);
            const isLoading = (kind: string) => documents.pending === `${invoice.id}:${kind}`;
            return (
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
                  <p className="mt-0.5 text-xs text-ink-subtle">
                    {invoice.number ? (
                      <>
                        <span className="tabular-nums" dir="ltr">
                          {t("billing.invoices.number", { number: invoice.number })}
                        </span>
                        <span> · </span>
                      </>
                    ) : null}
                    {t("billing.invoices.issuedOn", { date: format.date(invoice.issued_at) })}
                    {invoice.paid_at ? (
                      <>
                        <span> · </span>
                        {t("billing.invoices.paidOn", { date: format.date(invoice.paid_at) })}
                      </>
                    ) : null}
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 max-sm:w-full sm:flex-col sm:items-end sm:gap-1.5 sm:text-right">
                  <p className="text-sm font-semibold text-ink">
                    {format.money(invoice.amount.money.amount_minor, invoice.amount.money.currency_code)}
                    {invoice.amount.is_estimated ? (
                      <span className="ml-1 text-xs font-normal text-ink-subtle">({t("billing.invoices.estimated")})</span>
                    ) : null}
                  </p>
                  {invoice.tax && invoice.tax_rate_basis_points ? (
                    <p className="text-xs text-ink-subtle">
                      {t("billing.invoices.tax", {
                        rate: formatTaxRate(invoice.tax_rate_basis_points, locale),
                        amount: format.money(invoice.tax.money.amount_minor, invoice.tax.money.currency_code),
                      })}
                    </p>
                  ) : null}
                  <Badge tone={INVOICE_STATUS_TONES[invoice.status]}>{t(STATUS_LABELS[invoice.status])}</Badge>
                </div>
                {canDownloadInvoice(invoice) || invoice.is_receipt_available ? (
                  <div className="flex w-full flex-wrap gap-2">
                    {canDownloadInvoice(invoice) ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        leadingIcon={<IconDownload className="size-4" />}
                        isLoading={isLoading("invoice")}
                        loadingText={t("billing.documents.downloading")}
                        disabled={documents.pending !== null && !isLoading("invoice")}
                        aria-label={t("billing.documents.invoiceLabel", { name })}
                        onClick={() => void documents.run(invoice, "invoice")}
                      >
                        {t("billing.documents.invoice")}
                      </Button>
                    ) : null}
                    {invoice.is_receipt_available ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        leadingIcon={<IconDownload className="size-4" />}
                        isLoading={isLoading("receipt")}
                        loadingText={t("billing.documents.downloading")}
                        disabled={documents.pending !== null && !isLoading("receipt")}
                        aria-label={t("billing.documents.receiptLabel", { name })}
                        onClick={() => void documents.run(invoice, "receipt")}
                      >
                        {t("billing.documents.receipt")}
                      </Button>
                    ) : null}
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
