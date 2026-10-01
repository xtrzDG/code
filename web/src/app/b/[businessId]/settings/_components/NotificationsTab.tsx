"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconPlus } from "@/components/icons";
import { Badge, Button, ButtonLink, Card, EmptyState, Field, Input, Modal, Select, useToast } from "@/components/ui";
import { ConfirmDialog } from "@/components/workspace/ConfirmDialog";
import { IconBell } from "@/components/workspace/icons";
import { InlineError } from "@/components/workspace/InlineError";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import {
  MAX_MANAGER_CONTACTS,
  MAX_MANAGER_NAME_LENGTH,
  applyContactChange,
  contactFromForm,
  contactKey,
  languageChoices,
  validateContact,
  type ContactChange,
  type ContactError,
  type ContactField,
  type ContactForm,
  type ManagerContact,
  type ManagerContactChannel,
  type ManagerContactInput,
} from "../_lib/settings";

const CHANNELS: readonly ManagerContactChannel[] = ["telegram", "whatsapp", "email", "sms"];

const CHANNEL_LABELS: Record<ManagerContactChannel, MessageKey> = {
  telegram: "settings.contacts.channels.telegram",
  whatsapp: "settings.contacts.channels.whatsapp",
  email: "settings.contacts.channels.email",
  sms: "settings.contacts.channels.sms",
};

const ADDRESS_LABELS: Record<ManagerContactChannel, MessageKey> = {
  telegram: "settings.contacts.address.telegram",
  whatsapp: "settings.contacts.address.whatsapp",
  email: "settings.contacts.address.email",
  sms: "settings.contacts.address.sms",
};

const ADDRESS_HINTS: Record<ManagerContactChannel, MessageKey> = {
  telegram: "settings.contacts.addressHint.telegram",
  whatsapp: "settings.contacts.addressHint.whatsapp",
  email: "settings.contacts.addressHint.email",
  sms: "settings.contacts.addressHint.sms",
};

const CONTACT_ERRORS: Record<ContactError, MessageKey> = {
  required: "settings.contacts.errors.required",
  tooLong: "settings.contacts.errors.tooLong",
  email: "settings.contacts.errors.email",
  chatId: "settings.contacts.errors.chatId",
  duplicate: "settings.contacts.errors.duplicate",
};

type Editing = { index: number | null } | null;

/**
 * Staff who receive handoffs, bookings and leads. The API saves the whole
 * list at once, and the platform bot adds Telegram contacts meanwhile, so
 * the tab loads the list fresh and applies each change to a fresh copy.
 */
