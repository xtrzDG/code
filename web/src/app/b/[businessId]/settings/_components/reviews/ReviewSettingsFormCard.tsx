"use client";

import Link from "next/link";
import { useState } from "react";

import { Switch } from "@/components/content/Switch";
import { useBusiness } from "@/components/business/BusinessContext";
import { AutosaveHint } from "@/components/forms/AutosaveHint";
import { SavePill } from "@/components/forms/SavePill";
import { useAutosaveForm } from "@/components/forms/useAutosaveForm";
import { Alert, Card, Field, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import {
  delayOptions,
  delayText,
  feedbackReadiness,
  isSameReviewSettings,
  READINESS_TEXTS,
  READINESS_TONES,
  reviewSettingsBody,
  reviewSettingsErrors,
  reviewSettingsForm,
  type ReviewSettingsBody,
  type ReviewSettingsForm,
  type ReviewSettingsView,
} from "../../_lib/reviews";
import type { ReviewSettingsState } from "../../_lib/useReviewSettings";

type TextField = "templateName" | "reviewUrl";

/**
 * The owner's choices: whether and when customers are asked about their
 * visit, the WhatsApp template for those quiet for a day, and the Google
 * review page every customer who answers is invited to. Every change
 * saves itself; a name or link that is not valid yet waits (its error
 * shows once the field is left), and switching feedback off offers Undo.
 */
export function ReviewSettingsFormCard({ stored, state }: { stored: ReviewSettingsView; state: ReviewSettingsState }) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const { save, settings, stats } = state;
  const [left, setLeft] = useState<readonly TextField[]>([]);
  const form = useAutosaveForm<ReviewSettingsForm, ReviewSettingsView, ReviewSettingsBody>({
    stored,
    toForm: reviewSettingsForm,
    invalidFields: (values) => {
      const errors = reviewSettingsErrors(values);
      return (["templateName", "reviewUrl"] as const).filter((field) => errors[field] !== null);
    },
    toBody: (values, base) => (isSameReviewSettings(values, base) ? null : reviewSettingsBody(values)),
    save: (body) => save.run(body),
    onSaved: (saved) => {
      settings.setData(saved);
      stats.reload();
    },
    undo: (before, after) => (before.isFeedbackEnabled && !after.isFeedbackEnabled ? t("reviewSettings.feedback.turnedOff") : null),
  });
  const { values } = form;
  const errors = reviewSettingsErrors(values);
  const errorOf = (field: TextField) => {
    const key = left.includes(field) ? errors[field] : null;
    return key ? t(key) : undefined;
  };
  const leave = (field: TextField) => {
    setLeft((current) => (current.includes(field) ? current : [...current, field]));
    form.flush();
  };
  const readiness = feedbackReadiness(values, form.stored);
  const pill = (field: keyof ReviewSettingsForm) => <SavePill state={form.fieldState(field)} onRetry={form.retry} />;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <AutosaveHint state={form.state} />
      </div>
      <Card title={t("reviewSettings.feedback.title")} description={t("reviewSettings.feedback.description")}>
        <div className="space-y-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
              <p className="text-sm font-medium text-ink">{t("reviewSettings.feedback.toggle")}</p>
              {pill("isFeedbackEnabled")}
            </div>
            <Switch
              checked={values.isFeedbackEnabled}
              onChange={(isFeedbackEnabled) => form.update("isFeedbackEnabled", isFeedbackEnabled)}
              label={t("reviewSettings.feedback.toggle")}
            />
          </div>
          <Alert tone={READINESS_TONES[readiness]}>
            <p>{t(READINESS_TEXTS[readiness])}</p>
            {readiness !== "off" && !form.stored.is_whatsapp_connected ? (
              <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                <span>{t("reviewSettings.feedback.whatsappMissing")}</span>
                <Link
                  href={businessPath(business.id, "assistant/channels")}
                  className="font-medium text-accent underline underline-offset-2 hover:no-underline"
                >
                  {t("reviewSettings.feedback.connectWhatsapp")}
                </Link>
              </p>
            ) : null}
          </Alert>
          <Field label={t("reviewSettings.feedback.delay")} hint={t("reviewSettings.feedback.delayHint")} status={pill("delayMinutes")}>
            {(control) => (
              <Select
                {...control}
                value={String(values.delayMinutes)}
                onChange={(event) => form.update("delayMinutes", Number(event.target.value))}
              >
                {delayOptions(values.delayMinutes).map((minutes) => {
                  const text = delayText(minutes);
                  return (
                    <option key={minutes} value={minutes}>
                      {tp(text.key, text.count)}
                    </option>
                  );
                })}
              </Select>
            )}
          </Field>
          <Field
            label={t("reviewSettings.feedback.template")}
            hint={t("reviewSettings.feedback.templateHint")}
            error={errorOf("templateName")}
            status={pill("templateName")}
          >
            {(control) => (
              <Input
                {...control}
                dir="ltr"
                autoComplete="off"
                spellCheck={false}
                placeholder="visit_feedback"
                value={values.templateName}
                onChange={(event) => form.type("templateName", event.target.value)}
                onBlur={() => leave("templateName")}
              />
            )}
          </Field>
          <p className="text-sm text-ink-muted">{t("reviewSettings.feedback.rules")}</p>
        </div>
      </Card>

      <Card title={t("reviewSettings.link.title")} description={t("reviewSettings.link.description")}>
        <div className="space-y-3">
          <Field label={t("reviewSettings.link.label")} hint={t("reviewSettings.link.hint")} error={errorOf("reviewUrl")} status={pill("reviewUrl")}>
            {(control) => (
              <Input
                {...control}
                type="url"
                dir="ltr"
                inputMode="url"
                autoComplete="url"
                spellCheck={false}
                placeholder="https://g.page/r/…/review"
                value={values.reviewUrl}
                onChange={(event) => form.type("reviewUrl", event.target.value)}
                onBlur={() => leave("reviewUrl")}
              />
            )}
          </Field>
          <p className="text-sm text-ink-muted">
            {values.reviewUrl.trim() === ""
              ? t("reviewSettings.link.missing")
              : form.stored.is_link_tracked
                ? t("reviewSettings.link.tracked")
                : null}
          </p>
        </div>
      </Card>
    </div>
  );
}
