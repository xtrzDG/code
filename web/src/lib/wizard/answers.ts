/**
 * Pure helpers of the profile wizard (app/b/[businessId]/onboarding):
 * niche answers, their API body and the problems the API would refuse.
 */

import type { WizardQuestionView } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

/** One answer as the form holds it: text, or choice keys for choice questions. */
export interface AnswerValue {
  text: string;
  choices: string[];
}

export type AnswerValues = Record<string, AnswerValue>;

export interface ProfileAnswerInput {
  question_key: string;
  answer?: string | null;
  choice_keys?: string[];
}

const CHOICE_TYPES = new Set(["single_choice", "multiple_choice"]);

export function isChoiceQuestion(question: WizardQuestionView): boolean {
  return CHOICE_TYPES.has(question.question.answer_type);
}

/** Form values from the wizard's current answers. */
export function initialAnswers(questions: readonly WizardQuestionView[]): AnswerValues {
  const values: AnswerValues = {};
  for (const item of questions) {
    const selected = item.selected_choice_keys ?? [];
    if (isChoiceQuestion(item)) {
      const choices = selected.length > 0 ? selected : (item.answer ?? "").split(",").filter(Boolean);
      values[item.question.key] = { text: "", choices };
    } else {
      values[item.question.key] = { text: item.answer ?? selected[0] ?? "", choices: [] };
    }
  }
  return values;
}

/**
 * The `answers` of a step body. A step save replaces all answers of that
 * step, so every answered question is sent and empty ones are left out
 * (which clears them).
 */
export function answersPayload(
  questions: readonly WizardQuestionView[],
  values: AnswerValues,
): ProfileAnswerInput[] {
  const answers: ProfileAnswerInput[] = [];
  for (const item of questions) {
    const value = values[item.question.key];
    if (!value) {
      continue;
    }
    if (isChoiceQuestion(item)) {
      if (value.choices.length > 0) {
        answers.push({ question_key: item.question.key, choice_keys: value.choices });
      }
    } else if (value.text.trim() !== "") {
      answers.push({ question_key: item.question.key, answer: value.text.trim() });
    }
  }
  return answers;
}

const MAX_SHORT_TEXT = 300;
const MAX_LONG_TEXT = 4000;
const WEB_LINK = /^https?:\/\/[^\s/]+(\/\S*)?$/;

/** Problems the API would refuse, per question key. */
export function validateAnswers(
  questions: readonly WizardQuestionView[],
  values: AnswerValues,
): Record<string, MessageKey> {
  const errors: Record<string, MessageKey> = {};
  for (const item of questions) {
    const text = values[item.question.key]?.text.trim() ?? "";
    if (text === "") {
      continue;
    }
    switch (item.question.answer_type) {
      case "number":
        if (!/^\d+$/.test(text)) {
          errors[item.question.key] = "validation.wholeNumber";
        }
        break;
      case "url":
        if (!WEB_LINK.test(text) || text.length < 10) {
          errors[item.question.key] = "validation.url";
        }
        break;
      case "short_text":
        if (text.length > MAX_SHORT_TEXT) {
          errors[item.question.key] = "validation.tooLong";
        }
        break;
      case "long_text":
        if (text.length > MAX_LONG_TEXT) {
          errors[item.question.key] = "validation.tooLong";
        }
        break;
      default:
        break;
    }
  }
  return errors;
}
