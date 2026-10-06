"use client";

import { useState } from "react";

import type { Schema } from "@/api/types";
import { Button, Card, ConfirmDialog, ErrorState, Field, Input, LoadingRegion, Select, SkeletonText, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatMoney, formatNumber } from "@/lib/format";

import { payoutMonths } from "../_lib/partnerForms";
import { usePayouts } from "../_lib/useAdminPartners";

type PayoutRowView = Schema<"PayoutRowView">;

/**
 * Payouts: the commissions earned in one UTC month, per partner and
 * currency, and "Mark paid" after the bank transfer (with its reference,
 * written to the audit log). A billing admin's work; others see the
 * report and the API refuses them the change.
 */
export function PayoutsCard({ canMarkPaid }: { canMarkPaid: boolean }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const [months] = useState(() => payoutMonths(new Date()));
  const [month, setMonth] = useState(months[0] ?? "");
  const { report, markPaid, marking } = usePayouts(month);
  const [paying, setPaying] = useState<PayoutRowView | null>(null);
  const [reference, setReference] = useState("");
  const rows = report.data?.rows ?? [];

  const confirm = async () => {
    if (paying && reference.trim() !== "" && (await markPaid(paying.partner_id, reference.trim()))) {
      setPaying(null);
      toast.success(t("adminPartners.payouts.markedPaid"));
    }
  };

  return (
    <Card
      title={t("adminPartners.payouts.title")}
      description={t("adminPartners.payouts.description")}
      actions={
        <Field label={t("adminPartners.payouts.month")}>
          {(control) => (
            <Select {...control} value={month} onChange={(event) => setMonth(event.target.value)} className="w-36">
              {months.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </Select>
          )}
        </Field>
      }
    >
      {report.error && !report.data ? (
        <ErrorState error={report.error} onRetry={report.reload} />
      ) : !report.data ? (
        <LoadingRegion label={t("adminPartners.loading")}>
          <SkeletonText lines={3} />
        </LoadingRegion>
      ) : rows.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("adminPartners.payouts.empty")}</p>
      ) : (
        <ul className="divide-y divide-line">
          {rows.map((row) => (
            <li key={`${row.partner_id}:${row.currency_code}`} className="flex flex-wrap items-center justify-between gap-3 py-3" data-testid="payout-row">
              <div className="min-w-0">
                <p className="font-medium text-ink">{row.partner_name ?? row.partner_id}</p>
                <p className="text-xs text-ink-subtle">
                  {t("adminPartners.payouts.accrued")}: {formatMoney(row.accrued_minor, row.currency_code, locale)} (
                  {t("adminPartners.payouts.invoices", { count: formatNumber(row.accrued_invoices, locale) })}) ·{" "}
                  {t("adminPartners.payouts.paid")}: {formatMoney(row.paid_minor, row.currency_code, locale)}
                </p>
              </div>
              {canMarkPaid && row.accrued_minor > 0 ? (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    setReference("");
                    setPaying(row);
                  }}
                >
                  {t("adminPartners.payouts.markPaid")}
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={paying !== null}
        onClose={() => setPaying(null)}
        onConfirm={confirm}
        tone="primary"
        isPending={marking.isPending}
        error={marking.error}
        errorOverrides={{ conflict: "adminPartners.payouts.nothingDue" }}
        confirmDisabled={reference.trim() === ""}
        title={t("adminPartners.payouts.markTitle", { month, name: paying?.partner_name ?? "" })}
        description={t("adminPartners.payouts.markDescription")}
        confirmLabel={t("adminPartners.payouts.markPaid")}
      >
        <Field label={t("adminPartners.payouts.reference")} hint={t("adminPartners.payouts.referenceHint")} required>
          {(control) => <Input {...control} autoComplete="off" value={reference} onChange={(event) => setReference(event.target.value)} />}
        </Field>
      </ConfirmDialog>
    </Card>
  );
}
