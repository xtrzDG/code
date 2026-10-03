"use client";

/**
 * "Hours and bookings" as state: the week (the saved hours, else the
 * niche's usual ones), the booking choices, the first bookable place and
 * the niche's required questions about hours and bookings. Valid changes
 * save themselves to the profile; Continue saves what is left, creates the
 * bookable place and accepts the rest of the niche's starter answers (who
 * to call when, what never to promise, the tone, ready answers), which
 * fill only what the owner has not written themselves.
 */

import { useMemo, useState } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/result";
import type { Schema } from "@/api/types";
import { hoursToRows, rowsToHours, type DayRows } from "@/app/b/[businessId]/assistant/profile/_components/HoursEditor";
import { useToast } from "@/components/ui";
import { describeError } from "@/api/errors";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { bookingForm, bookingRulesInput, isResourceEdited, resourceBody, resourceForm, type BookingProblem } from "@/lib/tunnel/bookings";
import { answerProblems, answersToSave, HOURS_QUESTION_STEPS, requiredQuestions, startingAnswers, wizardQuestions } from "@/lib/tunnel/questions";
import type { AnswerValues } from "@/lib/wizard/answers";

import { useSaveTracker } from "../SaveTracker";
import { useAutosave } from "../useAutosave";
import type { StepContext } from "../flow/stepContext";
import { useProfilePatch } from "../flow/useProfilePatch";

type StarterSection = Schema<"StarterSection">;
const AFTER_HOURS: readonly StarterSection[] = ["handoff_rules", "forbidden_rules", "tone", "faq"];

function isSuggested(starters: Schema<"StarterAnswersView">, section: StarterSection): boolean {
  return starters.sections.some((item) => item.section === section && item.state === "suggested");
}

export function useHoursStep(ctx: StepContext) {
  const { t } = useI18n();
  const toast = useToast();
  const track = useSaveTracker();
  const { wizard, starters } = ctx;
  const takesBookings = wizard.niche.takes_bookings;
  const questions = useMemo(() => requiredQuestions(wizardQuestions(wizard), HOURS_QUESTION_STEPS), [wizard]);
  const needsResource = takesBookings && isSuggested(starters, "resource");

  const [days, setDays] = useState<DayRows[]>(() => hoursToRows(wizard.profile.hours?.length ? wizard.profile.hours : (starters.hours ?? [])));
  const [booking, setBooking] = useState(() => bookingForm(wizard.profile.booking_rules, starters.booking_rules));
  const [resource, setResource] = useState(() => resourceForm(starters.resource));
  const [answers, setAnswers] = useState<AnswerValues>(() => startingAnswers(questions));
  const [problems, setProblems] = useState<{ hours?: MessageKey; booking?: BookingProblem | null; answers: Record<string, MessageKey> }>({ answers: {} });
  const [isSaving, setSaving] = useState(false);

  const hours = rowsToHours(days);
  const rules = takesBookings ? bookingRulesInput(booking, wizard.profile.booking_rules ?? starters.booking_rules) : null;
  const patch = {
    ...(hours.ok ? { hours: hours.hours } : {}),
    ...(rules?.ok ? { booking_rules: rules.rules } : {}),
    answers: answersToSave(questions, answers),
  };
  const patchProfile = useProfilePatch(ctx.businessId);
  const autosave = useAutosave(patch, patchProfile, { isValid: () => hours.ok && hours.hours.length > 0 });

  const validate = (): boolean => {
    const place = needsResource ? resourceBody(resource, starters.resource) : null;
    const found = {
      hours: !hours.ok ? Object.values(hours.errors)[0] : hours.hours.length === 0 ? ("tunnelOffer.hours.errors.noHours" as const) : undefined,
      booking: rules && !rules.ok ? rules.problem : place && !place.ok ? place.problem : null,
      answers: answerProblems(questions, answers),
    };
    setProblems(found);
    return !found.hours && !found.booking && Object.keys(found.answers).length === 0;
  };

  /** Save everything and accept the starter answers; resolves to whether it all went. */
  const finish = async (): Promise<boolean> => {
    if (!validate()) {
      return false;
    }
    setSaving(true);
    try {
      if (!(await autosave.flush())) {
        throw new Error("profile");
      }
      const edited = needsResource && isResourceEdited(resource, starters.resource);
      const created = resourceBody(resource, starters.resource);
      if (edited && created.ok) {
        await track(unwrap(api.POST("/v1/businesses/{business_id}/resources", { params: { path: { business_id: ctx.businessId } }, body: created.body })).then(() => true));
      }
      const sections = AFTER_HOURS.filter((section) => isSuggested(starters, section));
      if (needsResource && !edited) {
        sections.push("resource");
      }
      if (sections.length > 0) {
        await track(
          unwrap(
            api.POST("/v1/businesses/{business_id}/setup/starter-answers/apply", {
              params: { path: { business_id: ctx.businessId } },
              body: { sections },
            }),
          ).then(() => true),
        );
      }
      return true;
    } catch (error) {
      toast.show({ tone: "error", title: error instanceof Error && error.message === "profile" ? t("tunnel.saveFailed") : describeError(error, t).title });
      return false;
    } finally {
      setSaving(false);
    }
  };

  return {
    takesBookings,
    bySlots: wizard.niche.booking_unit !== "night",
    questions,
    days,
    setDays: (next: DayRows[]) => {
      setDays(next);
      setProblems((current) => ({ ...current, hours: undefined }));
    },
    booking,
    setBooking,
    resource: needsResource ? resource : null,
    setResource,
    answers,
    setAnswer: (key: string, value: AnswerValues[string]) => setAnswers((current) => ({ ...current, [key]: value })),
    problems,
    hourErrors: hours.ok ? {} : hours.errors,
    isSaving,
    finish,
  };
}
