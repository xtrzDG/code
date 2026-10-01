"use client";

import Link from "next/link";
import { useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { Field, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { NicheQuestions, useNicheAnswers } from "../NicheQuestions";
import { StepForm, StepSection } from "../StepForm";
import type { StepProps } from "../types";

/** Step 1: the niche, the customer languages and the language of the answers. */
export function NicheStep({ wizard, step, canEdit, isSaving, isLastStep, onSave, onChange }: StepProps) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const questions = step.questions ?? [];
  const answers = useNicheAnswers(questions, onChange);
  const [answersLanguage, setAnswersLanguage] = useState(wizard.profile.answers_language);

  const languageChoices = [
    ...new Set([wizard.profile.answers_language, business.owner_language, ...wizard.customer_languages]),
  ];

  return (
    <StepForm
      title={step.title}
      description={step.description}
      canEdit={canEdit}
      isSaving={isSaving}
      isLastStep={isLastStep}
      onSubmit={(advance) => {
        if (!answers.validate()) {
          return;
        }
        void onSave({ answers_language: answersLanguage, answers: answers.payload() }, { advance });
      }}
    >
      <StepSection title={t("onboarding.niche.niche")}>
        <div className="rounded-xl border border-line bg-surface-muted/50 p-4">
          <p className="font-medium text-ink">{wizard.niche.name}</p>
          <p className="mt-1 text-sm text-ink-muted">{wizard.niche.description}</p>
        </div>
      </StepSection>

      <StepSection title={t("onboarding.niche.customerLanguages")}>
        <div className="flex flex-wrap items-center gap-2">
          {wizard.customer_languages.map((tag) => (
            <span key={tag} lang={tag} className="rounded-full bg-surface-muted px-3 py-1 text-sm text-ink">
              {languageName(tag, tag)}
              {tag === wizard.default_language ? " ★" : ""}
            </span>
          ))}
          <Link href={businessPath(business.id, "settings")} className="text-sm font-medium text-accent hover:underline">
            {t("onboarding.niche.changeInSettings")}
          </Link>
        </div>
      </StepSection>

      <Field label={t("onboarding.niche.answersLanguage")} hint={t("onboarding.niche.answersLanguageHint")}>
        {(control) => (
          <Select
            {...control}
            value={answersLanguage}
            onChange={(event) => {
              setAnswersLanguage(event.target.value);
              onChange();
            }}
            className="max-w-xs"
          >
            {languageChoices.map((tag) => (
              <option key={tag} value={tag}>
                {languageName(tag, locale)}
              </option>
            ))}
          </Select>
        )}
      </Field>

      <NicheQuestions questions={questions} state={answers} />
    </StepForm>
  );
}