export function NotificationsTab() {
  const { t, locale } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business, isOwner } = useBusiness();
  const stored = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } } }),
    [business.id],
  );
  const [saved, setSaved] = useState<ManagerContact[] | null>(null);
  const contacts: ManagerContact[] = saved ?? stored.data?.manager_contacts ?? business.manager_contacts ?? [];
  const [editing, setEditing] = useState<Editing>(null);
  const [removing, setRemoving] = useState<number | null>(null);
  const [dialogError, setDialogError] = useState<ApiError | null>(null);

  const save = useApiMutation(
    async (change: ContactChange) => {
      const fresh = await api.GET("/v1/businesses/{business_id}", {
        params: { path: { business_id: business.id } },
      });
      if (!fresh.data) {
        return fresh;
      }
      return api.PATCH("/v1/businesses/{business_id}", {
        params: { path: { business_id: business.id } },
        body: { manager_contacts: applyContactChange(fresh.data.manager_contacts ?? [], change) },
      });
    },
    { errorToast: false },
  );

  const persist = async (change: ContactChange): Promise<boolean> => {
    setDialogError(null);
    const result = await save.run(change);
    if (!result.ok) {
      setDialogError(result.error);
      return false;
    }
    setSaved(result.data.manager_contacts ?? []);
    router.refresh();
    toast.success(t("settings.contacts.saved"));
    return true;
  };

  const onSaveContact = async (contact: ManagerContactInput) => {
    if (!editing) {
      return;
    }
    const original = editing.index === null ? undefined : contacts[editing.index];
    const change: ContactChange = original
      ? { kind: "edit", original: contactKey(original), contact }
      : { kind: "add", contact };
    if (await persist(change)) {
      setEditing(null);
    }
  };

  const onRemove = async () => {
    const original = removing === null ? undefined : contacts[removing];
    if (!original) {
      return;
    }
    if (await persist({ kind: "remove", original: contactKey(original) })) {
      setRemoving(null);
    }
  };

  const removingContact = removing !== null ? contacts[removing] : undefined;
  const isFull = contacts.length >= MAX_MANAGER_CONTACTS;

  return (
    <div className="space-y-6">
      <Card
        title={t("settings.contacts.title")}
        description={t("settings.contacts.description")}
        padded={contacts.length === 0}
        actions={
          isOwner ? (
            <Button
              size="sm"
              leadingIcon={<IconPlus className="size-4" aria-hidden />}
              disabled={isFull}
              title={isFull ? t("settings.contacts.limit", { count: MAX_MANAGER_CONTACTS }) : undefined}
              onClick={() => {
                setDialogError(null);
                setEditing({ index: null });
              }}
            >
              {t("settings.contacts.add")}
            </Button>
          ) : undefined
        }
      >
        {contacts.length === 0 ? (
          <EmptyState
            className="py-6"
            icon={<IconBell className="size-6" />}
            title={t("settings.contacts.empty")}
            description={t("settings.contacts.emptyDescription")}
          />
        ) : (
          <ul className="divide-y divide-line">
            {contacts.map((contact, index) => (
              <li key={`${contact.channel}-${contact.address}`} className="flex items-start gap-3 px-5 py-4 sm:px-6">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-ink" dir="auto">
                    {contact.name}
                  </p>
                  <p className="mt-0.5 truncate text-sm text-ink-muted" dir="ltr">
                    {contact.address}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge tone="accent">{t(CHANNEL_LABELS[contact.channel])}</Badge>
                    <Badge>{languageName(contact.language, locale)}</Badge>
                  </div>
                </div>
                {isOwner ? (
                  <div className="flex shrink-0 flex-col items-end gap-1 sm:flex-row">
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={t("settings.contacts.editLabel", { name: contact.name })}
                      onClick={() => {
                        setDialogError(null);
                        setEditing({ index });
                      }}
                    >
                      {t("settings.contacts.edit")}
                    </Button>
                    <Button
                      variant="danger-ghost"
                      size="sm"
                      aria-label={t("settings.contacts.removeLabel", { name: contact.name })}
                      onClick={() => {
                        setDialogError(null);
                        setRemoving(index);
                      }}
                    >
                      {t("settings.contacts.remove")}
                    </Button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-ink-muted">{t("settings.contacts.telegramLinkHint")}</p>
          <ButtonLink href={businessPath(business.id, "channels")} variant="secondary" size="sm">
            {t("settings.contacts.openChannels")}
          </ButtonLink>
        </div>
      </Card>

      <Modal
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={editing?.index === null ? t("settings.contacts.addTitle") : t("settings.contacts.editTitle")}
      >
        {editing ? (
          <ContactFormView
            key={editing.index ?? "new"}
            initial={editing.index === null ? undefined : contacts[editing.index]}
            others={contacts.filter((_, index) => index !== editing.index)}
            languages={languageChoices([business.owner_language], business.languages, ["ka", "ru", "en"])}
            isPending={save.isPending}
            error={dialogError}
            onCancel={() => setEditing(null)}
            onSubmit={onSaveContact}
          />
        ) : null}
      </Modal>

      <ConfirmDialog
        open={removing !== null}
        onClose={() => setRemoving(null)}
        onConfirm={onRemove}
        isPending={save.isPending}
        error={dialogError}
        title={removingContact ? t("settings.contacts.removeTitle", { name: removingContact.name }) : ""}
        confirmLabel={t("settings.contacts.remove")}
      >
        {removingContact ? <p>{t("settings.contacts.removeDescription", { name: removingContact.name })}</p> : null}
      </ConfirmDialog>
    </div>
  );
}

function ContactFormView({
  initial,
  others,
  languages,
  isPending,
  error,
  onCancel,
  onSubmit,
}: {
  initial: ManagerContact | undefined;
  others: readonly ManagerContact[];
  languages: readonly string[];
  isPending: boolean;
  error: ApiError | null;
  onCancel: () => void;
  onSubmit: (contact: ManagerContactInput) => void;
}) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const [form, setForm] = useState<ContactForm>({
    name: initial?.name ?? "",
    channel: initial?.channel ?? "email",
    address: initial?.address ?? "",
    language: initial?.language ?? business.owner_language,
  });
  const [errors, setErrors] = useState<Partial<Record<ContactField, ContactError>>>({});
  const languageOptions = languageChoices(languages, [form.language]);

  const update = (patch: Partial<ContactForm>) => {
    setForm((current) => ({ ...current, ...patch }));
    setErrors({});
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const found = validateContact(form, others);
    setErrors(found);
    if (Object.keys(found).length === 0) {
      onSubmit(contactFromForm(form));
    }
  };

  return (
    <form onSubmit={submit} noValidate className="space-y-5">
      <Field label={t("settings.contacts.name")} required error={errors.name ? t(CONTACT_ERRORS[errors.name]) : undefined}>
        {(control) => (
          <Input
            {...control}
            value={form.name}
            dir="auto"
            maxLength={MAX_MANAGER_NAME_LENGTH}
            autoComplete="off"
            onChange={(event) => update({ name: event.target.value })}
          />
        )}
      </Field>
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label={t("settings.contacts.channel")}>
          {(control) => (
            <Select {...control} value={form.channel} onChange={(event) => update({ channel: event.target.value as ManagerContactChannel })}>
              {CHANNELS.map((channel) => (
                <option key={channel} value={channel}>
                  {t(CHANNEL_LABELS[channel])}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("settings.contacts.language")}>
          {(control) => (
            <Select {...control} value={form.language} onChange={(event) => update({ language: event.target.value })}>
              {languageOptions.map((tag) => (
                <option key={tag} value={tag}>
                  {languageName(tag, locale)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
      <Field
        label={t(ADDRESS_LABELS[form.channel])}
        hint={t(ADDRESS_HINTS[form.channel])}
        required
        error={errors.address ? t(CONTACT_ERRORS[errors.address]) : undefined}
      >
        {(control) => (
          <Input
            {...control}
            type={form.channel === "email" ? "email" : form.channel === "telegram" ? "text" : "tel"}
            inputMode={form.channel === "email" ? "email" : form.channel === "telegram" ? "numeric" : "tel"}
            dir="ltr"
            autoComplete="off"
            value={form.address}
            onChange={(event) => update({ address: event.target.value })}
          />
        )}
      </Field>
      <InlineError error={error} />
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onCancel} disabled={isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={isPending} loadingText={t("common.saving")}>
          {t("common.save")}
        </Button>
      </div>
    </form>
  );
}
