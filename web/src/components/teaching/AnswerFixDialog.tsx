"use client";

/**
 * "Fix this answer" (owners): opens on an assistant answer with the
 * customer's question, the kind of fix it most likely needs and what the
 * assistant knows now. Saving creates or updates a knowledge item linked
 * to the answer, which reaches customers with the next "Apply changes";
 * then the owner may save the same question as a check.
 */

import { useState, type FormEvent } from "react";

import { describeError } from "@/api/errors";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconCheckCircle } from "@/components/icons";
import { Alert, Button, ErrorState, LoadingRegion, Modal, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { checkFormFromCorrection } from "@/lib/teachingChecks";
import {
  correctionBody,
  correctionFormOf,
  correctionProblems,
  guardReasonKeys,
  type CorrectionDraft,
  type CorrectionForm,
  type CorrectionResult,
} from "@/lib/teaching";

import { CheckDialog } from "./CheckDialog";
import { AnswerContext, CorrectionFields } from "./CorrectionFields";
import { useCorrectAnswer, useCorrectionDraft } from "./useTeaching";

const FORM_ID = "answer-fix-form";

export function AnswerFixDialog({
  conversationId,
  messageId,
  onClose,
}: {
  conversationId: string;
  /** The answer to fix; null: closed. */
  messageId: string | null;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const draft = useCorrectionDraft(conversationId, messageId);
  const [result, setResult] = useState<CorrectionResult | null>(null);
  const [isSavingCheck, setSavingCheck] = useState(false);
  const close = () => {
    setResult(null);
    onClose();
  };

  return (
    <>
      <Modal
        open={messageId !== null && !isSavingCheck}
        onClose={close}
        size="lg"
        title={result ? t("teaching.fix.savedTitle") : t("teaching.fix.title")}
        description={result ? undefined : t("teaching.fix.description")}
        footer={
          result ? (
            <>
              <Button variant="secondary" onClick={close}>
                {t("teaching.fix.done")}
              </Button>
              <Button onClick={() => setSavingCheck(true)}>{t("teaching.fix.saveAsCheck")}</Button>
            </>
          ) : (
            <>
              <Button variant="secondary" onClick={close}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" form={FORM_ID} disabled={!draft.data}>
                {t("teaching.fix.save")}
              </Button>
            </>
          )
        }
      >
        {result ? (
          <div className="flex items-start gap-3" role="status">
            <IconCheckCircle className="mt-0.5 size-6 shrink-0 text-success" aria-hidden />
            <div className="space-y-1 text-sm">
              <p className="font-medium text-ink">{t(result.is_new ? "teaching.fix.saved" : "teaching.fix.updated")}</p>
              <p className="text-ink-muted">{t("teaching.fix.savedDescription")}</p>
            </div>
          </div>
        ) : draft.data && messageId ? (
          <FixForm
            key={messageId}
            conversationId={conversationId}
            messageId={messageId}
            draft={draft.data}
            onSaved={setResult}
          />
        ) : draft.error ? (
          <ErrorState error={draft.error} onRetry={draft.reload} />
        ) : (
          <LoadingRegion label={t("teaching.fix.loading")}>
            <SkeletonText lines={6} />
          </LoadingRegion>
        )}
      </Modal>
      {result ? (
        <CheckDialog
          open={isSavingCheck}
          initial={checkFormFromCorrection(result, business.currency_code)}
          check={null}
          title={t("teaching.checks.saveTitle")}
          description={t("teaching.checks.saveDescription")}
          onClose={() => {
            setSavingCheck(false);
            close();
          }}
        />
      ) : null}
    </>
  );
}

function FixForm({
  conversationId,
  messageId,
  draft,
  onSaved,
}: {
  conversationId: string;
  messageId: string;
  draft: CorrectionDraft;
  onSaved: (result: CorrectionResult) => void;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const correct = useCorrectAnswer(conversationId);
  const [form, setForm] = useState<CorrectionForm>(() => correctionFormOf(draft));
  const [isSubmitted, setSubmitted] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const problems = isSubmitted ? correctionProblems(form, business.currency_code) : [];
  const guardReasons = guardReasonKeys(draft.guard_reasons);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    if (correctionProblems(form, business.currency_code).length > 0) {
      return;
    }
    setError(null);
    const saved = await correct.run(messageId, correctionBody(form, business.currency_code));
    if (!saved.ok) {
      setError(saved.error);
      return;
    }
    // The dialog itself turns into the saved state: no toast besides it.
    onSaved(saved.data);
  };

  return (
    <form id={FORM_ID} onSubmit={(event) => void submit(event)} className="space-y-5" noValidate aria-busy={correct.isPending || undefined}>
      {error ? <Alert tone="danger">{describeError(error, t).title}</Alert> : null}
      <AnswerContext draft={draft} />
      {guardReasons.length > 0 ? (
        <p className="text-sm text-warning">
          {t("teaching.fix.guardHeld", { reasons: guardReasons.map((reason) => t(reason)).join(", ") })}
        </p>
      ) : null}
      {draft.is_corrected ? <Alert tone="info">{t("teaching.fix.alreadyCorrected")}</Alert> : null}
      <CorrectionFields draft={draft} form={form} problems={problems} onChange={setForm} />
    </form>
  );
}
