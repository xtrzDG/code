"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import type { KnowledgeItemDetails, KnowledgeItemKind } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconPlus, IconTrash } from "@/components/icons";
import { Button, Field, Input, LoadingBlock, Select, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { businessPath } from "@/lib/navigation";
import {
  markOfferRowsSaved,
  newOfferRow,
  offerItemsPayload,
  offerKinds,
  offerRowFromItem,
  validateOfferRow,
  type OfferRow,
  type OfferRowErrors,
} from "@/lib/wizard";

import { NicheQuestions, useNicheAnswers } from "../NicheQuestions";
import { StepForm, StepSection } from "../StepForm";
import type { StepProps } from "../types";

const KIND_LABELS: Record<KnowledgeItemKind, MessageKey> = {
  faq: "onboarding.offer.kinds.faq",
  policy: "onboarding.offer.kinds.policy",
  menu_item: "onboarding.offer.kinds.menu_item",
  service: "onboarding.offer.kinds.service",
  room_type: "onboarding.offer.kinds.room_type",
  package: "onboarding.offer.kinds.package",
  vehicle: "onboarding.offer.kinds.vehicle",
  product: "onboarding.offer.kinds.product",
};

/** Step 3: what the business sells, with prices in its currency. */
export function OfferStep(props: StepProps) {
  const { t } = useI18n();
  if (!props.knowledge) {
    return <LoadingBlock label={t("common.loading")} />;
  }
  return <OfferStepForm {...props} knowledge={props.knowledge} />;
}

function OfferStepForm({
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
  const { business } = useBusiness();
  const currency = wizard.currency_code;
  const kinds = offerKinds(wizard.knowledge_kinds);
  const questions = step.questions ?? [];
  const answers = useNicheAnswers(questions, onChange);
  const sequence = useRef(0);

  const [rows, setRows] = useState<OfferRow[]>(() => {
    const existing = knowledge.filter((item) => kinds.includes(item.kind)).map((item) => offerRowFromItem(item, currency));
    return existing.length > 0 ? existing : [newOfferRow(kinds[0] ?? "service", "new-0")];
  });
  const [rowErrors, setRowErrors] = useState<Record<string, OfferRowErrors>>({});

  const updateRow = (key: string, patch: Partial<OfferRow>) => {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
    setRowErrors((current) => ({ ...current, [key]: {} }));
    onChange();
  };

  const addRow = () => {
    sequence.current += 1;
    setRows((current) => [...current, newOfferRow(kinds[0] ?? "service", `new-${sequence.current}`)]);
  };

  const submit = async (advance: boolean) => {
    const errors: Record<string, OfferRowErrors> = {};
    for (const row of rows) {
      const found = validateOfferRow(row, currency);
      if (Object.keys(found).length > 0) {
        errors[row.key] = found;
      }
    }
    setRowErrors(errors);
    if (Object.keys(errors).length > 0 || !answers.validate()) {
      return;
    }
    const result = await onSave({ items: offerItemsPayload(rows, currency), answers: answers.payload() }, { advance });
    if (result) {
      setRows((current) => markOfferRowsSaved(current, result.saved_knowledge_items ?? []));
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
      <StepSection title={t("onboarding.offer.title")} hint={t("onboarding.offer.hint", { currency })}>
        {rows.length === 0 ? <p className="text-sm text-ink-muted">{t("onboarding.offer.empty")}</p> : null}
        <ol className="space-y-4">
          {rows.map((row, index) => {
            const errors = rowErrors[row.key] ?? {};
            return (
              <li key={row.key} className="rounded-xl border border-line p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
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
                <div className="grid gap-4 md:grid-cols-6">
                  {kinds.length > 1 ? (
                    <Field label={t("onboarding.offer.kind")} className="md:col-span-2">
                      {(control) => (
                        <Select
                          {...control}
                          value={row.kind}
                          onChange={(event) => updateRow(row.key, { kind: event.target.value as KnowledgeItemKind })}
                        >
                          {kinds.map((kind) => (
                            <option key={kind} value={kind}>
                              {t(KIND_LABELS[kind])}
                            </option>
                          ))}
                        </Select>
                      )}
                    </Field>
                  ) : null}
                  <Field
                    label={t("onboarding.offer.itemTitle")}
                    error={errors.title && t(errors.title)}
                    className={kinds.length > 1 ? "md:col-span-4" : "md:col-span-6"}
                  >
                    {(control) => (
                      <Input
                        {...control}
                        value={row.title}
                        maxLength={300}
                        onChange={(event) => updateRow(row.key, { title: event.target.value })}
                      />
                    )}
                  </Field>
                  <Field label={t("onboarding.offer.itemBody")} optionalLabel={t("common.optional")} className="md:col-span-6">
                    {(control) => (
                      <Textarea
                        {...control}
                        rows={2}
                        value={row.body}
                        maxLength={8000}
                        onChange={(event) => updateRow(row.key, { body: event.target.value })}
                      />
                    )}
                  </Field>
                  <Field
                    label={t("onboarding.offer.price", { currency })}
                    error={errors.price && t(errors.price)}
                    className="md:col-span-3"
                  >
                    {(control) => (
                      <Input
                        {...control}
                        inputMode="decimal"
                        value={row.price}
                        onChange={(event) => updateRow(row.key, { price: event.target.value })}
                      />
                    )}
                  </Field>
                  <Field
                    label={t("onboarding.offer.duration")}
                    optionalLabel={t("common.optional")}
                    error={errors.duration && t(errors.duration)}
                    className="md:col-span-3"
                  >
                    {(control) => (
                      <Input
                        {...control}
                        inputMode="numeric"
                        value={row.duration}
                        onChange={(event) => updateRow(row.key, { duration: event.target.value })}
                      />
                    )}
                  </Field>
                </div>
              </li>
            );
          })}
        </ol>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="secondary" size="sm" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={addRow}>
            {t("onboarding.offer.addItem")}
          </Button>
          <Link href={businessPath(business.id, "knowledge")} className="text-sm font-medium text-accent hover:underline">
            {t("nav.knowledge")}
          </Link>
        </div>
      </StepSection>

      <NicheQuestions questions={questions} state={answers} />
    </StepForm>
  );
}
