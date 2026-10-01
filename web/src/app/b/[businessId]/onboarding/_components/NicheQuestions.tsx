"use client";

import { useState } from "react";

import type { WizardQuestionView } from "@/api/types";
import { Checkbox, Field, Fieldset, Input, Radio, Select, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  answersPayload,
  initialAnswers,
  validateAnswers,
  type AnswerValue,
  type AnswerValues,
  type ProfileAnswerInput,
} from "@/lib/wizard";

import { StepSection } from "./StepForm";

/** Answers of one step's niche questions, with validation and the API payload. */
export function useNicheAnswers(questions: readonly WizardQuestionView[], onChange: () => void) {
  const [values, setValues] = useState<AnswerValues>(() => initialAnswers(questions));
  const [errors, setErrors] = useState<Record<string, MessageKey>>({});

  return {
    values,
    errors,
    setValue: (key: string, value: AnswerValue) => {
      setValues((current) => ({ ...current, [key]: value }));
      setErrors((current) => {
        const { [key]: _removed, ...rest } = current;
        return rest;
      });
      onChange();
    },
    /** Shows problems next to the questions; true when the answers can be sent. */
    validate: (): boolean => {
      const found = validateAnswers(questions, values);
      setErrors(found);
      return Object.keys(found).length === 0;
    },
    payload: (): ProfileAnswerInput[] => answersPayload(questions, values),
  };
}

export type NicheAnswersState = ReturnType<typeof useNicheAnswers>;

/** The niche-specific questions of a step, each rendered for its answer type. */
export function NicheQuestions({
  questions,
  state,
}: {
  questions: readonly WizardQuestionView[];
  state: NicheAnswersState;
}) {
  const { t } = useI18n();
  if (questions.length === 0) {
    return null;
  }

  return (
    <StepSection title={t("onboarding.nicheQuestions")}>
      <div className="space-y-6">
        {questions.map((item) => (
          <Question
            key={item.question.key}
            item={item}
            value={state.values[item.question.key] ?? { text: "", choices: [] }}
            error={state.errors[item.question.key]}
            onChange={(value) => state.setValue(item.question.key, value)}
          />
        ))}
      </div>
    </StepSection>
  );
}

function Question({
  item,
  value,
  error,
  onChange,
}: {
  item: WizardQuestionView;
  value: AnswerValue;
  error: MessageKey | undefined;
  onChange: (value: AnswerValue) => void;
}) {
  const { t } = useI18n();
  const { question } = item;
  const errorText = error ? t(error) : undefined;
  const hint = question.hint ?? undefined;
  const setText = (text: string) => onChange({ text, choices: [] });

  switch (question.answer_type) {
    case "yes_no":
      return (
        <Fieldset legend={<RequiredLabel label={question.label} required={question.is_required} />} hint={hint} error={errorText}>
          <div className="flex gap-6">
            {(["yes", "no"] as const).map((option) => (
              <Radio
                key={option}
                name={`question-${question.key}`}
                id={`question-${question.key}-${option}`}
                checked={value.text === option}
                onChange={() => setText(option)}
                label={option === "yes" ? t("common.yes") : t("common.no")}
              />
            ))}
          </div>
        </Fieldset>
      );
    case "multiple_choice":
      return (
        <Fieldset legend={<RequiredLabel label={question.label} required={question.is_required} />} hint={hint} error={errorText}>
          <div className="grid gap-2 sm:grid-cols-2">
            {(question.choices ?? []).map((choice) => (
              <Checkbox
                key={choice.key}
                id={`question-${question.key}-${choice.key}`}
                checked={value.choices.includes(choice.key)}
                onChange={(event) =>
                  onChange({
                    text: "",
                    choices: event.target.checked
                      ? [...value.choices, choice.key]
                      : value.choices.filter((key) => key !== choice.key),
                  })
                }
                label={choice.label}
              />
            ))}
          </div>
        </Fieldset>
      );
    case "single_choice":
      return (
        <Field label={question.label} required={question.is_required} hint={hint} error={errorText}>
          {(control) => (
            <Select
              {...control}
              value={value.choices[0] ?? ""}
              onChange={(event) => onChange({ text: "", choices: event.target.value ? [event.target.value] : [] })}
            >
              <option value="">{t("onboarding.choose")}</option>
              {(question.choices ?? []).map((choice) => (
                <option key={choice.key} value={choice.key}>
                  {choice.label}
                </option>
              ))}
            </Select>
          )}
        </Field>
      );
    case "long_text":
      return (
        <Field label={question.label} required={question.is_required} hint={hint} error={errorText}>
          {(control) => (
            <Textarea {...control} required={false} value={value.text} maxLength={4000} onChange={(event) => setText(event.target.value)} />
          )}
        </Field>
      );
    default:
      return (
        <Field label={question.label} required={question.is_required} hint={hint} error={errorText}>
          {(control) => (
            <Input
              {...control}
              required={false}
              value={value.text}
              maxLength={question.answer_type === "url" ? 2048 : 300}
              type={question.answer_type === "url" ? "url" : question.answer_type === "phone_number" ? "tel" : "text"}
              inputMode={question.answer_type === "number" ? "numeric" : undefined}
              onChange={(event) => setText(event.target.value)}
            />
          )}
        </Field>
      );
  }
}

function RequiredLabel({ label, required }: { label: string; required: boolean }) {
  return (
    <>
      {label}
      {required ? (
        <span className="ml-0.5 text-danger" aria-hidden>
          *
        </span>
      ) : null}
    </>
  );
}
