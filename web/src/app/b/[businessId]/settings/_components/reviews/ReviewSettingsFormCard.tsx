"use client";

import Link from "next/link";
import { useState } from "react";

import { Switch } from "@/components/content/Switch";
import { useBusiness } from "@/components/business/BusinessContext";
import { Alert, Button, Card, Field, InlineError, Input, Select, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import {
  delayOptions,
  delayText,
  feedbackReadiness,
  hasErrors,
  isSameReviewSettings,
  READINESS_TEXTS,
  READINESS_TONES,
  reviewSettingsBody,
  reviewSettingsErrors,
  reviewSettingsForm,
  type ReviewSettingsForm,
  type ReviewSettingsView,
} from "../../_lib/reviews";
import type { ReviewSettingsState } from "../../_lib/useReviewSettings";

/**
 * The owner's choices: whether and when customers are asked about their
 * visit, the WhatsApp template for those quiet for a day, and the Google
 * review page every customer who answers is invited to.
 */
export function ReviewSettingsFormCard({ stored, state }: { stored: ReviewSettingsView; state: ReviewSettingsState }) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [form, setForm] = useState<ReviewSettingsForm>(() => reviewSettingsForm(stored));
  const [isChecked, setIsChecked] = useState(false);
  const { save, settings, stats } = state;
  const errors = reviewSettingsErrors(form);
  const shownErrors = isChecked ? errors : { templateName: null, reviewUrl: null };
  const readiness = feedbackReadiness(form, stored);
  const update = (change: Partial<ReviewSettingsForm>) => setForm((current) => ({ ...current, ...change }));

  const submit = async () => {
    setIsChecked(true);
    if (hasErrors(reviewSettingsErrors(form))) {
      return;
    }
    const result = await save.run(reviewSettingsBody(form));
    if (result.ok) {
      settings.setData(result.data);
      setForm(reviewSettingsForm(result.data));
      setIsChecked(false);
      stats.reload();
      toast.success(t("reviewSettings.saved"));
    }
  };

  return (
    <form
      noValidate
      className="space-y-6"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <Card title={t("reviewSettings.feedback.title")} description={t("reviewSettings.feedback.description")}>
        <div className="space-y-5">
          <div className="flex items-start justify-between gap-4">
            <p className="min-w-0 text-sm font-medium text-ink">{t("reviewSettings.feedback.toggle")}</p>
            <Switch
              checked={form.isFeedbackEnabled}
              onChange={(isFeedbackEnabled) => update({ isFeedbackEnabled })}
              label={t("reviewSettings.feedback.toggle")}
              disabled={save.isPending}
            />
          </div>
          <Alert tone={READINESS_TONES[readiness]}>
            <p>{t(READINESS_TEXTS[readiness])}</p>
            {readiness !== "off" && !stored.is_whatsapp_connected ? (
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
          <Field label={t("reviewSettings.feedback.delay")} hint={t("reviewSettings.feedback.delayHint")}>
            {(control) => (
              <Select
                {...control}
                value={String(form.delayMinutes)}
                disabled={save.isPending}
                onChange={(event) => update({ delayMinutes: Number(event.target.value) })}
              >
                {delayOptions(form.delayMinutes).map((minutes) => {
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
            error={shownErrors.templateName ? t(shownErrors.templateName) : undefined}
          >
            {(control) => (
              <Input
                {...control}
                dir="ltr"
                autoComplete="off"
                spellCheck={false}
                placeholder="visit_feedback"
                value={form.templateName}
                disabled={save.isPending}
                onChange={(event) => update({ templateName: event.target.value })}
              />
            )}
          </Field>
          <p className="text-sm text-ink-muted">{t("reviewSettings.feedback.rules")}</p>
        </div>
      </Card>

      <Card title={t("reviewSettings.link.title")} description={t("reviewSettings.link.description")}>
        <div className="space-y-3">
          <Field
            label={t("reviewSettings.link.label")}
            hint={t("reviewSettings.link.hint")}
            error={shownErrors.reviewUrl ? t(shownErrors.reviewUrl) : undefined}
          >
            {(control) => (
              <Input
                {...control}
                type="url"
                dir="ltr"
                inputMode="url"
                autoComplete="url"
                spellCheck={false}
                placeholder="https://g.page/r/…/review"
                value={form.reviewUrl}
                disabled={save.isPending}
                onChange={(event) => update({ reviewUrl: event.target.value })}
              />
            )}
          </Field>
          <p className="text-sm text-ink-muted">
            {form.reviewUrl.trim() === ""
              ? t("reviewSettings.link.missing")
              : stored.is_link_tracked
                ? t("reviewSettings.link.tracked")
                : null}
          </p>
        </div>
      </Card>

      <InlineError error={save.error} />
      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={isSameReviewSettings(form, stored)}
          isLoading={save.isPending}
          loadingText={t("common.saving")}
        >
          {t("reviewSettings.save")}
        </Button>
      </div>
    </form>
  );
}
