"use client";

/**
 * Step 1, "What's your business called?": the name, the kind of business
 * (cards; fixed once the business exists) and the one or two things every
 * customer of that kind asks (the niche's required questions about the
 * business). Checked on Continue; the screen around saves. In the edit
 * mode (Assistant → Business profile) there is no Continue: the screen
 * passes the problems of what is typed (`problems`), every question of the
 * section is asked, and `extra` holds the section's other fields.
 */

import { useState, type ReactNode } from "react";

import type { NicheSummaryView, WizardQuestionView } from "@/api/types";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { Alert, ErrorState, Field, Input, LoadingRegion, SkeletonText } from "@/components/ui";
import type { ApiError } from "@/api/errors";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { answerProblems } from "@/lib/tunnel/questions";
import type { AnswerValues } from "@/lib/wizard/answers";

import { NicheCards } from "../fields/NicheCards";
import { QuestionField } from "../fields/QuestionField";
import { StepScreen, type StepActions } from "../StepScreen";
import type { StepMode } from "../stepMode";

const MAX_BUSINESS_NAME = 120;

export interface BusinessForm {
  name: string;
  nicheKey: string;
  answers: AnswerValues;
}

export interface BusinessProblems {
  name?: MessageKey;
  niche?: MessageKey;
  answers: Record<string, MessageKey>;
}

export interface BusinessStepProps {
  form: BusinessForm;
  onChange: (form: BusinessForm) => void;
  niches: { data?: readonly NicheSummaryView[]; error: ApiError | null; reload: () => void };
  /** The chosen kind's required questions about the business; null while they load. */
  questions: readonly WizardQuestionView[] | null;
  /** The business exists: its kind is shown, not chosen. */
  isNicheFixed: boolean;
  onSubmit: () => void;
  onBack?: () => void;
  isBusy?: boolean;
  mode?: StepMode;
  /** The edit mode's problems, shown as the owner types (the tunnel shows its own on Continue). */
  problems?: BusinessProblems;
  /** More of the section under the questions (the edit mode's links). */
  extra?: ReactNode;
}

export function BusinessStep({ form, onChange, niches, questions, isNicheFixed, onSubmit, onBack, isBusy, mode = "tunnel", problems, extra }: BusinessStepProps) {
  const { t } = useI18n();
  const [checked, setErrors] = useState<BusinessProblems>({ answers: {} });
  const errors = problems ?? checked;
  const isEdit = mode === "edit";
  const niche = niches.data?.find((item) => item.key === form.nicheKey);
  const shownNiches = isNicheFixed ? (niche ? [niche] : []) : (niches.data ?? []);

  const submit = () => {
    const found = {
      name: form.name.trim() === "" ? ("tunnelBusiness.business.errors.name" as const) : undefined,
      niche: form.nicheKey === "" ? ("tunnelBusiness.business.errors.kind" as const) : undefined,
      answers: questions ? answerProblems(questions, form.answers) : {},
    };
    setErrors(found);
    if (!found.name && !found.niche && Object.keys(found.answers).length === 0 && questions !== null) {
      onSubmit();
    }
  };

  return (
    <StepScreen
      step="business"
      mode={mode}
      title={isEdit ? t("profileEdit.sections.business.title") : t("tunnelBusiness.business.title")}
      text={isEdit ? t("profileEdit.sections.business.text") : t("tunnelBusiness.business.text")}
      actions={(isEdit ? {} : { onContinue: submit, onBack, isBusy }) satisfies StepActions}
      aside={isEdit ? undefined : <LanguageSwitcher className="justify-center sm:hidden" />}
    >
      <div className="space-y-10">
        <Field label={t("tunnelBusiness.business.name")} required error={errors.name && t(errors.name)}>
          {(control) => (
            <Input
              {...control}
              value={form.name}
              maxLength={MAX_BUSINESS_NAME}
              autoComplete="organization"
              placeholder={t("tunnelBusiness.business.namePlaceholder")}
              className="h-14 text-lg"
              onChange={(event) => {
                onChange({ ...form, name: event.target.value });
                setErrors((current) => ({ ...current, name: undefined }));
              }}
            />
          )}
        </Field>

        {niches.error && !niches.data ? (
          <ErrorState error={niches.error} onRetry={niches.reload} />
        ) : !niches.data ? (
          <LoadingRegion label={t("common.loading")}>
            <SkeletonText lines={4} />
          </LoadingRegion>
        ) : (
          <div className="space-y-3">
            <NicheCards
              niches={shownNiches}
              value={form.nicheKey}
              legend={t("tunnelBusiness.business.kindTitle")}
              hint={isNicheFixed ? t("tunnelBusiness.business.kindFixed") : t("tunnelBusiness.business.kindHint")}
              error={errors.niche && t(errors.niche)}
              onChange={(nicheKey) => {
                if (!isNicheFixed) {
                  onChange({ ...form, nicheKey, answers: {} });
                  setErrors((current) => ({ ...current, niche: undefined, answers: {} }));
                }
              }}
            />
            {niche?.requires_legal_review ? <Alert tone="warning">{t("tunnelBusiness.business.legalReview")}</Alert> : null}
          </div>
        )}

        {form.nicheKey && questions === null ? (
          <LoadingRegion label={t("common.loading")}>
            <SkeletonText lines={2} />
          </LoadingRegion>
        ) : questions && questions.length > 0 ? (
          <section className="space-y-5 rounded-2xl border border-line bg-surface/80 p-5 backdrop-blur-sm sm:p-6">
            <h2 className="text-base font-semibold text-ink">
              {isEdit ? t("profileEdit.business.questionsTitle") : t("tunnelBusiness.business.detailsTitle")}
            </h2>
            {questions.map((item) => (
              <QuestionField
                key={item.question.key}
                item={item}
                value={form.answers[item.question.key]}
                error={errors.answers[item.question.key]}
                onChange={(value) => {
                  onChange({ ...form, answers: { ...form.answers, [item.question.key]: value } });
                  setErrors((current) => {
                    const { [item.question.key]: _cleared, ...rest } = current.answers;
                    return { ...current, answers: rest };
                  });
                }}
              />
            ))}
          </section>
        ) : null}
        {extra}
      </div>
    </StepScreen>
  );
}
