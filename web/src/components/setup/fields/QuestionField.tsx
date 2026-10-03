"use client";

/**
 * One question of the niche ("What cuisine do you serve?"), drawn for its
 * answer type: yes or no, one or several choices, a number, a link or
 * text. Controlled: the screen keeps the answers (in the draft of /create,
 * or autosaved to the profile).
 */

import type { WizardQuestionView } from "@/api/types";
import { Checkbox, Field, Fieldset, Input, Radio, Select, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import type { AnswerValue } from "@/lib/wizard/answers";

const EMPTY: AnswerValue = { text: "", choices: [] };

function Legend({ label, required }: { label: string; required: boolean }) {
  return (
    <>
      {label}
      {required ? (
        <span className="ms-0.5 text-danger" aria-hidden>
          *
        </span>
      ) : null}
    </>
  );
}

export function QuestionField({
  item,
  value = EMPTY,
  error,
  onChange,
}: {
  item: WizardQuestionView;
  value?: AnswerValue;
  error?: MessageKey;
  onChange: (value: AnswerValue) => void;
}) {
  const { t } = useI18n();
  const { question } = item;
  const errorText = error ? t(error) : undefined;
  const hint = question.hint ?? undefined;
  const setText = (text: string) => onChange({ text, choices: [] });
  const id = `tunnel-question-${question.key}`;

  switch (question.answer_type) {
    case "yes_no":
      return (
        <Fieldset legend={<Legend label={question.label} required={question.is_required} />} hint={hint} error={errorText}>
          <div className="flex gap-6">
            {(["yes", "no"] as const).map((option) => (
              <Radio
                key={option}
                name={id}
                id={`${id}-${option}`}
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
        <Fieldset legend={<Legend label={question.label} required={question.is_required} />} hint={hint} error={errorText}>
          <div className="grid gap-2 sm:grid-cols-2">
            {(question.choices ?? []).map((choice) => (
              <Checkbox
                key={choice.key}
                id={`${id}-${choice.key}`}
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
              required={false}
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
            <Textarea {...control} required={false} rows={3} value={value.text} maxLength={4000} onChange={(event) => setText(event.target.value)} />
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
