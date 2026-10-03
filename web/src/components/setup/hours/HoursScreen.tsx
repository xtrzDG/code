"use client";

/**
 * Step 4, "When are you open?": the week prefilled with the usual hours of
 * the niche (or what the business saved), how bookings work for niches
 * that take them, and the niche's required questions about hours and
 * bookings (a hotel's check-in time).
 */

import { HoursEditor } from "@/app/b/[businessId]/assistant/profile/_components/HoursEditor";
import { useI18n } from "@/i18n/client";

import { QuestionField } from "../fields/QuestionField";
import { StepScreen } from "../StepScreen";
import type { StepContext } from "../flow/stepContext";
import { BookingFields } from "./BookingFields";
import { useHoursStep } from "./useHoursStep";

export function HoursScreen({ ctx }: { ctx: StepContext }) {
  const { t } = useI18n();
  const step = useHoursStep(ctx);

  const submit = async () => {
    if (await step.finish()) {
      ctx.refresh();
      ctx.next();
    }
  };

  return (
    <StepScreen
      step="hours"
      title={t("tunnelOffer.hours.title")}
      text={t("tunnelOffer.hours.text")}
      wide
      actions={{ onContinue: () => void submit(), onBack: ctx.back, isBusy: step.isSaving }}
    >
      <div className="space-y-8">
        <section aria-labelledby="tunnel-hours" className="space-y-3">
          <h2 id="tunnel-hours" className="text-lg font-semibold text-ink">
            {t("tunnelOffer.hours.hoursLabel")}
          </h2>
          <div className="rounded-2xl bg-surface/85 backdrop-blur-sm">
            <HoursEditor days={step.days} onChange={step.setDays} errors={step.hourErrors} />
          </div>
          {step.problems.hours ? (
            <p className="text-sm text-danger" role="alert">
              {t(step.problems.hours)}
            </p>
          ) : null}
        </section>

        {step.takesBookings ? (
          <section aria-labelledby="tunnel-bookings" className="space-y-4 rounded-2xl border border-line bg-surface/85 p-5 backdrop-blur-sm sm:p-6">
            <h2 id="tunnel-bookings" className="text-lg font-semibold text-ink">
              {t("tunnelOffer.hours.bookingsTitle")}
            </h2>
            <BookingFields
              form={step.booking}
              onChange={step.setBooking}
              bySlots={step.bySlots}
              resource={step.resource}
              onResource={step.setResource}
              problem={step.problems.booking ?? null}
            />
          </section>
        ) : null}

        {step.questions.length > 0 ? (
          <section className="space-y-5 rounded-2xl border border-line bg-surface/85 p-5 backdrop-blur-sm sm:p-6">
            {step.questions.map((item) => (
              <QuestionField
                key={item.question.key}
                item={item}
                value={step.answers[item.question.key]}
                error={step.problems.answers[item.question.key]}
                onChange={(value) => step.setAnswer(item.question.key, value)}
              />
            ))}
          </section>
        ) : null}
      </div>
    </StepScreen>
  );
}
