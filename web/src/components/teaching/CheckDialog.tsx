"use client";

/**
 * Writing one of the owner's checks: the customer's question (asked word
 * for word), what the answer must do and, when it must (not) mention
 * something, the words. Used for a new check, a changed one and "Save as a
 * check" from a fixed answer, a bad rating or a question without an answer.
 * A new check written here takes the language of its question unless the
 * owner picks one. Once saved, the dialog offers "Check now": one test
 * conversation with what customers get now, its outcome shown right there.
 */

import { useState, type FormEvent } from "react";

import { describeError } from "@/api/errors";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconCheckCircle } from "@/components/icons";
import { Alert, Button, Field, Input, Modal, Select, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import type { CheckView, Expectation } from "@/lib/teaching";
import {
  AUTO_LANGUAGE,
  CHECK_QUESTION_MAX_LENGTH,
  checkBody,
  checkChanges,
  checkProblems,
  EXPECTATION_LABELS,
  EXPECTATIONS,
  EXPECTED_TEXT_MAX_LENGTH,
  needsExpectedText,
  type CheckForm,
} from "@/lib/teachingChecks";

import { CheckNowPanel } from "./CheckNowPanel";
import { useChecks } from "./useTeaching";

const ERROR_TEXTS = { conflict: "teaching.checks.conflict" } as const;

export function CheckDialog({
  open,
  initial,
  check,
  title,
  description,
  onClose,
  onSaved,
}: {
  open: boolean;
  /** What the form starts from. */
  initial: CheckForm;
  /** The check being changed; null for a new one. */
  check: CheckView | null;
  title: string;
  description?: string;
  onClose: () => void;
  onSaved?: (saved: CheckView) => void;
}) {
  const { t } = useI18n();
  const formId = "check-dialog-form";
  const [saved, setSaved] = useState<CheckView | null>(null);
  const close = () => {
    setSaved(null);
    onClose();
  };
  return (
    <Modal
      open={open}
      onClose={close}
      title={saved ? t("updates.checkNow.savedTitle") : title}
      description={saved ? undefined : description}
      footer={
        saved ? (
          <Button variant="secondary" onClick={close}>
            {t("teaching.fix.done")}
          </Button>
        ) : (
          <>
            <Button variant="secondary" onClick={close}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" form={formId}>
              {t("common.save")}
            </Button>
          </>
        )
      }
    >
      {open && saved ? (
        <div className="space-y-4">
          <p className="flex items-start gap-2 text-sm text-ink" role="status">
            <IconCheckCircle className="mt-0.5 size-5 shrink-0 text-success" aria-hidden />
            <span dir="auto" className="[overflow-wrap:anywhere]">
              {t(check ? "teaching.checks.changed" : "teaching.checks.created")}
            </span>
          </p>
          <CheckNowPanel checkId={saved.id} question={saved.question} />
        </div>
      ) : open ? (
        <CheckFields
          key={check?.id ?? initial.question}
          formId={formId}
          initial={initial}
          check={check}
          onSaved={(checkSaved) => {
            onSaved?.(checkSaved);
            setSaved(checkSaved);
          }}
        />
      ) : null}
    </Modal>
  );
}

function CheckFields({
  formId,
  initial,
  check,
  onSaved,
}: {
  formId: string;
  initial: CheckForm;
  check: CheckView | null;
  onSaved: (saved: CheckView) => void;
}) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const checks = useChecks(false);
  const [form, setForm] = useState<CheckForm>(initial);
  const [isSubmitted, setSubmitted] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const problems = isSubmitted ? checkProblems(form) : [];
  const languages = Array.from(new Set([...business.languages, form.language])).filter((language) => language !== AUTO_LANGUAGE);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    if (checkProblems(form).length > 0) {
      return;
    }
    setError(null);
    const result = check ? await checks.update.run(check.id, checkChanges(form)) : await checks.create.run(checkBody(form));
    if (!result.ok) {
      setError(result.error);
      return;
    }
    if (check) {
      checks.replace(result.data);
    }
    onSaved(result.data);
  };

  return (
    <form id={formId} onSubmit={(event) => void submit(event)} className="space-y-5" noValidate>
      {error ? <Alert tone="danger">{describeError(error, t, ERROR_TEXTS).title}</Alert> : null}
      <Field
        label={t("teaching.checks.question")}
        hint={t("teaching.checks.questionHint")}
        error={problems.includes("question") ? t("teaching.checks.questionProblem") : undefined}
        required
      >
        {(control) => (
          <Textarea
            {...control}
            rows={2}
            value={form.question}
            maxLength={CHECK_QUESTION_MAX_LENGTH}
            onChange={(event) => setForm({ ...form, question: event.target.value })}
          />
        )}
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("teaching.checks.expectation")}>
          {(control) => (
            <Select
              {...control}
              value={form.expectation}
              onChange={(event) => setForm({ ...form, expectation: event.target.value as Expectation })}
            >
              {EXPECTATIONS.map((expectation) => (
                <option key={expectation} value={expectation}>
                  {t(EXPECTATION_LABELS[expectation])}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("teaching.checks.language")}>
          {(control) => (
            <Select {...control} value={form.language} onChange={(event) => setForm({ ...form, language: event.target.value })}>
              {check === null ? <option value={AUTO_LANGUAGE}>{t("updates.language.auto")}</option> : null}
              {languages.map((language) => (
                <option key={language} value={language}>
                  {languageName(language, locale)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
      {needsExpectedText(form.expectation) ? (
        <Field
          label={t("teaching.checks.expectedText")}
          hint={t("teaching.checks.expectedTextHint")}
          error={problems.includes("expectedText") ? t("teaching.checks.expectedTextProblem") : undefined}
          required
        >
          {(control) => (
            <Input
              {...control}
              value={form.expectedText}
              maxLength={EXPECTED_TEXT_MAX_LENGTH}
              onChange={(event) => setForm({ ...form, expectedText: event.target.value })}
            />
          )}
        </Field>
      ) : null}
    </form>
  );
}
