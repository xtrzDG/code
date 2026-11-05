"use client";

import { useId, useState, type FormEvent } from "react";

import { PAYMENT_LINK_KINDS, type DepositSettingsView, type PaymentLinkKind } from "@/components/deposits/depositModel";
import {
  EMPTY_PAYMENT_LINK,
  paymentLinkBody,
  paymentLinkErrors,
  type PaymentLinkForm,
} from "@/components/deposits/depositSettingsModel";
import { useDepositSettingsActions } from "@/components/deposits/useDeposits";
import { Button, Field, Fieldset, Input, Radio, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

const KIND_LABELS = {
  template: "deposits.pages.kinds.template",
  static: "deposits.pages.kinds.static",
} as const;
const KIND_HINTS = {
  template: "deposits.pages.kindHints.template",
  static: "deposits.pages.kindHints.static",
} as const;

/**
 * A new payment page: its name, whether it fills in the amount (a template
 * with {amount} and {reference}) or always charges one amount, and its
 * https address. A key in the address is kept encrypted by the API.
 */
export function PaymentPageForm({
  onAdded,
  onCancel,
}: {
  onAdded: (settings: DepositSettingsView) => void;
  onCancel?: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const formId = useId();
  const actions = useDepositSettingsActions();
  const [form, setForm] = useState<PaymentLinkForm>(EMPTY_PAYMENT_LINK);
  const [showErrors, setShowErrors] = useState(false);
  const errors = showErrors ? paymentLinkErrors(form) : {};
  const change = (patch: Partial<PaymentLinkForm>) => setForm((current) => ({ ...current, ...patch }));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setShowErrors(true);
    if (Object.keys(paymentLinkErrors(form)).length > 0) {
      return;
    }
    const result = await actions.addPage.run(paymentLinkBody(form));
    if (result.ok) {
      setForm(EMPTY_PAYMENT_LINK);
      setShowErrors(false);
      toast.success(t("deposits.pages.added"));
      onAdded(result.data);
    }
  };

  return (
    <form id={formId} onSubmit={(event) => void submit(event)} noValidate className="space-y-4 rounded-xl bg-surface-muted p-4">
      <Field label={t("deposits.pages.label")} error={errors.label && t(errors.label)}>
        {(control) => (
          <Input
            {...control}
            autoComplete="off"
            maxLength={80}
            placeholder={t("deposits.pages.labelPlaceholder")}
            value={form.label}
            onChange={(event) => change({ label: event.target.value })}
          />
        )}
      </Field>
      <Fieldset legend={t("deposits.pages.kind")}>
        <div className="space-y-2">
          {PAYMENT_LINK_KINDS.map((kind: PaymentLinkKind) => (
            <Radio
              key={kind}
              name={`${formId}-kind`}
              value={kind}
              checked={form.kind === kind}
              onChange={() => change({ kind })}
              label={t(KIND_LABELS[kind])}
              description={t(KIND_HINTS[kind])}
            />
          ))}
        </div>
      </Fieldset>
      <Field label={t("deposits.pages.address")} hint={t("deposits.pages.addressHint")} error={errors.address && t(errors.address)}>
        {(control) => (
          <Input
            {...control}
            type="url"
            dir="ltr"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            placeholder={form.kind === "template" ? "https://pay.example.com/?amount={amount}&ref={reference}" : "https://buy.stripe.com/…"}
            value={form.address}
            onChange={(event) => change({ address: event.target.value })}
          />
        )}
      </Field>
      <div className="flex flex-wrap justify-end gap-2">
        {onCancel ? (
          <Button variant="secondary" size="sm" onClick={onCancel} disabled={actions.addPage.isPending}>
            {t("common.cancel")}
          </Button>
        ) : null}
        <Button type="submit" size="sm" isLoading={actions.addPage.isPending} loadingText={t("common.saving")}>
          {t("deposits.pages.add")}
        </Button>
      </div>
    </form>
  );
}
