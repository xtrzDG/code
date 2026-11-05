"use client";

/** The dialogs of /admin/partners: add a partner, change a rate, add a code. */

import { useState } from "react";

import type { RequestBody } from "@/api/types";
import { ConfirmDialog, Field, Fieldset, Input, Radio } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { basisPointsToPercent, percentToBasisPoints } from "@/lib/referrals/referralLinks";

import { createPartnerBody, isReferralCode, partnerFormProblem, type PartnerForm } from "../_lib/partnerForms";

const EMPTY: PartnerForm = { name: "", by: "phone", contact: "", ratePercent: "20", code: "" };

interface DialogProps {
  open: boolean;
  isPending: boolean;
  error: unknown;
  onClose: () => void;
}

export function AddPartnerDialog({
  onAdd,
  ...dialog
}: DialogProps & { onAdd: (body: RequestBody<"/v1/admin/partners", "post">) => void | Promise<void> }) {
  const { t } = useI18n();
  const [form, setForm] = useState<PartnerForm>(EMPTY);
  const [wasOpen, setWasOpen] = useState(dialog.open);
  const [isChecked, setChecked] = useState(false);
  if (wasOpen !== dialog.open) {
    setWasOpen(dialog.open);
    if (dialog.open) {
      setForm(EMPTY);
      setChecked(false);
    }
  }
  const problem = partnerFormProblem(form);
  const update = (change: Partial<PartnerForm>) => setForm((current) => ({ ...current, ...change }));
  const shownProblem = isChecked ? problem : null;

  return (
    <ConfirmDialog
      {...dialog}
      onConfirm={() => {
        setChecked(true);
        return problem === null ? onAdd(createPartnerBody(form)) : undefined;
      }}
      tone="primary"
      title={t("adminPartners.form.addTitle")}
      description={t("adminPartners.legal")}
      confirmLabel={t("adminPartners.add")}
    >
      <div className="space-y-4">
        <Field label={t("adminPartners.form.name")} required error={shownProblem === "nameRequired" ? t("adminPartners.form.nameRequired") : undefined}>
          {(control) => <Input {...control} value={form.name} autoComplete="off" onChange={(event) => update({ name: event.target.value })} />}
        </Field>
        <Fieldset legend={t("adminPartners.form.signsInWith")}>
          <div className="flex flex-wrap gap-4">
            {(["phone", "email"] as const).map((option) => (
              <Radio
                key={option}
                name="partner-by"
                value={option}
                checked={form.by === option}
                onChange={() => update({ by: option, contact: "" })}
                label={t(`adminPartners.form.${option}`)}
              />
            ))}
          </div>
        </Fieldset>
        <Field
          label={t(`adminPartners.form.${form.by}`)}
          required
          error={shownProblem === "contactRequired" ? t("adminPartners.form.contactRequired") : undefined}
        >
          {(control) => (
            <Input
              {...control}
              type={form.by === "email" ? "email" : "tel"}
              inputMode={form.by === "email" ? "email" : "tel"}
              autoComplete="off"
              dir="ltr"
              placeholder={form.by === "email" ? "name@example.com" : "+995 555 12 34 56"}
              value={form.contact}
              onChange={(event) => update({ contact: event.target.value })}
            />
          )}
        </Field>
        <Field
          label={t("adminPartners.form.rate")}
          hint={t("adminPartners.form.rateHint")}
          error={shownProblem === "rateInvalid" ? t("adminPartners.form.rateInvalid") : undefined}
        >
          {(control) => (
            <Input {...control} inputMode="decimal" className="max-w-32" value={form.ratePercent} onChange={(event) => update({ ratePercent: event.target.value })} />
          )}
        </Field>
        <Field
          label={t("adminPartners.form.code")}
          hint={t("adminPartners.form.codeHint")}
          required
          error={shownProblem === "codeInvalid" ? t("adminPartners.form.codeInvalid") : undefined}
        >
          {(control) => (
            <Input {...control} dir="ltr" autoComplete="off" spellCheck={false} value={form.code} onChange={(event) => update({ code: event.target.value })} />
          )}
        </Field>
      </div>
    </ConfirmDialog>
  );
}

export function RateDialog({
  name,
  basisPoints,
  onSave,
  ...dialog
}: DialogProps & { name: string; basisPoints: number; onSave: (basisPoints: number) => void | Promise<void> }) {
  const { t } = useI18n();
  const [value, setValue] = useState(String(basisPointsToPercent(basisPoints)));
  const [wasOpen, setWasOpen] = useState(dialog.open);
  if (wasOpen !== dialog.open) {
    setWasOpen(dialog.open);
    if (dialog.open) {
      setValue(String(basisPointsToPercent(basisPoints)));
    }
  }
  const parsed = percentToBasisPoints(value);
  return (
    <ConfirmDialog
      {...dialog}
      onConfirm={() => (parsed === null ? undefined : onSave(parsed))}
      tone="primary"
      confirmDisabled={parsed === null}
      title={t("adminPartners.form.rateTitle", { name })}
      confirmLabel={t("adminPartners.form.save")}
    >
      <Field label={t("adminPartners.form.rate")} hint={t("adminPartners.form.rateHint")} error={parsed === null ? t("adminPartners.form.rateInvalid") : undefined}>
        {(control) => <Input {...control} inputMode="decimal" className="max-w-32" value={value} onChange={(event) => setValue(event.target.value)} />}
      </Field>
    </ConfirmDialog>
  );
}

export function CodeDialog({
  name,
  onAdd,
  ...dialog
}: DialogProps & { name: string; onAdd: (code: string) => void | Promise<void> }) {
  const { t } = useI18n();
  const [code, setCode] = useState("");
  const [wasOpen, setWasOpen] = useState(dialog.open);
  if (wasOpen !== dialog.open) {
    setWasOpen(dialog.open);
    if (dialog.open) {
      setCode("");
    }
  }
  const isValid = isReferralCode(code);
  return (
    <ConfirmDialog
      {...dialog}
      onConfirm={() => (isValid ? onAdd(code.trim()) : undefined)}
      tone="primary"
      confirmDisabled={!isValid}
      errorOverrides={{ conflict: "adminPartners.form.codeTaken" }}
      title={t("adminPartners.form.codeTitle", { name })}
      confirmLabel={t("adminPartners.addCode")}
    >
      <Field
        label={t("adminPartners.form.code")}
        hint={t("adminPartners.form.codeHint")}
        error={code.trim() !== "" && !isValid ? t("adminPartners.form.codeInvalid") : undefined}
      >
        {(control) => <Input {...control} dir="ltr" autoComplete="off" spellCheck={false} value={code} onChange={(event) => setCode(event.target.value)} />}
      </Field>
    </ConfirmDialog>
  );
}
