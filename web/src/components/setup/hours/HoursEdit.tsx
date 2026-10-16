"use client";

/**
 * "Hours and bookings" of Assistant → Business profile: the tunnel's
 * fourth screen in the edit mode. The week, how bookings work (with the
 * deposit) and the niche's questions about them, saved as the owner
 * changes them; the niche's usual hours and rules only as a suggestion
 * to accept or change. What customers book has its own page.
 */

import Link from "next/link";

import { IconArrowRight } from "@/components/icons";
import { Alert, Button, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";
import { timeZoneLabel } from "@/lib/timeZones";

import { SaveProblem } from "../edit/SaveProblem";
import { SectionQuestions } from "../edit/SectionQuestions";
import type { StepContext } from "../flow/stepContext";
import { StepScreen } from "../StepScreen";
import { BookingFields } from "./BookingFields";
import { HoursEditor } from "./HoursEditor";
import { useHoursEdit } from "./useHoursEdit";

const SECTION = "space-y-4 rounded-2xl border border-line bg-surface/85 p-5 backdrop-blur-sm sm:p-6";

export function HoursEdit({ ctx }: { ctx: StepContext }) {
  const { t, locale } = useI18n();
  const step = useHoursEdit(ctx);
  const currency = ctx.wizard.currency_code;

  return (
    <StepScreen step="hours" mode="edit" title={t("profileEdit.sections.hours.title")} text={t("profileEdit.sections.hours.text")} wide actions={{}}>
      <div className="space-y-8">
        <section aria-labelledby="profile-hours" className="space-y-3">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h2 id="profile-hours" className="text-lg font-semibold text-ink">
              {t("tunnelOffer.hours.hoursLabel")}
            </h2>
            <p className="text-sm text-ink-subtle">{t("profileEdit.hours.timezone", { timezone: timeZoneLabel(ctx.wizard.timezone, locale) })}</p>
          </div>
          {step.isHoursSuggested ? (
            <Alert
              title={t("profileEdit.hours.suggestedTitle")}
              action={
                <Button size="sm" variant="secondary" onClick={step.acceptHours}>
                  {t("profileEdit.hours.useSuggested")}
                </Button>
              }
            >
              {t("profileEdit.hours.suggestedText")}
            </Alert>
          ) : null}
          <div className="rounded-2xl bg-surface/85 backdrop-blur-sm">
            <HoursEditor days={step.days} onChange={step.setDays} errors={step.hourErrors} />
          </div>
          {step.noHours ? (
            <p className="text-sm text-danger" role="alert">
              {t("tunnelOffer.hours.errors.noHours")}
            </p>
          ) : null}
          <SaveProblem error={step.hoursError} />
        </section>

        {step.takesBookings ? (
          <section aria-labelledby="profile-bookings" className={SECTION}>
            <h2 id="profile-bookings" className="text-lg font-semibold text-ink">
              {t("tunnelOffer.hours.bookingsTitle")}
            </h2>
            {step.isRulesSuggested ? (
              <Alert
                title={t("profileEdit.hours.bookingSuggestedTitle")}
                action={
                  <Button size="sm" variant="secondary" onClick={step.acceptRules}>
                    {t("profileEdit.hours.useSuggestedBooking")}
                  </Button>
                }
              >
                {t("profileEdit.hours.bookingSuggestedText")}
              </Alert>
            ) : null}
            <BookingFields
              form={step.booking}
              onChange={step.setBooking}
              bySlots={step.bySlots}
              resource={null}
              onResource={() => undefined}
              problem={step.bookingProblem}
            />
            <Field
              label={t("profileEdit.hours.deposit", { currency })}
              hint={t("profileEdit.hours.depositHint")}
              optionalLabel={t("common.optional")}
              error={step.depositProblem ? t(step.depositProblem) : undefined}
              className="sm:max-w-xs"
            >
              {(control) => (
                <Input {...control} inputMode="decimal" value={step.deposit} onChange={(event) => step.setDeposit(event.target.value)} className="tabular-nums" />
              )}
            </Field>
            <SaveProblem error={step.rulesError} />
            <div className="flex flex-col gap-3 rounded-xl border border-line bg-surface-muted/40 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 space-y-0.5">
                <p className="text-sm font-semibold text-ink">{t("profileEdit.hours.resourcesTitle")}</p>
                <p className="text-sm text-ink-muted">{t("profileEdit.hours.resourcesText")}</p>
              </div>
              <Link
                href={`${businessPath(ctx.businessId, "assistant/knowledge")}/resources`}
                className="inline-flex min-h-10 shrink-0 items-center gap-1.5 rounded-lg px-2 text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-focus"
              >
                {t("profileEdit.hours.openResources")}
                <IconArrowRight className="size-4 rtl:-scale-x-100" aria-hidden />
              </Link>
            </div>
          </section>
        ) : null}

        <SectionQuestions ctx={ctx} section="hours" title={t("profileEdit.hours.questionsTitle")} />
      </div>
    </StepScreen>
  );
}
