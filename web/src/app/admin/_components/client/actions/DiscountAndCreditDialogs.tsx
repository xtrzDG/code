"use client";

import { useState } from "react";

import { api } from "@/api/client";
import type { RequestBody } from "@/api/types";
import { Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { todayInTimeZone } from "@/lib/specialDays";

import {
  isDiscountDayValid,
  lastDiscountDay,
  parseCreditMinor,
  parseDiscountPercent,
} from "../../../_lib/accountActions";
import { ActionDialog, useAccountAction, type AccountActionDialogProps } from "./ActionDialog";

/**
 * A percent off every period that starts on or before the last day (in the
 * client's time zone); a new discount replaces the current one.
 */
export function DiscountDialog({
  businessId,
  name,
  open,
  onClose,
  timeZone,
  autoDebitNote,
}: AccountActionDialogProps & { timeZone: string; autoDebitNote?: string }) {
  const { t } = useI18n();
  const [today] = useState(() => todayInTimeZone(new Date(), timeZone));
  const [percent, setPercent] = useState("");
  const [lastDay, setLastDay] = useState("");
  const [touched, setTouched] = useState({ percent: false, lastDay: false });
  const parsedPercent = parseDiscountPercent(percent);
  const isDayValid = isDiscountDayValid(lastDay, today);
  const action = useAccountAction(
    businessId,
    (body: RequestBody<"/v1/admin/clients/{business_id}/discount", "post">) =>
      api.POST("/v1/admin/clients/{business_id}/discount", { params: { path: { business_id: businessId } }, body }),
    onClose,
  );

  return (
    <ActionDialog
      open={open}
      onClose={onClose}
      title={t("adminActions.discount.title", { name })}
      description={t("adminActions.discount.description")}
      confirmLabel={t("adminActions.discount.confirm")}
      fieldsValid={parsedPercent !== null && isDayValid}
      isPending={action.isPending}
      error={action.error}
      note={autoDebitNote}
      onConfirm={(reason) =>
        parsedPercent === null ? undefined : action.submit({ percent: parsedPercent, last_day: lastDay, reason })
      }
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label={t("adminActions.discount.percent")}
          error={touched.percent && parsedPercent === null ? t("adminActions.discount.percentInvalid") : undefined}
          required
        >
          {(control) => (
            <Input
              {...control}
              type="number"
              inputMode="numeric"
              min={1}
              max={100}
              step={1}
              value={percent}
              onChange={(event) => setPercent(event.target.value)}
              onBlur={() => setTouched((current) => ({ ...current, percent: true }))}
            />
          )}
        </Field>
        <Field
          label={t("adminActions.discount.lastDay")}
          hint={t("adminActions.discount.lastDayHint")}
          error={touched.lastDay && !isDayValid ? t("adminActions.discount.lastDayInvalid") : undefined}
          required
        >
          {(control) => (
            <Input
              {...control}
              type="date"
              min={today}
              max={lastDiscountDay(today)}
              value={lastDay}
              onChange={(event) => setLastDay(event.target.value)}
              onBlur={() => setTouched((current) => ({ ...current, lastDay: true }))}
            />
          )}
        </Field>
      </div>
    </ActionDialog>
  );
}

/** Credit in the subscription's currency, off the next bills before tax until spent. */
export function CreditDialog({
  businessId,
  name,
  open,
  onClose,
  currency,
  autoDebitNote,
}: AccountActionDialogProps & { currency: string; autoDebitNote?: string }) {
  const { t } = useI18n();
  const [amount, setAmount] = useState("");
  const [isTouched, setTouched] = useState(false);
  const minor = parseCreditMinor(amount, currency);
  const action = useAccountAction(
    businessId,
    (body: RequestBody<"/v1/admin/clients/{business_id}/credits", "post">) =>
      api.POST("/v1/admin/clients/{business_id}/credits", { params: { path: { business_id: businessId } }, body }),
    onClose,
  );

  return (
    <ActionDialog
      open={open}
      onClose={onClose}
      title={t("adminActions.credit.title", { name })}
      description={t("adminActions.credit.description")}
      confirmLabel={t("adminActions.credit.confirm")}
      fieldsValid={minor !== null}
      isPending={action.isPending}
      error={action.error}
      note={autoDebitNote}
      onConfirm={(reason) => (minor === null ? undefined : action.submit({ amount_minor: minor, reason }))}
    >
      <Field
        label={t("adminActions.credit.amount", { currency })}
        error={isTouched && minor === null ? t("adminActions.credit.amountInvalid") : undefined}
        required
      >
        {(control) => (
          <Input
            {...control}
            inputMode="decimal"
            autoComplete="off"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            onBlur={() => setTouched(true)}
          />
        )}
      </Field>
    </ActionDialog>
  );
}
