"use client";

/** "Add a person": how they sign in (phone or e-mail) and their role. */

import { useState } from "react";

import type { PlatformAdminRole } from "@/api/types";
import { ConfirmDialog, Field, Fieldset, Input, Radio, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { ADMIN_ROLES, ROLE_HINTS, ROLE_LABELS, type AddAdminBy } from "../../_lib/team";

export function AddAdminDialog({
  open,
  isPending,
  error,
  onClose,
  onAdd,
}: {
  open: boolean;
  isPending: boolean;
  error: unknown;
  onClose: () => void;
  onAdd: (by: AddAdminBy, value: string, role: PlatformAdminRole) => void | Promise<void>;
}) {
  const { t } = useI18n();
  const [by, setBy] = useState<AddAdminBy>("email");
  const [value, setValue] = useState("");
  const [role, setRole] = useState<PlatformAdminRole>("support_readonly");
  const [wasOpen, setWasOpen] = useState(open);
  if (wasOpen !== open) {
    setWasOpen(open);
    if (open) {
      setValue("");
    }
  }

  return (
    <ConfirmDialog
      open={open}
      onClose={onClose}
      onConfirm={() => onAdd(by, value, role)}
      tone="primary"
      isPending={isPending}
      confirmDisabled={value.trim() === ""}
      error={error}
      title={t("adminTeam.addTitle")}
      description={t("adminTeam.addDescription")}
      confirmLabel={t("adminTeam.add")}
    >
      <div className="space-y-4">
        <Fieldset legend={t("adminTeam.by")}>
          <div className="flex flex-wrap gap-4">
            {(["email", "phone"] as const).map((option) => (
              <Radio
                key={option}
                name="admin-by"
                value={option}
                checked={by === option}
                onChange={() => setBy(option)}
                label={option === "email" ? t("adminTeam.byEmail") : t("adminTeam.byPhone")}
              />
            ))}
          </div>
        </Fieldset>
        <Field label={by === "email" ? t("adminTeam.email") : t("adminTeam.phone")} required>
          {(control) => (
            <Input
              {...control}
              type={by === "email" ? "email" : "tel"}
              inputMode={by === "email" ? "email" : "tel"}
              autoComplete="off"
              dir="ltr"
              placeholder={by === "email" ? "name@example.com" : "+995 555 12 34 56"}
              value={value}
              onChange={(event) => setValue(event.target.value)}
            />
          )}
        </Field>
        <Field label={t("adminTeam.role")} hint={t(ROLE_HINTS[role])}>
          {(control) => (
            <Select {...control} value={role} onChange={(event) => setRole(event.target.value as PlatformAdminRole)}>
              {ADMIN_ROLES.map((option) => (
                <option key={option} value={option}>
                  {t(ROLE_LABELS[option])}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
    </ConfirmDialog>
  );
}
