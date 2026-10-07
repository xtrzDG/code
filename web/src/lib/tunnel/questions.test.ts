import { describe, expect, it } from "vitest";

import type { Schema, WizardQuestionView } from "@/api/types";

import {
  answerProblems,
  answersToSave,
  BUSINESS_QUESTION_STEPS,
  catalogQuestions,
  HOURS_QUESTION_STEPS,
  requiredQuestions,
  startingAnswers,
  wizardQuestions,
} from "./questions";

type Question = Schema<"LocalizedQuestionView">;

function question(overrides: Partial<Question>): Question {
  return {
    key: "cuisine",
    fact_key: "cuisine",
    step: "niche_and_languages",
    answer_type: "short_text",
    is_required: true,
    label: "What cuisine?",
    hint: null,
    choices: [],
    ...overrides,
  } as Question;
}

const CUISINE = question({});
const PROPERTY = question({ key: "property_type", answer_type: "single_choice", choices: [{ key: "hotel", label: "Hotel" }] });
const CHECK_IN = question({ key: "check_in_time", step: "booking_rules" });
const SEATS = question({ key: "seats", step: "booking_rules", answer_type: "number", is_required: false });

describe("required questions of a screen", () => {
  it("are the required ones of its profile steps", () => {
    const all = catalogQuestions([CUISINE, PROPERTY, CHECK_IN, SEATS]);
    expect(requiredQuestions(all, BUSINESS_QUESTION_STEPS).map((item) => item.question.key)).toEqual(["cuisine", "property_type"]);
    expect(requiredQuestions(all, HOURS_QUESTION_STEPS).map((item) => item.question.key)).toEqual(["check_in_time"]);
  });

  it("come with their answers from the wizard", () => {
    const wizard = {
      steps: [
        { step: "niche_and_languages", number: 1, title: "", description: "", is_complete: false, questions: [{ question: CUISINE, answer: "Georgian" }] },
        { step: "offer", number: 3, title: "", description: "", is_complete: true },
      ],
    } as Pick<Schema<"ProfileWizardView">, "steps">;
    const questions = wizardQuestions(wizard);
    expect(questions).toHaveLength(1);
    expect(startingAnswers(questions)).toEqual({ cuisine: { text: "Georgian", choices: [] } });
  });

  it("start from the draft's answers over the saved ones, for their own questions only", () => {
    const questions: WizardQuestionView[] = [{ question: CUISINE, answer: "Georgian" }];
    expect(
      startingAnswers(questions, {
        cuisine: { text: "Italian", choices: [] },
        other: { text: "x", choices: [] },
      }),
    ).toEqual({ cuisine: { text: "Italian", choices: [] } });
  });
});

describe("answer problems", () => {
  it("ask for required answers and refuse what the API would", () => {
    const questions = catalogQuestions([CUISINE, PROPERTY, SEATS]);
    expect(answerProblems(questions, {})).toEqual({ cuisine: "validation.required", property_type: "validation.required" });
    expect(
      answerProblems(questions, {
        cuisine: { text: "Georgian", choices: [] },
        property_type: { text: "", choices: ["hotel"] },
        seats: { text: "many", choices: [] },
      }),
    ).toEqual({ seats: "validation.wholeNumber" });
  });

  it("send only the screen's answered questions", () => {
    const questions = catalogQuestions([CUISINE, PROPERTY]);
    expect(answersToSave(questions, { cuisine: { text: " Georgian ", choices: [] }, property_type: { text: "", choices: [] } })).toEqual([
      { question_key: "cuisine", answer: "Georgian" },
    ]);
  });
});
