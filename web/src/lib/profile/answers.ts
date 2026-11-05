/**
 * Niche answers as the profile editor saves them (PATCH …/profile): every
 * question on the screen is named, so an answer the owner cleared is
 * cleared in the profile too, and questions on other screens stay as
 * they are.
 */

import type { WizardQuestionView } from "@/api/types";

import { isChoiceQuestion, type AnswerValues, type ProfileAnswerInput } from "../wizard/answers";

export function answersPatch(questions: readonly WizardQuestionView[], values: AnswerValues): ProfileAnswerInput[] {
  return questions.map((item) => {
    const value = values[item.question.key];
    if (isChoiceQuestion(item)) {
      return { question_key: item.question.key, choice_keys: value?.choices ?? [] };
    }
    const text = value?.text.trim() ?? "";
    return { question_key: item.question.key, answer: text === "" ? null : text };
  });
}
