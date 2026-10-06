"use client";

import { useState } from "react";

import { Field, Input, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import {
  NOTICE_FIELDS,
  NOTICE_LANGUAGES,
  NOTICE_MAX_LENGTH,
  noticeFill,
  type IncidentForm,
  type IncidentFormErrors,
  type IncidentProblem,
  type NoticeField,
  type NoticeLanguage,
} from "../../_lib/incidentForm";

const TEXT_ROWS: Readonly<Record<NoticeField, number>> = {
  nature: 3,
  subject_categories: 2,
  record_categories: 2,
  likely_consequences: 2,
  measures: 2,
};

/**
 * The DPA 12.1 part of a breach: the approximate numbers concerned and the
 * five texts per language (English required), one language at a time.
 */
export function BreachNoticeFields({
  form,
  errors,
  errorText,
  onChange,
}: {
  form: IncidentForm;
  errors: IncidentFormErrors;
  errorText: (problem: IncidentProblem) => string;
  onChange: (patch: Partial<IncidentForm>) => void;
}) {
  const { t } = useI18n();
  const [language, setLanguage] = useState<NoticeLanguage>("en");
  const notice = form.notices[language];
  const problem = errors.notices[language];

  const setText = (field: NoticeField, value: string) =>
    onChange({ notices: { ...form.notices, [language]: { ...notice, [field]: value } } });

  return (
    <fieldset className="space-y-4 rounded-xl border border-line p-4">
      <legend className="px-1 text-sm font-semibold text-ink">{t("adminIncident.breach.title")}</legend>
      <p className="text-sm text-ink-muted">{t("adminIncident.breach.description")}</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label={t("adminIncident.breach.subjects")}
          required
          error={errors.fields.subjectCount ? errorText(errors.fields.subjectCount) : undefined}
        >
          {(control) => (
            <Input
              {...control}
              inputMode="numeric"
              autoComplete="off"
              value={form.subjectCount}
              onChange={(event) => onChange({ subjectCount: event.target.value })}
            />
          )}
        </Field>
        <Field
          label={t("adminIncident.breach.records")}
          required
          error={errors.fields.recordCount ? errorText(errors.fields.recordCount) : undefined}
        >
          {(control) => (
            <Input
              {...control}
              inputMode="numeric"
              autoComplete="off"
              value={form.recordCount}
              onChange={(event) => onChange({ recordCount: event.target.value })}
            />
          )}
        </Field>
      </div>

      <div role="group" aria-label={t("adminIncident.breach.language")} className="flex flex-wrap gap-2">
        {NOTICE_LANGUAGES.map((code) => {
          const fill = noticeFill(form.notices[code]);
          const hasProblem = errors.notices[code] !== undefined;
          return (
            <button
              key={code}
              type="button"
              aria-pressed={language === code}
              onClick={() => setLanguage(code)}
              className={cn(
                "motion-press rounded-full border px-3 py-1.5 text-sm transition-colors",
                language === code ? "border-accent-solid bg-accent-soft text-accent-ink" : "border-line text-ink hover:bg-surface-muted",
                hasProblem && "border-danger text-danger",
              )}
            >
              {t(`adminIncident.breach.languages.${code}`)}
              {code === "en" ? <span aria-hidden> *</span> : null}
              {fill !== "empty" ? (
                <span className="ms-1.5 text-xs opacity-80">
                  ({t(fill === "complete" ? "adminIncident.breach.complete" : "adminIncident.breach.partial")})
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      {problem ? (
        <p className="text-sm text-danger" role="alert">
          {errorText(problem)}
        </p>
      ) : null}

      <div className="space-y-4" key={language}>
        {NOTICE_FIELDS.map((field) => (
          <Field key={field} label={t(`adminIncident.breach.fields.${field}`)} required={language === "en"}>
            {(control) => (
              <Textarea
                {...control}
                lang={language}
                rows={TEXT_ROWS[field]}
                maxLength={NOTICE_MAX_LENGTH[field]}
                value={notice[field]}
                onChange={(event) => setText(field, event.target.value)}
              />
            )}
          </Field>
        ))}
      </div>
    </fieldset>
  );
}
