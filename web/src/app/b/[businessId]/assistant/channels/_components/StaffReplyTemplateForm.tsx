"use client";

import { useId, useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { Button, Field, Input, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import type { ChannelView } from "../_lib/channels";
import { buildStaffTemplateBody, type StaffTemplateBody, type StaffTemplateFieldError } from "../_lib/staffTemplate";

const FIELD_ERRORS: Record<StaffTemplateFieldError, MessageKey> = {
  required: "channels.fieldErrors.required",
  name: "channels.staffTemplate.nameInvalid",
  language: "channels.staffTemplate.languageInvalid",
};

/**
 * On the WhatsApp card: the Meta-approved message template that carries
 * staff replies from the conversation card once the customer's 24-hour
 * window has closed (its body has one variable, the staff text). Owners
 * set or remove it; staff see which one is set.
 */
export function StaffReplyTemplateForm({
  channel,
  canManage,
  onSaved,
}: {
  channel: ChannelView;
  canManage: boolean;
  onSaved: (channel: ChannelView) => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const id = useId();
  const saved = channel.staff_reply_template ?? null;
  const [name, setName] = useState(saved?.name ?? "");
  const [language, setLanguage] = useState(saved?.language_code ?? "");
  const [errors, setErrors] = useState<{ name?: StaffTemplateFieldError; language?: StaffTemplateFieldError }>({});

  const save = useMutation((body: StaffTemplateBody) =>
    api.PUT("/v1/businesses/{business_id}/channels/whatsapp/staff-template", {
      params: { path: { business_id: business.id } },
      body,
    }),
  );

  const apply = (updated: ChannelView, message: MessageKey) => {
    onSaved(updated);
    const template = updated.staff_reply_template ?? null;
    setName(template?.name ?? "");
    setLanguage(template?.language_code ?? "");
    toast.success(t(message));
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const built = buildStaffTemplateBody(name, language);
    if (!built.ok) {
      setErrors(built.errors);
      return;
    }
    setErrors({});
    const result = await save.run(built.body);
    if (result.ok) {
      apply(result.data, "channels.staffTemplate.savedToast");
    }
  };

  const onRemove = async () => {
    setErrors({});
    const result = await save.run({});
    if (result.ok) {
      apply(result.data, "channels.staffTemplate.removedToast");
    }
  };

  const headingId = `${id}-title`;
  return (
    <section aria-labelledby={headingId} className="mt-4 border-t border-line pt-4">
      <h4 id={headingId} className="text-sm font-semibold text-ink">
        {t("channels.staffTemplate.title")}
      </h4>
      <p className="mt-1 text-sm text-ink-muted">{t("channels.staffTemplate.description")}</p>
      <p className="mt-2 text-sm text-ink">
        {saved ? (
          <>
            {t("channels.staffTemplate.current")}{" "}
            <span dir="ltr" className="font-mono">
              {saved.name} ({saved.language_code})
            </span>
          </>
        ) : (
          t("channels.staffTemplate.notSet")
        )}
      </p>
      {canManage ? (
        <form noValidate onSubmit={(event) => void onSubmit(event)} className="mt-3 space-y-3">
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_8rem]">
            <Field
              label={t("channels.staffTemplate.name")}
              error={errors.name ? t(FIELD_ERRORS[errors.name]) : undefined}
            >
              {(control) => (
                <Input
                  {...control}
                  value={name}
                  dir="ltr"
                  spellCheck={false}
                  autoComplete="off"
                  maxLength={512}
                  placeholder="staff_reply"
                  className="font-mono"
                  onChange={(event) => setName(event.target.value)}
                />
              )}
            </Field>
            <Field
              label={t("channels.staffTemplate.language")}
              error={errors.language ? t(FIELD_ERRORS[errors.language]) : undefined}
            >
              {(control) => (
                <Input
                  {...control}
                  value={language}
                  dir="ltr"
                  spellCheck={false}
                  autoComplete="off"
                  maxLength={8}
                  placeholder="en_US"
                  className="font-mono"
                  onChange={(event) => setLanguage(event.target.value)}
                />
              )}
            </Field>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" variant="secondary" isLoading={save.isPending} loadingText={t("channels.widget.saving")}>
              {t("channels.staffTemplate.save")}
            </Button>
            {saved ? (
              <Button type="button" size="sm" variant="danger-ghost" disabled={save.isPending} onClick={() => void onRemove()}>
                {t("channels.staffTemplate.remove")}
              </Button>
            ) : null}
          </div>
        </form>
      ) : null}
    </section>
  );
}
