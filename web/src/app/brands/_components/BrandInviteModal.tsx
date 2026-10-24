"use client";

import { useState, type FormEvent } from "react";

import { useCountries } from "@/api/catalog";
import { Button, Field, Input, Modal, ModalFooter, Radio, Select, useToast } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { useI18n } from "@/i18n/client";
import { countryFlag } from "@/lib/countries";

import { buildBrandInvite, type BrandLocationView, type InviteForm, type InviteProblem } from "../_lib/brands";
import { useBrandTeam } from "../_lib/useBrands";
import { RoleFields } from "./RoleFields";

const PROBLEMS: Record<InviteProblem, "brands.team.errors.required" | "settings.team.errors.email" | "brands.team.errors.locations"> = {
  required: "brands.team.errors.required",
  email: "settings.team.errors.email",
  locations: "brands.team.errors.locations",
};

/** Inviting a brand owner or a regional manager by phone (any country) or e-mail. */
export function BrandInviteModal({
  open,
  onClose,
  brandId,
  locations,
}: {
  open: boolean;
  onClose: () => void;
  brandId: string;
  locations: readonly BrandLocationView[];
}) {
  const { t } = useI18n();
  return (
    <Modal open={open} onClose={onClose} title={t("brands.team.inviteTitle")} description={t("brands.team.inviteDescription")}>
      {open ? <InviteFormBody onClose={onClose} brandId={brandId} locations={locations} /> : null}
    </Modal>
  );
}

function InviteFormBody({ onClose, brandId, locations }: { onClose: () => void; brandId: string; locations: readonly BrandLocationView[] }) {
  const { t } = useI18n();
  const toast = useToast();
  const countries = useCountries();
  const { invite } = useBrandTeam(brandId);
  const [form, setForm] = useState<InviteForm>({
    method: "phone",
    phone: "",
    countryHint: locations[0]?.country_code ?? "GE",
    email: "",
    displayName: "",
    role: "regional_manager",
    businessIds: [],
  });
  const [problems, setProblems] = useState<Partial<Record<"contact" | "locations", InviteProblem>>>({});
  const update = (patch: Partial<InviteForm>) => {
    setForm((current) => ({ ...current, ...patch }));
    setProblems({});
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const built = buildBrandInvite(form);
    if (!built.ok) {
      setProblems(built.problems);
      return;
    }
    const result = await invite.run(built.body);
    if (result.ok) {
      const name = form.displayName.trim() || (form.method === "phone" ? form.phone.trim() : form.email.trim());
      toast.success({ text: t("brands.team.invited"), values: { name } });
      onClose();
    }
  };

  const contactError = problems.contact ? t(PROBLEMS[problems.contact]) : undefined;
  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-ink">{t("brands.team.method")}</legend>
        <div className="flex flex-wrap gap-4">
          <Radio id="brand-invite-phone" name="brand-invite-method" checked={form.method === "phone"} onChange={() => update({ method: "phone" })} label={t("brands.team.methodPhone")} />
          <Radio id="brand-invite-email" name="brand-invite-method" checked={form.method === "email"} onChange={() => update({ method: "email" })} label={t("brands.team.methodEmail")} />
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
          <Field label={t("brands.team.phone")} required error={contactError}>
            {(control) => (
              <Input {...control} type="tel" inputMode="tel" autoComplete="off" dir="ltr" value={form.phone} onChange={(event) => update({ phone: event.target.value })} />
            )}
          </Field>
        </div>
      ) : (
        <Field label={t("brands.team.email")} required error={contactError}>
          {(control) => (
            <Input {...control} type="email" inputMode="email" autoComplete="off" dir="ltr" value={form.email} onChange={(event) => update({ email: event.target.value })} />
          )}
        </Field>
      )}
      <Field label={t("brands.team.displayName")} optionalLabel={t("common.optional")}>
        {(control) => (
          <Input {...control} value={form.displayName} dir="auto" autoComplete="off" maxLength={100} onChange={(event) => update({ displayName: event.target.value })} />
        )}
      </Field>
      <RoleFields
        idPrefix="brand-invite"
        role={form.role}
        businessIds={form.businessIds}
        locations={locations}
        locationsError={problems.locations ? t(PROBLEMS[problems.locations]) : undefined}
        onChange={(change) => update(change)}
      />
      <InlineError error={invite.error} overrides={{ conflict: "brands.team.errors.alreadyMember" }} />
      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={invite.isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={invite.isPending}>
          {t("brands.team.send")}
        </Button>
      </ModalFooter>
    </form>
  );
}
