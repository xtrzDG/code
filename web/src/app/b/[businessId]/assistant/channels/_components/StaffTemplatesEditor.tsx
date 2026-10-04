"use client";

import { useId, useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconChevronDown, IconPlus, IconTrash } from "@/components/icons";
import { Button, Field, Input, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { cn } from "@/lib/cn";

import type { ChannelView } from "../_lib/channels";
import {
  buildStaffTemplatesBody,
  isSameTemplates,
  newTemplateRow,
  nextTemplateLanguage,
  savedStaffTemplates,
  templateLanguageCode,
  templateRows,
  type StaffTemplatesBody,
  type TemplateRow,
  type TemplateRowError,
  type TemplateRowErrors,
} from "../_lib/staffTemplates";

/** The API keeps at most this many templates (one per language). */
const MAX_TEMPLATES = 30;

const ROW_ERRORS: Record<TemplateRowError, MessageKey> = {
  required: "channelSetup.templates.errors.required",
  name: "channelSetup.templates.errors.name",
  language: "channelSetup.templates.errors.language",
  duplicate: "channelSetup.templates.errors.duplicate",
};

/** The anchor the "Check templates" fix scrolls to. */
export const STAFF_TEMPLATES_ID = "whatsapp-staff-templates";

/**
 * On the WhatsApp card, folded under "For advanced users": the Meta-approved
 * templates that carry staff replies once a customer has not written for a
 * day, one per language (a reply takes the customer's language, else the
 * main one). Owners edit the rows and save them at once; staff see the list.
 */
export function StaffTemplatesEditor({
  channel,
  canManage,
  isOpen,
  onOpenChange,
  onSaved,
}: {
  channel: ChannelView;
  canManage: boolean;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onSaved: (channel: ChannelView) => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const id = useId();
  const saved = savedStaffTemplates(channel);
  const mainLanguage = templateLanguageCode(business.default_language);
  const [rows, setRows] = useState<TemplateRow[]>(() =>
    saved.length > 0 ? templateRows(saved) : [newTemplateRow(mainLanguage)],
  );
  const [errors, setErrors] = useState<Record<string, TemplateRowErrors>>({});

  const save = useMutation((body: StaffTemplatesBody) =>
    api.PUT("/v1/businesses/{business_id}/channels/whatsapp/staff-templates", {
      params: { path: { business_id: business.id } },
      body,
    }),
  );

  const update = (key: string, field: "language" | "name", value: string) => {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, [field]: value } : row)));
    setErrors((current) => ({ ...current, [key]: { ...current[key], [field]: undefined } }));
  };

  const addRow = () =>
    setRows((current) => [...current, newTemplateRow(nextTemplateLanguage(business.languages, business.default_language, current))]);

  const removeRow = (key: string) => setRows((current) => current.filter((row) => row.key !== key));

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const built = buildStaffTemplatesBody(rows);
    if (!built.ok) {
      setErrors(built.errors);
      return;
    }
    setErrors({});
    const result = await save.run(built.body);
    if (result.ok) {
      onSaved(result.data);
      setRows(templateRows(savedStaffTemplates(result.data)));
      toast.success(t("channelSetup.templates.savedToast"));
    }
  };

  const summary = saved
    .map((template) =>
      template.language_code === mainLanguage
        ? `${template.language_code} (${t("channelSetup.templates.mainLanguage")})`
        : template.language_code,
    )
    .join(", ");
  const panelId = `${id}-panel`;

  return (
    <section id={STAFF_TEMPLATES_ID} aria-labelledby={`${id}-title`} className="mt-4 scroll-mt-24 border-t border-line pt-4">
      <h4 id={`${id}-title`} className="text-sm font-semibold text-ink">
        <button
          type="button"
          aria-expanded={isOpen}
          aria-controls={panelId}
          onClick={() => onOpenChange(!isOpen)}
          className="flex w-full items-center justify-between gap-2 rounded-lg text-start focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <span>{t("channelSetup.templates.advanced")}</span>
          <IconChevronDown aria-hidden className={cn("size-4 shrink-0 text-ink-muted transition-transform", isOpen && "rotate-180")} />
        </button>
      </h4>
      <p className="mt-1 text-sm text-ink-muted">
        {saved.length > 0 ? (
          <span dir="ltr" className="font-mono">
            {t("channelSetup.templates.summary", { list: summary })}
          </span>
        ) : (
          t("channelSetup.templates.none")
        )}
      </p>

      {isOpen ? (
        <div id={panelId} className="mt-3 space-y-3">
          <p className="text-sm text-ink-muted">{t("channelSetup.templates.description")}</p>
          <p className="text-sm text-ink-muted">{t("channelSetup.templates.howTo")}</p>
          {canManage ? (
            <form noValidate onSubmit={(event) => void onSubmit(event)} className="space-y-3">
              <ul className="space-y-3">
                {rows.map((row) => (
                  <TemplateRowFields
                    key={row.key}
                    row={row}
                    errors={errors[row.key]}
                    onChange={update}
                    onRemove={() => removeRow(row.key)}
                  />
                ))}
              </ul>
              <div className="flex flex-wrap gap-2">
                <Button type="button" size="sm" variant="ghost" onClick={addRow} disabled={rows.length >= MAX_TEMPLATES}>
                  <IconPlus aria-hidden className="size-4" />
                  {t("channelSetup.templates.add")}
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  variant="secondary"
                  isLoading={save.isPending}
                  loadingText={t("channels.widget.saving")}
                  disabled={isSameTemplates(rows, saved)}
                >
                  {t("channelSetup.templates.save")}
                </Button>
              </div>
            </form>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function TemplateRowFields({
  row,
  errors,
  onChange,
  onRemove,
}: {
  row: TemplateRow;
  errors: TemplateRowErrors | undefined;
  onChange: (key: string, field: "language" | "name", value: string) => void;
  onRemove: () => void;
}) {
  const { t } = useI18n();
  const language = templateLanguageCode(row.language);
  return (
    <li className="grid items-start gap-2 rounded-xl bg-surface-muted/60 p-3 sm:grid-cols-[8rem_minmax(0,1fr)_auto]">
      <Field
        label={t("channelSetup.templates.language")}
        hint={t("channelSetup.templates.languageHint")}
        error={errors?.language ? t(ROW_ERRORS[errors.language]) : undefined}
      >
        {(control) => (
          <Input
            {...control}
            value={row.language}
            dir="ltr"
            spellCheck={false}
            autoComplete="off"
            maxLength={8}
            className="font-mono"
            onChange={(event) => onChange(row.key, "language", event.target.value)}
          />
        )}
      </Field>
      <Field
        label={t("channelSetup.templates.name")}
        hint={t("channelSetup.templates.nameHint")}
        error={errors?.name ? t(ROW_ERRORS[errors.name]) : undefined}
      >
        {(control) => (
          <Input
            {...control}
            value={row.name}
            dir="ltr"
            spellCheck={false}
            autoComplete="off"
            maxLength={512}
            className="font-mono"
            onChange={(event) => onChange(row.key, "name", event.target.value)}
          />
        )}
      </Field>
      <Button
        type="button"
        size="sm"
        variant="danger-ghost"
        className="sm:mt-7"
        onClick={onRemove}
        aria-label={language ? t("channelSetup.templates.remove", { language }) : t("channelSetup.templates.removeEmpty")}
      >
        <IconTrash aria-hidden className="size-4" />
      </Button>
    </li>
  );
}
