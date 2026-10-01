"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { useCountries } from "@/api/catalog";
import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { useApiMutation } from "@/api/hooks";
import { MemberRoleBadge } from "@/components/business/BusinessStatusBadge";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconPlus } from "@/components/icons";
import { Badge, Button, Card, Field, Input, Modal, Radio, Select, useToast } from "@/components/ui";
import { ConfirmDialog } from "@/components/workspace/ConfirmDialog";
import { InlineError } from "@/components/workspace/InlineError";
import { IconUsers } from "@/components/workspace/icons";
import { DANGER_GHOST } from "@/components/workspace/styles";
import { useI18n } from "@/i18n/client";
import { countryFlag } from "@/lib/countries";
import { HOME_PATH } from "@/lib/navigation";

import {
  buildInviteBody,
  canRemoveMember,
  memberInitials,
  memberLabel,
  sortMembers,
  type BusinessMember,
  type InviteBody,
  type InviteError,
  type InviteForm,
} from "../_lib/settings";

/** Team members with roles; the owner invites staff by phone or e-mail and removes members. */
export function TeamTab() {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business, me, isOwner } = useBusiness();
  const [members, setMembers] = useState<BusinessMember[]>(business.members);
  const [isInviting, setInviting] = useState(false);
  const [removing, setRemoving] = useState<BusinessMember | null>(null);
  const [removeError, setRemoveError] = useState<ApiError | null>(null);

  const remove = useApiMutation(
    (userId: string) =>
      api.DELETE("/v1/businesses/{business_id}/members/{user_id}", {
        params: { path: { business_id: business.id, user_id: userId } },
      }),
    { errorToast: false },
  );

  const onRemove = async () => {
    if (!removing) {
      return;
    }
    const result = await remove.run(removing.user_id);
    if (!result.ok) {
      setRemoveError(result.error);
      return;
    }
    toast.success(t("settings.team.removed", { name: memberLabel(removing) }));
    setRemoving(null);
    if (removing.user_id === me.user.id) {
      router.replace(HOME_PATH);
      return;
    }
    setMembers(result.data.members);
    router.refresh();
  };

  const sorted = sortMembers(members);

  return (
    <Card
      title={t("settings.team.title")}
      description={t("settings.team.description")}
      padded={false}
      actions={
        isOwner ? (
          <Button size="sm" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setInviting(true)}>
            {t("settings.team.invite")}
          </Button>
        ) : undefined
      }
    >
      <ul className="divide-y divide-line">
        {sorted.map((member) => {
          const name = memberLabel(member);
          const isMe = member.user_id === me.user.id;
          const contacts = [member.phone_number, member.email].filter((value): value is string => Boolean(value) && value !== name);
          const removable = canRemoveMember(member, members);
          return (
            <li key={member.user_id} className="flex flex-wrap items-center gap-x-4 gap-y-3 px-5 py-4 sm:px-6">
              <span
                className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent-ink"
                aria-hidden
              >
                {memberInitials(member) ?? <IconUsers className="size-5" />}
              </span>
              <div className="min-w-0 flex-1 basis-40">
                <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
                  <span dir="auto" className="break-all">
                    {name}
                  </span>
                  {isMe ? <Badge tone="info">{t("settings.team.you")}</Badge> : null}
                </p>
                {contacts.length > 0 ? (
                  <p className="mt-0.5 truncate text-sm text-ink-muted" dir="ltr">
                    {contacts.join(" · ")}
                  </p>
                ) : null}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {!member.is_verified ? <Badge tone="warning">{t("settings.team.notSignedIn")}</Badge> : null}
                <MemberRoleBadge role={member.role} />
                {isOwner ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    className={DANGER_GHOST}
                    disabled={!removable}
                    title={!removable ? t("settings.team.lastOwner") : undefined}
                    aria-label={t("settings.team.removeLabel", { name })}
                    onClick={() => {
                      setRemoveError(null);
                      setRemoving(member);
                    }}
                  >
                    {t("settings.team.remove")}
                  </Button>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>

      <InviteModal
        open={isInviting}
        onClose={() => setInviting(false)}
        onInvited={(updated, name) => {
          setMembers(updated);
          setInviting(false);
          router.refresh();
          toast.success(t("settings.team.invited", { name }));
        }}
      />

      <ConfirmDialog
        open={removing !== null}
        onClose={() => setRemoving(null)}
        onConfirm={onRemove}
        isPending={remove.isPending}
        error={removeError}
        title={removing ? t("settings.team.removeTitle", { name: memberLabel(removing) }) : ""}
        confirmLabel={t("settings.team.remove")}
      >
        {removing ? (
          <p>{removing.user_id === me.user.id ? t("settings.team.removeSelfDescription") : t("settings.team.removeDescription")}</p>
        ) : null}
      </ConfirmDialog>
    </Card>
  );
}

function InviteModal({
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
  });
  const [errors, setErrors] = useState<Partial<Record<"phone" | "email", InviteError>>>({});
  const invite = useApiMutation(
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

      <div className="rounded-xl bg-surface-muted/70 p-3 text-sm">
        <p className="font-medium text-ink">{t("settings.team.role")}</p>
        <p className="mt-0.5 text-ink-muted">{t("settings.team.roleStaff")}</p>
      </div>

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
