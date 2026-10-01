"use client";

import { useRef, useState } from "react";

import type { KnowledgeItemDetails } from "@/api/types";
import { IconPlus, IconTrash } from "@/components/icons";
import { Button, Field, Input, LoadingBlock, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  cleanRules,
  faqPayload,
  faqRowFromItem,
  markFaqRowsSaved,
  newFaqRow,
  validateFaqRow,
  type FaqRow,
} from "@/lib/wizard";

import { NicheQuestions, useNicheAnswers } from "../NicheQuestions";
import { RuleListEditor } from "../RuleListEditor";
import { StepForm, StepSection } from "../StepForm";
import type { StepProps } from "../types";

/** Step 5: frequent questions, when to pass to a person, what never to do, tone. */
export function FaqStep(props: StepProps) {
  const { t } = useI18n();
  if (!props.knowledge) {
    return <LoadingBlock label={t("common.loading")} />;
  }
  return <FaqStepForm {...props} knowledge={props.knowledge} />;
}

function FaqStepForm({
  wizard,
  step,
  knowledge,
  canEdit,
  isSaving,
  isLastStep,
  onSave,
  onChange,
}: StepProps & { knowledge: KnowledgeItemDetails[] }) {
  const { t } = useI18n();
  const { profile } = wizard;
  const questions = step.questions ?? [];
  const answers = useNicheAnswers(questions, onChange);
  const sequence = useRef(0);

  const [rows, setRows] = useState<FaqRow[]>(() => {
    const existing = knowledge.filter((item) => item.kind === "faq").map(faqRowFromItem);
    return existing.length > 0 ? existing : [newFaqRow("new-0")];
  });
  const [rowErrors, setRowErrors] = useState<Record<string, { question?: MessageKey; answer?: MessageKey }>>({});
  // A profile saved for the first time starts from the niche's suggested rules.
  const [handoffRules, setHandoffRules] = useState<string[]>(() =>
    profile.is_saved || (profile.handoff_rules ?? []).length > 0 ? (profile.handoff_rules ?? []) : [...wizard.default_handoff_rules],
  );
  const [forbidden, setForbidden] = useState<string[]>(() =>
    profile.is_saved || (profile.forbidden ?? []).length > 0 ? (profile.forbidden ?? []) : [...wizard.default_forbidden_rules],
  );
  const [tone, setTone] = useState(profile.tone ?? "");

  const updateRow = (key: string, patch: Partial<FaqRow>) => {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
    setRowErrors((current) => ({ ...current, [key]: {} }));
    onChange();
  };

  const submit = async (advance: boolean) => {
    const errors: Record<string, { question?: MessageKey; answer?: MessageKey }> = {};
    for (const row of rows) {
      const found = validateFaqRow(row);
      if (found.question || found.answer) {
        errors[row.key] = found;
      }
    }
    setRowErrors(errors);
    if (Object.keys(errors).length > 0 || !answers.validate()) {
      return;
    }
    const result = await onSave(
      {
        faq: faqPayload(rows),
        handoff_rules: cleanRules(handoffRules),
        forbidden: cleanRules(forbidden),
        tone: tone.trim() || null,
        answers: answers.payload(),
      },
      { advance },
    );
    if (result) {
      setRows((current) => markFaqRowsSaved(current, result.saved_knowledge_items ?? []));
    }
  };

  return (
    <StepForm
      title={step.title}
      description={step.description}
      canEdit={canEdit}
      isSaving={isSaving}
      isLastStep={isLastStep}
      onSubmit={(advance) => void submit(advance)}
    >
      <StepSection title={t("onboarding.faq.title")} hint={t("onboarding.faq.hint")}>
        <ol className="space-y-4">
          {rows.map((row, index) => {
            const errors = rowErrors[row.key] ?? {};
            return (
              <li key={row.key} className="space-y-3 rounded-xl border border-line p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-medium tracking-wide text-ink-subtle uppercase">#{index + 1}</span>
                  {row.id === null ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`${t("common.remove")} #${index + 1}`}
                      onClick={() => setRows((current) => current.filter((item) => item.key !== row.key))}
                    >
                      <IconTrash className="size-4" aria-hidden />
                    </Button>
                  ) : null}
                </div>
                <Field label={t("onboarding.faq.question")} error={errors.question && t(errors.question)}>
                  {(control) => (
                    <Input
                      {...control}
                      value={row.question}
                      maxLength={300}
                      onChange={(event) => updateRow(row.key, { question: event.target.value })}
                    />
                  )}
                </Field>
                <Field label={t("onboarding.faq.answer")} error={errors.answer && t(errors.answer)}>
                  {(control) => (
                    <Textarea
                      {...control}
                      rows={2}
                      value={row.answer}
                      maxLength={8000}
                      onChange={(event) => updateRow(row.key, { answer: event.target.value })}
                    />
                  )}
                </Field>
              </li>
            );
          })}
        </ol>
        <Button
          variant="secondary"
          size="sm"
          leadingIcon={<IconPlus className="size-4" aria-hidden />}
          onClick={() => {
            sequence.current += 1;
            setRows((current) => [...current, newFaqRow(`new-${sequence.current}`)]);
          }}
        >
          {t("onboarding.faq.addEntry")}
        </Button>
      </StepSection>

      <StepSection title={t("onboarding.faq.handoffRules")} hint={t("onboarding.faq.handoffHint")}>
        <RuleListEditor
          label={t("onboarding.faq.handoffRules")}
          rules={handoffRules}
          suggestions={wizard.default_handoff_rules}
          onChange={(next) => {
            setHandoffRules(next);
            onChange();
          }}
        />
      </StepSection>

      <StepSection title={t("onboarding.faq.forbidden")} hint={t("onboarding.faq.forbiddenHint")}>
        <RuleListEditor
          label={t("onboarding.faq.forbidden")}
          rules={forbidden}
          suggestions={wizard.default_forbidden_rules}
          onChange={(next) => {
            setForbidden(next);
            onChange();
          }}
        />
      </StepSection>

      <Field label={t("onboarding.faq.tone")}>
        {(control) => (
          <Input
            {...control}
            value={tone}
            maxLength={200}
            placeholder={t("onboarding.faq.tonePlaceholder")}
            onChange={(event) => {
              setTone(event.target.value);
              onChange();
            }}
          />
        )}
      </Field>

      <NicheQuestions questions={questions} state={answers} />
    </StepForm>
  );
}
