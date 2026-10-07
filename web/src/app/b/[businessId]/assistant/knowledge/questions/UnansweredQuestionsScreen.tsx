"use client";

import { useId, useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useMutation } from "@/api/useMutation";
import type { Schema } from "@/api/types";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCheck } from "@/components/icons";
import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingRegion,
  Modal,
  SkeletonRows,
  Textarea,
  useToast,
} from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { languageName } from "@/lib/format";
import { MAX_BODY_LENGTH, MAX_TITLE_LENGTH } from "@/lib/knowledge/form";


type UnansweredQuestion = Schema<"UnansweredQuestionDetails">;
type AnsweredQuestionResult = Schema<"AnsweredQuestionResult">;

const PAGE_SIZE = 25;

/**
 * Knowledge -> Questions without an answer: what customers asked and the
 * assistant could not answer, most asked first, paged and filtered by the API.
 */
export function UnansweredQuestionsScreen() {
  const { t, tp, locale } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const [includeResolved, setIncludeResolved] = useState(false);
  const [includeSandbox, setIncludeSandbox] = useState(false);
  const [answering, setAnswering] = useState<UnansweredQuestion | null>(null);

  const questions = useCursorPage<UnansweredQuestion, Schema<"UnansweredQuestionPage">>(
    queryKeys.knowledge.questions(business.id, includeResolved, includeSandbox),
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/unanswered-questions", {
        params: {
          path: { business_id: business.id },
          query: {
            include_resolved: includeResolved ? "true" : undefined,
            include_sandbox: includeSandbox ? "true" : undefined,
            limit: String(limit),
            cursor: cursor ?? undefined,
          },
        },
      }),
    { pageSize: PAGE_SIZE },
  );

  const list = questions.items ?? [];

  return (
    <div className="space-y-6">
      {!isOwner ? <Alert tone="info">{t("knowledge.questions.ownerOnly")}</Alert> : null}

      <Card padded={false}>
        <div className="flex flex-col gap-3 border-b border-line px-4 py-4 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:px-6">
          <p className="text-sm text-ink-muted">{t("knowledge.questions.intro")}</p>
          <div className="flex flex-wrap gap-x-5 gap-y-2">
            <Checkbox
              id="questions-include-resolved"
              label={t("knowledge.questions.includeResolved")}
              checked={includeResolved}
              onChange={(event) => setIncludeResolved(event.target.checked)}
            />
            <Checkbox
              id="questions-include-sandbox"
              label={t("knowledge.questions.includeSandbox")}
              checked={includeSandbox}
              onChange={(event) => setIncludeSandbox(event.target.checked)}
            />
          </div>
        </div>

        {questions.isLoading ? (
          <LoadingRegion label={t("common.loading")}>
            <SkeletonRows rows={4} className="rounded-none border-0" />
          </LoadingRegion>
        ) : questions.error ? (
          <ErrorState error={questions.error} onRetry={questions.reload} />
        ) : list.length === 0 ? (
          <EmptyState
            icon={<IconCheck className="size-6" />}
            title={t("knowledge.questions.emptyTitle")}
            description={t("knowledge.questions.emptyDescription")}
          />
        ) : (
          <>
            <ul className="divide-y divide-line">
              {list.map((question) => (
                <li key={question.id} className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start sm:gap-6 sm:px-6">
                  <div className="min-w-0 flex-1 space-y-1.5">
                    <p className="font-medium break-words text-ink" dir="auto" data-user-content>
                      {question.question}
                    </p>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-subtle">
                      <span>{tp("knowledge.questions.asked", question.occurrence_count)}</span>
                      <span>{t("knowledge.questions.lastAsked", { date: format.dateTime(question.last_seen_at) })}</span>
                      <span>{languageName(question.language, locale)}</span>
                      {question.is_sandbox ? <Badge>{t("knowledge.questions.sandbox")}</Badge> : null}
                      {question.is_resolved ? <Badge tone="success">{t("knowledge.questions.answered")}</Badge> : null}
                    </div>
                  </div>
                  {isOwner && !question.is_resolved ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      aria-label={`${t("knowledge.questions.addAnswer")}: ${question.question}`}
                      onClick={() => setAnswering(question)}
                    >
                      {t("knowledge.questions.addAnswer")}
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
            {questions.hasMore ? (
              <div className="flex flex-col items-center gap-2 border-t border-line px-4 py-3 text-center sm:px-6">
                {questions.moreError ? (
                  <p className="text-sm text-danger" role="alert">
                    {t("knowledge.paging.failed")}
                  </p>
                ) : null}
                <Button variant="ghost" isLoading={questions.isLoadingMore} loadingText={t("common.loading")} onClick={questions.loadMore}>
                  {questions.moreError ? t("common.retry") : t("knowledge.paging.more")}
                </Button>
              </div>
            ) : null}
          </>
        )}
      </Card>

      {answering ? (
        <AnswerDialog
          key={answering.id}
          question={answering}
          onClose={() => setAnswering(null)}
          onAnswered={(result) => {
            questions.updateItems((items) =>
              includeResolved
                ? items.map((item) => (item.id === result.question.id ? result.question : item))
                : items.filter((item) => item.id !== result.question.id),
            );
            setAnswering(null);
          }}
        />
      ) : null}
    </div>
  );
}

function AnswerDialog({
  question,
  onClose,
  onAnswered,
}: {
  question: UnansweredQuestion;
  onClose: () => void;
  onAnswered: (result: AnsweredQuestionResult) => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const formId = useId();
  const [answer, setAnswer] = useState("");
  const [title, setTitle] = useState(question.question);
  const [errors, setErrors] = useState<{ answer?: MessageKey; title?: MessageKey }>({});

  const save = useMutation(
    (body: { answer: string; title: string | null }) =>
      api.POST("/v1/businesses/{business_id}/unanswered-questions/{question_id}/answer", {
        params: { path: { business_id: business.id, question_id: question.id } },
        body,
      }),
    // A new FAQ item: the items, the open-question counts and the assistant's checks follow.
    { stale: [queryKeys.knowledge.all(business.id), queryKeys.assistant.all(business.id)], invalidate: [queryKeys.dashboard.all(business.id)] },
  );

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const found = {
      ...(answer.trim() === "" ? { answer: "validation.required" as const } : {}),
      ...(title.trim().length > MAX_TITLE_LENGTH ? { title: "validation.tooLong" as const } : {}),
    };
    setErrors(found);
    if (Object.keys(found).length > 0) {
      return;
    }
    const cleanTitle = title.trim();
    const result = await save.run({
      answer: answer.trim(),
      title: cleanTitle === "" || cleanTitle === question.question.trim() ? null : cleanTitle,
    });
    if (result.ok) {
      toast.success(t("knowledge.questions.saved"), result.data.requires_reassembly ? t("knowledge.questions.savedHint") : undefined);
      onAnswered(result.data);
    }
  };

  return (
    <Modal
      open
      onClose={() => {
        if (!save.isPending) {
          onClose();
        }
      }}
      size="lg"
      title={t("knowledge.questions.answerTitle")}
      description={t("knowledge.questions.answerDescription")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={save.isPending}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" form={formId} isLoading={save.isPending} loadingText={t("common.saving")}>
            {t("knowledge.questions.saveAnswer")}
          </Button>
        </>
      }
    >
      <form id={formId} onSubmit={(event) => void submit(event)} noValidate className="space-y-4">
        <blockquote className="rounded-xl border-s-4 border-accent-solid bg-surface-muted px-4 py-3 text-sm break-words text-ink" dir="auto" data-user-content>
          {question.question}
        </blockquote>
        <Field label={t("knowledge.questions.answer")} hint={t("knowledge.questions.answerHint")} error={errors.answer && t(errors.answer)} required>
          {(control) => (
            <Textarea
              {...control}
              dir="auto"
              rows={5}
              autoFocus
              value={answer}
              maxLength={MAX_BODY_LENGTH}
              onChange={(event) => {
                setAnswer(event.target.value);
                setErrors((current) => ({ ...current, answer: undefined }));
              }}
            />
          )}
        </Field>
        <Field
          label={t("knowledge.questions.faqTitle")}
          hint={t("knowledge.questions.faqTitleHint")}
          optionalLabel={t("common.optional")}
          error={errors.title && t(errors.title)}
        >
          {(control) => (
            <Input
              {...control}
              dir="auto"
              value={title}
              maxLength={MAX_TITLE_LENGTH}
              onChange={(event) => setTitle(event.target.value)}
            />
          )}
        </Field>
      </form>
    </Modal>
  );
}
