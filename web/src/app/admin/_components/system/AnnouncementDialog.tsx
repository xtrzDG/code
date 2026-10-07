"use client";

import { useState, type FormEvent } from "react";

import { Button, Checkbox, DateTimeField, Field, Fieldset, Modal, Select, Textarea } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { ANNOUNCEMENT_LEVELS, STATUS_COMPONENTS } from "@/lib/help/platformStatus";

import {
  ANNOUNCEMENT_LANGUAGES,
  NO_ERRORS,
  TEXT_MAX_LENGTH,
  buildCreateBody,
  buildUpdateBody,
  emptyAnnouncementForm,
  formFromAnnouncement,
  needsComponents,
  type AdminAnnouncement,
  type AnnouncementErrors,
  type AnnouncementForm,
  type AnnouncementLevel,
  type AnnouncementProblem,
  type CreateAnnouncementBody,
  type UpdateAnnouncementBody,
} from "../../_lib/announcementForm";

interface AnnouncementDialogProps {
  /** null: closed; "new": a new announcement; an announcement: update it. */
  editing: AdminAnnouncement | "new" | null;
  onClose: () => void;
  onPublish: (body: CreateAnnouncementBody) => Promise<AdminAnnouncement | null>;
  onUpdate: (id: string, body: UpdateAnnouncementBody) => Promise<AdminAnnouncement | null>;
  isSaving: boolean;
  error: unknown;
}

/** "New announcement" and "Update": the form is new each time it opens. */
export function AnnouncementDialog({ editing, onClose, ...props }: AnnouncementDialogProps) {
  const { t } = useI18n();
  const isNew = editing === "new";
  return (
    <Modal
      open={editing !== null}
      onClose={onClose}
      size="lg"
      title={t(isNew ? "adminStatus.form.createTitle" : "adminStatus.form.editTitle")}
      description={t("adminStatus.form.description")}
    >
      {editing ? <AnnouncementFormBody key={isNew ? "new" : editing.id} editing={editing} onClose={onClose} {...props} /> : null}
    </Modal>
  );
}

function AnnouncementFormBody({
  editing,
  onClose,
  onPublish,
  onUpdate,
  isSaving,
  error,
}: Omit<AnnouncementDialogProps, "editing"> & { editing: AdminAnnouncement | "new" }) {
  const { t, locale } = useI18n();
  const isNew = editing === "new";
  const [form, setForm] = useState<AnnouncementForm>(() => (isNew ? emptyAnnouncementForm() : formFromAnnouncement(editing)));
  const [errors, setErrors] = useState<AnnouncementErrors>(NO_ERRORS);
  const problem = (value: AnnouncementProblem | undefined) => (value ? t(`adminStatus.form.errors.${value}`) : undefined);

  const update = (patch: Partial<AnnouncementForm>) => {
    setForm((current) => ({ ...current, ...patch }));
    setErrors(NO_ERRORS);
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const now = Date.now() * 1000;
    if (isNew) {
      const built = buildCreateBody(form, now);
      if (!built.ok) {
        setErrors(built.errors);
      } else if (await onPublish(built.body)) {
        onClose();
      }
      return;
    }
    const built = buildUpdateBody(form, editing, now);
    if (!built.ok) {
      setErrors(built.errors);
    } else if (built.body === null || (await onUpdate(editing.id, built.body))) {
      onClose();
    }
  };

  const toggleComponent = (component: AnnouncementForm["components"][number], checked: boolean) =>
    update({ components: checked ? [...form.components, component] : form.components.filter((item) => item !== component) });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <Field label={t("adminStatus.form.level")} hint={t(`adminStatus.form.levelHints.${form.level}`)} required>
        {(control) => (
          <Select {...control} value={form.level} onChange={(event) => update({ level: event.target.value as AnnouncementLevel })}>
            {ANNOUNCEMENT_LEVELS.map((level) => (
              <option key={level} value={level}>
                {t(`platformStatus.announcementLevels.${level}`)}
              </option>
            ))}
          </Select>
        )}
      </Field>

      {needsComponents(form.level) ? (
        <Fieldset legend={t("adminStatus.form.components")} hint={t("adminStatus.form.componentsHint")} error={problem(errors.components)}>
          <div className="grid gap-2 sm:grid-cols-2">
            {STATUS_COMPONENTS.map((component) => (
              <Checkbox
                key={component}
                label={t(`platformStatus.components.${component}`)}
                checked={form.components.includes(component)}
                onChange={(event) => toggleComponent(component, event.target.checked)}
              />
            ))}
          </div>
        </Fieldset>
      ) : null}

      {ANNOUNCEMENT_LANGUAGES.map((language) => (
        <Field
          key={language}
          label={t("adminStatus.form.textLabel", { language: languageName(language, locale) })}
          hint={language === "en" ? t("adminStatus.form.textHint") : undefined}
          required={language === "en"}
          optionalLabel={language === "en" ? undefined : t("common.optional")}
          error={problem(errors.texts[language])}
        >
          {(control) => (
            <Textarea
              {...control}
              lang={language}
              rows={2}
              maxLength={TEXT_MAX_LENGTH}
              value={form.texts[language]}
              onChange={(event) => update({ texts: { ...form.texts, [language]: event.target.value } })}
            />
          )}
        </Field>
      ))}

      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label={t("adminStatus.form.startsAt")}
          hint={isNew ? t("adminStatus.form.startsAtHint") : undefined}
          optionalLabel={isNew ? t("common.optional") : undefined}
          error={problem(errors.startsAt)}
        >
          {(control) => (
            <DateTimeField {...control} disabled={!isNew} value={form.startsAt} onChange={(startsAt) => update({ startsAt })} />
          )}
        </Field>
        <Field label={t("adminStatus.form.expectedEnd")} optionalLabel={t("common.optional")} error={problem(errors.expectedEnd)}>
          {(control) => (
            <DateTimeField {...control} value={form.expectedEnd} onChange={(expectedEnd) => update({ expectedEnd })} />
          )}
        </Field>
      </div>
      <p className="-mt-2 text-xs text-ink-muted">{t("adminStatus.form.timeZone")}</p>

      <InlineError error={error} />

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onClose} disabled={isSaving}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={isSaving} loadingText={t("adminStatus.form.saving")}>
          {t(isNew ? "adminStatus.form.publish" : "adminStatus.form.save")}
        </Button>
      </div>
    </form>
  );
}
