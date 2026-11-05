"use client";

/**
 * The niche's questions of one profile section ("Do you serve halal
 * food?"), required and optional, each answer saved by itself a moment
 * after it is given. Nothing is drawn for a section without questions.
 */

import { useId, useMemo, useState } from "react";

import { answersPatch } from "@/lib/profile/answers";
import { sectionQuestions, type ProfileSection } from "@/lib/profile/sections";
import { startingAnswers } from "@/lib/tunnel/questions";
import { validateAnswers, type AnswerValues } from "@/lib/wizard/answers";

import { QuestionField } from "../fields/QuestionField";
import type { StepContext } from "../flow/stepContext";
import { SaveProblem } from "./SaveProblem";
import { useProfileField } from "./useProfileField";

export function SectionQuestions({ ctx, section, title }: { ctx: StepContext; section: ProfileSection; title: string }) {
  const headingId = useId();
  const questions = useMemo(() => sectionQuestions(ctx.wizard, section), [ctx.wizard, section]);
  const [answers, setAnswers] = useState<AnswerValues>(() => startingAnswers(questions));
  const problems = validateAnswers(questions, answers);
  const saved = useProfileField(ctx.businessId, answersPatch(questions, answers), (value) => ({ answers: value }), {
    isValid: () => Object.keys(problems).length === 0,
  });

  if (questions.length === 0) {
    return null;
  }
  return (
    <section aria-labelledby={headingId} className="space-y-5 rounded-2xl border border-line bg-surface/85 p-5 backdrop-blur-sm sm:p-6">
      <h2 id={headingId} className="text-base font-semibold text-ink">
        {title}
      </h2>
      {questions.map((item) => (
        <QuestionField
          key={item.question.key}
          item={item}
          value={answers[item.question.key]}
          error={problems[item.question.key]}
          onChange={(value) => setAnswers((current) => ({ ...current, [item.question.key]: value }))}
        />
      ))}
      <SaveProblem error={saved.error} />
    </section>
  );
}
