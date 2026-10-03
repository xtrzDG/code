/**
 * The niche's required questions in the tunnel. Each screen asks only the
 * required questions that belong to it (the first screen the ones about
 * the business, "Hours and bookings" the ones about hours and bookings),
 * the rest waits in Assistant → Hours and rules. Before the business
 * exists the questions come from the catalog; afterwards from the profile
 * wizard, with the answers already given.
 */

import type { Schema, WizardQuestionView } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";
import { answersPayload, initialAnswers, validateAnswers, type AnswerValues, type ProfileAnswerInput } from "@/lib/wizard/answers";

type ProfileWizardStep = Schema<"ProfileWizardStep">;

/** The profile steps whose questions the first screen asks (the API's "business" setup step). */
export const BUSINESS_QUESTION_STEPS: ReadonlySet<ProfileWizardStep> = new Set(["niche_and_languages", "faq_and_handoff", "channels"]);
/** The profile steps whose questions "Hours and bookings" asks. */
export const HOURS_QUESTION_STEPS: ReadonlySet<ProfileWizardStep> = new Set(["contacts_and_hours", "booking_rules"]);

/** Catalog questions (no answers yet) in the shape the wizard gives them. */
export function catalogQuestions(questions: readonly Schema<"LocalizedQuestionView">[]): WizardQuestionView[] {
  return questions.map((question) => ({ question }));
}

/** Every question of the profile wizard, with its current answer. */
export function wizardQuestions(wizard: Pick<Schema<"ProfileWizardView">, "steps">): WizardQuestionView[] {
  return wizard.steps.flatMap((step) => step.questions ?? []);
}

/** The required questions of the given profile steps. */
export function requiredQuestions(questions: readonly WizardQuestionView[], steps: ReadonlySet<ProfileWizardStep>): WizardQuestionView[] {
  return questions.filter((item) => item.question.is_required && steps.has(item.question.step));
}

/** Answers to start from: what is saved, with the draft's answers over it. */
export function startingAnswers(questions: readonly WizardQuestionView[], draft: AnswerValues = {}): AnswerValues {
  const keys = new Set(questions.map((item) => item.question.key));
  const fromDraft = Object.fromEntries(Object.entries(draft).filter(([key]) => keys.has(key)));
  return { ...initialAnswers(questions), ...fromDraft };
}

function isAnswered(item: WizardQuestionView, values: AnswerValues): boolean {
  const value = values[item.question.key];
  if (!value) {
    return false;
  }
  return value.choices.length > 0 || value.text.trim() !== "";
}

/** What the API would refuse, and required questions left empty. */
export function answerProblems(questions: readonly WizardQuestionView[], values: AnswerValues): Record<string, MessageKey> {
  const problems: Record<string, MessageKey> = { ...validateAnswers(questions, values) };
  for (const item of questions) {
    if (item.question.is_required && !isAnswered(item, values) && !problems[item.question.key]) {
      problems[item.question.key] = "validation.required";
    }
  }
  return problems;
}

/** The answers to send: the screen's questions only, so other answers stay as they are. */
export function answersToSave(questions: readonly WizardQuestionView[], values: AnswerValues): ProfileAnswerInput[] {
  return answersPayload(questions, values);
}
