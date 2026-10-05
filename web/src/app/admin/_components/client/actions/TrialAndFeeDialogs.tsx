"use client";

import { useState } from "react";

import { api } from "@/api/client";
import type { RequestBody } from "@/api/types";
import { Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { parseTrialDays, TRIAL_DAYS_MAX } from "../../../_lib/accountActions";
import { ActionDialog, useAccountAction, type AccountActionDialogProps } from "./ActionDialog";

const DEFAULT_TRIAL_DAYS = "14";

/** More days of the free trial (a trial that ended unpaid starts again from today). */
export function ExtendTrialDialog({ businessId, name, open, onClose }: AccountActionDialogProps) {
  const { t } = useI18n();
  const [days, setDays] = useState(DEFAULT_TRIAL_DAYS);
  const [isTouched, setTouched] = useState(false);
  const parsed = parseTrialDays(days);
  const action = useAccountAction(
    businessId,
    (body: RequestBody<"/v1/admin/clients/{business_id}/trial-extension", "post">) =>
      api.POST("/v1/admin/clients/{business_id}/trial-extension", { params: { path: { business_id: businessId } }, body }),
    onClose,
  );

  return (
    <ActionDialog
      open={open}
      onClose={onClose}
      title={t("adminActions.extend.title", { name })}
      description={t("adminActions.extend.description")}
      confirmLabel={t("adminActions.extend.confirm")}
      fieldsValid={parsed !== null}
      isPending={action.isPending}
      error={action.error}
      onConfirm={(reason) => (parsed === null ? undefined : action.submit({ days: parsed, reason }))}
    >
      <Field
        label={t("adminActions.extend.days")}
        hint={t("adminActions.extend.daysHint")}
        error={isTouched && parsed === null ? t("adminActions.extend.daysInvalid") : undefined}
        required
      >
        {(control) => (
          <Input
            {...control}
            type="number"
            inputMode="numeric"
            min={1}
            max={TRIAL_DAYS_MAX}
            step={1}
            value={days}
            onChange={(event) => setDays(event.target.value)}
            onBlur={() => setTouched(true)}
          />
        )}
      </Field>
    </ActionDialog>
  );
}

/** The setup fee waived: its unpaid bill voided, never billed again. */
export function WaiveSetupFeeDialog({ businessId, name, open, onClose }: AccountActionDialogProps) {
  const { t } = useI18n();
  const action = useAccountAction(
    businessId,
    (body: RequestBody<"/v1/admin/clients/{business_id}/setup-fee-waiver", "post">) =>
      api.POST("/v1/admin/clients/{business_id}/setup-fee-waiver", { params: { path: { business_id: businessId } }, body }),
    onClose,
  );

  return (
    <ActionDialog
      open={open}
      onClose={onClose}
      title={t("adminActions.waive.title", { name })}
      description={t("adminActions.waive.description")}
      confirmLabel={t("adminActions.waive.confirm")}
      isPending={action.isPending}
      error={action.error}
      onConfirm={(reason) => action.submit({ reason })}
    />
  );
}
