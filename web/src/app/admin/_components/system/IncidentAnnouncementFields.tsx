"use client";

import { Checkbox, Field, Fieldset, Select, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { ANNOUNCEMENT_LEVELS, STATUS_COMPONENTS } from "@/lib/help/platformStatus";

import {
  ANNOUNCEMENT_LANGUAGES,
  NO_ERRORS,
  TEXT_MAX_LENGTH,
  needsComponents,
  type AnnouncementErrors,
  type AnnouncementForm,
  type AnnouncementLevel,
  type AnnouncementProblem,
} from "../../_lib/announcementForm";

interface IncidentAnnouncementFieldsProps {
  announcement: AnnouncementForm;
  errors: AnnouncementErrors | undefined;
  onChange: (announcement: AnnouncementForm) => void;
}

/**
 * The status announcement published with an incident: its level, the parts
 * of the platform it names and its text (English required). It starts now;
 * its expected end and later changes are made on the announcements card.
 */
export function IncidentAnnouncementFields({ announcement, errors = NO_ERRORS, onChange }: IncidentAnnouncementFieldsProps) {
  const { t, locale } = useI18n();
  const problem = (value: AnnouncementProblem | undefined) => (value ? t(`adminStatus.form.errors.${value}`) : undefined);
  const update = (patch: Partial<AnnouncementForm>) => onChange({ ...announcement, ...patch });
  const toggleComponent = (component: AnnouncementForm["components"][number], checked: boolean) =>
    update({
      components: checked ? [...announcement.components, component] : announcement.components.filter((item) => item !== component),
    });

  return (
    <section aria-labelledby="incident-announcement" className="space-y-4 rounded-2xl border border-line bg-surface-muted p-4">
      <h3 id="incident-announcement" className="text-sm font-semibold text-ink">
        {t("adminIncident.announcement.title")}
      </h3>
      <Field label={t("adminStatus.form.level")} hint={t(`adminStatus.form.levelHints.${announcement.level}`)} required>
        {(control) => (
          <Select {...control} value={announcement.level} onChange={(event) => update({ level: event.target.value as AnnouncementLevel })}>
            {ANNOUNCEMENT_LEVELS.map((level) => (
              <option key={level} value={level}>
                {t(`platformStatus.announcementLevels.${level}`)}
              </option>
            ))}
          </Select>
        )}
      </Field>

      {needsComponents(announcement.level) ? (
        <Fieldset legend={t("adminStatus.form.components")} hint={t("adminStatus.form.componentsHint")} error={problem(errors.components)}>
          <div className="grid gap-2 sm:grid-cols-2">
            {STATUS_COMPONENTS.map((component) => (
              <Checkbox
                key={component}
                label={t(`platformStatus.components.${component}`)}
                checked={announcement.components.includes(component)}
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
              value={announcement.texts[language]}
              onChange={(event) => update({ texts: { ...announcement.texts, [language]: event.target.value } })}
            />
          )}
        </Field>
      ))}
    </section>
  );
}
