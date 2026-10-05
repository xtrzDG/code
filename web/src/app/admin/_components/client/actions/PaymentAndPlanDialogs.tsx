"use client";

import { useState } from "react";

import { api } from "@/api/client";
import type { RequestBody, Schema } from "@/api/types";
import { Field, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { cleanReference, isReferenceValid, openInvoices, REFERENCE_MAX } from "../../../_lib/accountActions";
import { useClientFormat } from "../../../_lib/useClientFormat";
import { INVOICE_KIND_LABELS, PLAN_LABELS } from "../../labels";
import { ActionDialog, useAccountAction, type AccountActionDialogProps } from "./ActionDialog";

type PlanKey = Schema<"PlanKey">;
type BillingPeriod = Schema<"BillingPeriod">;
type PaymentMethod = Schema<"ManualPaymentMethod">;

const METHODS: readonly PaymentMethod[] = ["bank_transfer", "cash"];
const PLANS = Object.keys(PLAN_LABELS) as PlanKey[];
const PERIODS: readonly BillingPeriod[] = ["monthly", "annual"];

/** Money that came by bank transfer or in cash pays one open bill now. */
export function ManualPaymentDialog({
  businessId,
  name,
  open,
  onClose,
  invoices,
  timeZone,
}: AccountActionDialogProps & { invoices: readonly Schema<"AdminInvoiceView">[]; timeZone: string }) {
  const { t } = useI18n();
  const { date, money } = useClientFormat(timeZone);
  const bills = openInvoices(invoices);
  const [invoiceId, setInvoiceId] = useState(bills[0]?.id ?? "");
  const [method, setMethod] = useState<PaymentMethod>("bank_transfer");
  const [reference, setReference] = useState("");
  const [isTouched, setTouched] = useState(false);
  const isValid = bills.some((bill) => bill.id === invoiceId) && isReferenceValid(reference);
  const action = useAccountAction(
    businessId,
    (body: RequestBody<"/v1/admin/clients/{business_id}/invoices/{invoice_id}/manual-payment", "post">) =>
      api.POST("/v1/admin/clients/{business_id}/invoices/{invoice_id}/manual-payment", {
        params: { path: { business_id: businessId, invoice_id: invoiceId } },
        body,
      }),
    onClose,
  );
  const billLabel = (bill: Schema<"AdminInvoiceView">) =>
    [
      bill.number ?? t(INVOICE_KIND_LABELS[bill.kind]),
      t("billing.dateRange", { start: date(bill.period_start), end: date(bill.period_end) }),
      money(bill.amount.amount_minor, bill.amount.currency_code),
    ].join(" · ");

  return (
    <ActionDialog
      open={open}
      onClose={onClose}
      title={t("adminActions.payment.title", { name })}
      description={t("adminActions.payment.description")}
      confirmLabel={t("adminActions.payment.confirm")}
      fieldsValid={isValid}
      isPending={action.isPending}
      error={action.error}
      onConfirm={(reason) => action.submit({ method, reference: cleanReference(reference), reason })}
    >
      {bills.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("adminActions.payment.noOpenInvoices")}</p>
      ) : (
        <>
          <Field label={t("adminActions.payment.invoice")} required>
            {(control) => (
              <Select {...control} value={invoiceId} onChange={(event) => setInvoiceId(event.target.value)}>
                {bills.map((bill) => (
                  <option key={bill.id} value={bill.id}>
                    {billLabel(bill)}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("adminActions.payment.method")} required>
              {(control) => (
                <Select {...control} value={method} onChange={(event) => setMethod(event.target.value as PaymentMethod)}>
                  {METHODS.map((option) => (
                    <option key={option} value={option}>
                      {t(`adminActions.payment.methods.${option}`)}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field
              label={t("adminActions.payment.reference")}
              hint={t("adminActions.payment.referenceHint")}
              error={isTouched && !isReferenceValid(reference) ? t("adminActions.payment.referenceInvalid") : undefined}
              required
            >
              {(control) => (
                <Input
                  {...control}
                  autoComplete="off"
                  maxLength={REFERENCE_MAX}
                  value={reference}
                  onChange={(event) => setReference(event.target.value)}
                  onBlur={() => setTouched(true)}
                />
              )}
            </Field>
          </div>
        </>
      )}
    </ActionDialog>
  );
}

/** The plan (and billing period) the next bill is for, at the price book's price. */
export function OverridePlanDialog({
  businessId,
  name,
  open,
  onClose,
  currentPlan,
  currentPeriod,
}: AccountActionDialogProps & { currentPlan: PlanKey; currentPeriod: BillingPeriod | null | undefined }) {
  const { t } = useI18n();
  const [plan, setPlan] = useState<PlanKey>(currentPlan);
  const [period, setPeriod] = useState<BillingPeriod>(currentPeriod ?? "monthly");
  const isChanged = plan !== currentPlan || period !== (currentPeriod ?? "monthly");
  const action = useAccountAction(
    businessId,
    (body: RequestBody<"/v1/admin/clients/{business_id}/plan", "post">) =>
      api.POST("/v1/admin/clients/{business_id}/plan", { params: { path: { business_id: businessId } }, body }),
    onClose,
  );

  return (
    <ActionDialog
      open={open}
      onClose={onClose}
      title={t("adminActions.plan.title", { name })}
      description={t("adminActions.plan.description")}
      confirmLabel={t("adminActions.plan.confirm")}
      fieldsValid={isChanged}
      isPending={action.isPending}
      error={action.error}
      onConfirm={(reason) => action.submit({ plan_key: plan, billing_period: period, reason })}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("adminActions.plan.plan")} required>
          {(control) => (
            <Select {...control} value={plan} onChange={(event) => setPlan(event.target.value as PlanKey)}>
              {PLANS.map((option) => (
                <option key={option} value={option}>
                  {t(PLAN_LABELS[option])}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("adminActions.plan.period")} required>
          {(control) => (
            <Select {...control} value={period} onChange={(event) => setPeriod(event.target.value as BillingPeriod)}>
              {PERIODS.map((option) => (
                <option key={option} value={option}>
                  {t(option === "annual" ? "billing.periodNames.annual" : "billing.periodNames.monthly")}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
    </ActionDialog>
  );
}
