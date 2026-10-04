"use client";

/**
 * The fields of "Fix this answer": what should change (a question's
 * answer, a price, the opening hours, a rule) and what is right, plus the
 * answer as the customer saw it with what the assistant knows now.
 */

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Field, Fieldset, Input, Radio, Select, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { MONEY_INPUT_MESSAGES } from "@/lib/format";
import {
  CORRECTION_SCOPES,
  isPriceScope,
  SCOPE_LABELS,
  type CorrectionDraft,
  type CorrectionForm,
  type CorrectionProblem,
  type CorrectionScope,
} from "@/lib/teaching";

const QUESTION_LABELS = {
  faq: "teaching.fix.question",
  price: "teaching.fix.itemName",
  hours: "teaching.fix.hoursTitle",
  rule: "teaching.fix.ruleTitle",
} as const satisfies Record<CorrectionScope, string>;

/** The customer's question, the answer and the fact behind it. */
export function AnswerContext({ draft }: { draft: CorrectionDraft }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const fact = draft.current_fact ?? null;
  return (
    <dl className="space-y-3 rounded-2xl border border-line bg-surface-muted/60 p-4 text-sm">
      <div>
        <dt className="text-xs font-medium text-ink-subtle">{t("teaching.fix.customerAsked")}</dt>
        <dd dir="auto" className="mt-0.5 text-ink">
          {draft.question ?? <span className="text-ink-muted italic">{t("teaching.fix.noQuestion")}</span>}
        </dd>
      </div>
      <div>
        <dt className="text-xs font-medium text-ink-subtle">{t("teaching.fix.assistantAnswered")}</dt>
        <dd dir="auto" className="mt-0.5 line-clamp-4 whitespace-pre-wrap text-ink-muted">
          {draft.answer}
        </dd>
      </div>
      {fact ? (
        <div>
          <dt className="text-xs font-medium text-ink-subtle">{t("teaching.fix.currentFact")}</dt>
          <dd dir="auto" className="mt-0.5 text-ink">
            <span className="font-medium">{fact.title}</span>
            {fact.price_minor !== null && fact.price_minor !== undefined
              ? ` · ${format.money(fact.price_minor, fact.currency_code ?? undefined)}`
              : ""}
            {fact.body ? <span className="mt-0.5 block text-ink-muted">{fact.body}</span> : null}
          </dd>
        </div>
      ) : null}
    </dl>
  );
}

export function CorrectionFields({
  draft,
  form,
  problems,
  onChange,
}: {
  draft: CorrectionDraft;
  form: CorrectionForm;
  problems: readonly CorrectionProblem[];
  onChange: (form: CorrectionForm) => void;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const fact = draft.current_fact ?? null;
  const pricedFact = fact && fact.price_minor !== null && fact.price_minor !== undefined ? fact : null;
  const isPrice = isPriceScope(form.scope);
  const asksName = !isPrice || form.itemId === null;
  const priceProblem = problems.find((problem) => problem !== "question" && problem !== "answer");

  return (
    <div className="space-y-5">
      <Fieldset legend={t("teaching.fix.scopeLabel")}>
        <div className="grid gap-3 sm:grid-cols-2">
          {CORRECTION_SCOPES.map((scope) => (
            <Radio
              key={scope}
              id={`correction-scope-${scope}`}
              name="correction-scope"
              checked={form.scope === scope}
              onChange={() =>
                onChange({ ...form, scope, itemId: scope === "price" && pricedFact ? pricedFact.knowledge_item_id : null })
              }
              label={t(SCOPE_LABELS[scope])}
              description={t(`teaching.fix.scopeHints.${scope}`)}
            />
          ))}
        </div>
      </Fieldset>

      {isPrice && pricedFact ? (
        <Field label={t("teaching.fix.item")}>
          {(control) => (
            <Select
              {...control}
              value={form.itemId ?? ""}
              onChange={(event) => onChange({ ...form, itemId: event.target.value || null })}
            >
              <option value={pricedFact.knowledge_item_id}>{pricedFact.title}</option>
              <option value="">{t("teaching.fix.newItem")}</option>
            </Select>
          )}
        </Field>
      ) : null}

      {asksName ? (
        <Field
          label={t(QUESTION_LABELS[form.scope])}
          hint={form.scope === "faq" ? t("teaching.fix.questionHint") : undefined}
          error={problems.includes("question") ? t("teaching.fix.problems.question") : undefined}
          required
        >
          {(control) => (
            <Input {...control} value={form.question} dir="auto" onChange={(event) => onChange({ ...form, question: event.target.value })} />
          )}
        </Field>
      ) : null}

      {isPrice ? (
        <Field
          label={`${t("teaching.fix.price")} (${business.currency_code})`}
          error={
            priceProblem === undefined
              ? undefined
              : priceProblem === "price"
                ? t("teaching.fix.problems.price")
                : t(MONEY_INPUT_MESSAGES[priceProblem])
          }
          required
        >
          {(control) => (
            <Input
              {...control}
              inputMode="decimal"
              value={form.price}
              onChange={(event) => onChange({ ...form, price: event.target.value })}
            />
          )}
        </Field>
      ) : null}

      {!isPrice || form.itemId === null ? (
        <Field
          label={isPrice ? t("teaching.fix.priceDescription") : t("teaching.fix.answer")}
          hint={isPrice ? undefined : t("teaching.fix.answerHint")}
          error={problems.includes("answer") ? t("teaching.fix.problems.answer") : undefined}
          required={!isPrice}
        >
          {(control) => (
            <Textarea {...control} rows={3} value={form.answer} onChange={(event) => onChange({ ...form, answer: event.target.value })} />
          )}
        </Field>
      ) : null}
    </div>
  );
}
