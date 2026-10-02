"use client";

import { useState, type FormEvent } from "react";

import { useCountries } from "@/api/catalog";
import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { Button, Field, Input, Modal, Radio, Select } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { useI18n } from "@/i18n/client";
import { countryFlag } from "@/lib/countries";
import { cn } from "@/lib/cn";

import {
  buildInviteBody,
  ROLE_NAMES,
  type BusinessMember,
  type InviteBody,
  type InviteError,
  type InviteForm,
} from "../../_lib/team";

/** Inviting a member by phone or e-mail, as staff or an owner. */
export function InviteModal({
  open,
  onClose,
  onInvited,
}: {
  open: boolean;
  onClose: () => void;
  onInvited: (members: BusinessMember[], name: string) => void;
}) {
  const { t } = useI18n();
  return (
    <Modal open={open} onClose={onClose} title={t("settings.team.inviteTitle")} description={t("settings.team.inviteDescription")}>
      {open ? <InviteForm onClose={onClose} onInvited={onInvited} /> : null}
    </Modal>
  );
}

const INVITE_ERRORS: Record<InviteError, "settings.team.errors.required" | "settings.team.errors.email"> = {
  required: "settings.team.errors.required",
  email: "settings.team.errors.email",
};

function InviteForm({ onClose, onInvited }: { onClose: () => void; onInvited: (members: BusinessMember[], name: string) => void }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const countries = useCountries();
  const [form, setForm] = useState<InviteForm>({
    method: "phone",
    phone: "",
    countryHint: business.country_code,
    email: "",
    displayName: "",
    role: "staff",
  });
  const [errors, setErrors] = useState<Partial<Record<"phone" | "email", InviteError>>>({});
  const invite = useMutation(
    (body: InviteBody) => api.POST("/v1/businesses/{business_id}/members", { params: { path: { business_id: business.id } }, body }),
    { errorToast: false },
  );

  const update = (patch: Partial<InviteForm>) => {
    setForm((current) => ({ ...current, ...patch }));
    setErrors({});
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const built = buildInviteBody(form);
    if (!built.ok) {
      setErrors(built.errors);
      return;
    }
    const result = await invite.run(built.body);
    if (result.ok) {
      const name = form.displayName.trim() || (form.method === "phone" ? form.phone.trim() : form.email.trim());
      onInvited(result.data.members, name);
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-ink">{t("settings.team.method")}</legend>
        <div className="flex flex-wrap gap-4">
          <Radio
            id="invite-method-phone"
            name="invite-method"
            checked={form.method === "phone"}
            onChange={() => update({ method: "phone" })}
            label={t("settings.team.methodPhone")}
          />
          <Radio
            id="invite-method-email"
            name="invite-method"
            checked={form.method === "email"}
            onChange={() => update({ method: "email" })}
            label={t("settings.team.methodEmail")}
          />
        </div>
      </fieldset>

      {form.method === "phone" ? (
        <div className="grid gap-5 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <Field label={t("settings.team.country")}>
            {(control) => (
              <Select {...control} value={form.countryHint} onChange={(event) => update({ countryHint: event.target.value })}>
                {!countries.data ? <option value={form.countryHint}>{form.countryHint}</option> : null}
                {countries.data?.countries.map((country) => (
                  <option key={country.country_code} value={country.country_code}>
                    {`${countryFlag(country.country_code)} ${country.display_name} (+${country.calling_code})`}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field
            label={t("settings.team.phone")}
            hint={t("settings.team.phoneHint")}
            required
            error={errors.phone ? t(INVITE_ERRORS[errors.phone]) : undefined}
          >
            {(control) => (
              <Input
                {...control}
                type="tel"
                inputMode="tel"
                autoComplete="off"
                dir="ltr"
                value={form.phone}
                onChange={(event) => update({ phone: event.target.value })}
              />
            )}
          </Field>
        </div>
      ) : (
        <Field label={t("settings.team.email")} required error={errors.email ? t(INVITE_ERRORS[errors.email]) : undefined}>
          {(control) => (
            <Input
              {...control}
              type="email"
              inputMode="email"
              autoComplete="off"
              dir="ltr"
              value={form.email}
              onChange={(event) => update({ email: event.target.value })}
            />
          )}
        </Field>
      )}

      <Field label={t("settings.team.displayName")} optionalLabel={t("common.optional")}>
        {(control) => (
          <Input
            {...control}
            value={form.displayName}
            dir="auto"
            autoComplete="off"
            maxLength={100}
            placeholder={t("settings.team.displayNamePlaceholder")}
            onChange={(event) => update({ displayName: event.target.value })}
          />
        )}
      </Field>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-ink">{t("settings.team.role")}</legend>
        <div className="space-y-2">
          {(["staff", "owner"] as const).map((role) => (
            <Radio
              key={role}
              id={`invite-role-${role}`}
              name="invite-role"
              checked={form.role === role}
              onChange={() => update({ role })}
              className={cn(
                "rounded-xl border p-3 transition-colors",
                form.role === role ? "border-accent-solid bg-accent-soft/40" : "border-line hover:bg-surface-muted/60",
              )}
              label={<span className="font-medium">{t(ROLE_NAMES[role])}</span>}
              description={t(role === "owner" ? "settings.roles.ownerDescription" : "settings.team.roleStaff")}
            />
          ))}
        </div>
      </fieldset>

      <InlineError error={invite.error} overrides={{ conflict: "settings.team.errors.alreadyMember" }} />

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onClose} disabled={invite.isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={invite.isPending} loadingText={t("settings.team.sending")}>
          {t("settings.team.send")}
        </Button>
      </div>
    </form>
  );
}
