"use client";

import { useId, useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import type { KnowledgeItemDetails, KnowledgeItemKind } from "@/api/types";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Button, Checkbox, Field, Fieldset, Input, Modal, Select, Textarea, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { languageName } from "@/lib/format";
import {
  emptyKnowledgeForm,
  isEmptyPatch,
  knowledgeCreateBody,
  knowledgeFormFromItem,
  knowledgePatchBody,
  MAX_BODY_LENGTH,
  MAX_TITLE_LENGTH,
  validateKnowledgeForm,
  type KnowledgeForm,
  type KnowledgeFormErrors,
  type KnowledgeFormSource,
  type KnowledgeItemCreateBody,
  type KnowledgeItemPatchBody,
} from "@/lib/knowledge/form";
import { kindHasPrice } from "@/lib/knowledge/kinds";
import { isBookableKind } from "@/lib/offers";

import { KIND_LABELS } from "./hooks";
import { OfferFields } from "./OfferFields";
import { PriceFields } from "./PriceFields";

/** What the editor opens with: a new item of a kind, or an existing item. */
export type KnowledgeEditorTarget =
  | { mode: "create"; kind: KnowledgeItemKind }
  | { mode: "edit"; id: string; item: KnowledgeFormSource };

const TITLE_LABELS: Partial<Record<KnowledgeItemKind, MessageKey>> = {
  faq: "knowledge.form.question",
  policy: "knowledge.form.rule",
};

const BODY_LABELS: Partial<Record<KnowledgeItemKind, MessageKey>> = {
  faq: "knowledge.form.answer",
  policy: "knowledge.form.ruleDetails",
};

/**
 * Create or edit one knowledge item in a dialog. Prices are typed in major
 * units of the business currency; an edit sends only the changed fields.
 */
export function KnowledgeItemEditor({
  target,
  kinds,
  showActiveToggle = true,
  onClose,
  onSaved,
}: {
  target: KnowledgeEditorTarget;
  kinds: readonly KnowledgeItemKind[];
  /** False for imported drafts: they are switched on by confirming the import. */
  showActiveToggle?: boolean;
  onClose: () => void;
  onSaved: (item: KnowledgeItemDetails) => void;
}) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const currency = format.currency;
  const formId = useId();

  const [initial] = useState<KnowledgeForm>(() =>
    target.mode === "create" ? emptyKnowledgeForm(target.kind) : knowledgeFormFromItem(target.item, currency),
  );
  const [form, setForm] = useState<KnowledgeForm>(initial);
  const [errors, setErrors] = useState<KnowledgeFormErrors>({});

  // What the assistant knows changed: the changes customers do not get yet are read again,
  // and so are the resources (a performer list changes their services too) and the offers of bookings.
  const settled = {
    invalidate: [queryKeys.assistant.pendingAll(business.id), queryKeys.resources.list(business.id)],
    stale: [queryKeys.knowledge.offers(business.id)],
  };
  const create = useMutation(
    (body: KnowledgeItemCreateBody) =>
      api.POST("/v1/businesses/{business_id}/knowledge", {
        params: { path: { business_id: business.id }, query: { language: locale } },
        body,
      }),
    settled,
  );
  const update = useMutation(
    (itemId: string, body: KnowledgeItemPatchBody) =>
      api.PATCH("/v1/businesses/{business_id}/knowledge/{item_id}", {
        params: { path: { business_id: business.id, item_id: itemId }, query: { language: locale } },
        body,
      }),
    settled,
  );

  const change = (patch: Partial<KnowledgeForm>) => {
    setForm((current) => ({ ...current, ...patch }));
    setErrors((current) => {
      const next = { ...current };
      for (const key of Object.keys(patch)) {
        delete next[key as keyof KnowledgeFormErrors];
      }
      return next;
    });
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const found = validateKnowledgeForm(form, currency);
    setErrors(found);
    if (Object.keys(found).length > 0) {
      return;
    }
    if (target.mode === "create") {
      const result = await create.run(knowledgeCreateBody(form, currency));
      if (result.ok) {
        toast.success(t("knowledge.form.created"));
        onSaved(result.data);
      }
      return;
    }
    const patch = knowledgePatchBody(form, initial, currency);
    if (isEmptyPatch(patch)) {
      onClose();
      return;
    }
    const result = await update.run(target.id, patch);
    if (result.ok) {
      toast.success(t("common.saved"));
      onSaved(result.data);
    }
  };

  const isPending = create.isPending || update.isPending;
  const showPrice = kindHasPrice(form.kind);
  const kindOptions = kinds.includes(form.kind) ? kinds : [form.kind, ...kinds];

  return (
    <Modal
      open
      onClose={() => {
        if (!isPending) {
          onClose();
        }
      }}
      size="lg"
      title={target.mode === "create" ? t("knowledge.form.createTitle") : t("knowledge.form.editTitle")}
      description={t("knowledge.form.description")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isPending}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" form={formId} isLoading={isPending} loadingText={t("common.saving")}>
            {target.mode === "create" ? t("knowledge.form.add") : t("common.save")}
          </Button>
        </>
      }
    >
      <form id={formId} onSubmit={(event) => void submit(event)} noValidate className="grid gap-4 sm:grid-cols-6">
        <Field label={t("knowledge.form.kind")} className="sm:col-span-2">
          {(control) => (
            <Select
              {...control}
              value={form.kind}
              onChange={(event) => change({ kind: event.target.value as KnowledgeItemKind })}
            >
              {kindOptions.map((kind) => (
                <option key={kind} value={kind}>
                  {t(KIND_LABELS[kind])}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field
          label={t(TITLE_LABELS[form.kind] ?? "knowledge.form.title")}
          error={errors.title && t(errors.title)}
          required
          className="sm:col-span-4"
        >
          {(control) => (
            <Input
              {...control}
              dir="auto"
              value={form.title}
              maxLength={MAX_TITLE_LENGTH}
              autoFocus
              onChange={(event) => change({ title: event.target.value })}
            />
          )}
        </Field>
        <Field
          label={t(BODY_LABELS[form.kind] ?? "knowledge.form.body")}
          optionalLabel={form.kind === "faq" ? undefined : t("common.optional")}
          required={form.kind === "faq"}
          error={errors.body && t(errors.body)}
          className="sm:col-span-6"
        >
          {(control) => (
            <Textarea
              {...control}
              dir="auto"
              rows={4}
              value={form.body}
              maxLength={MAX_BODY_LENGTH}
              onChange={(event) => change({ body: event.target.value })}
            />
          )}
        </Field>
        {showPrice ? <PriceFields form={form} errors={errors} currency={currency} change={change} /> : null}
        {isBookableKind(form.kind) ? <OfferFields form={form} errors={errors} currency={currency} change={change} /> : null}
        {business.languages.length > 1 ? (
          <Fieldset legend={t("knowledge.form.languages")} hint={t("knowledge.form.languagesHint")} className="sm:col-span-6">
            <div className="flex flex-wrap gap-x-5 gap-y-2">
              {business.languages.map((language) => (
                <Checkbox
                  key={language}
                  id={`${formId}-language-${language}`}
                  label={languageName(language, locale)}
                  checked={form.languages.includes(language)}
                  onChange={(event) =>
                    change({
                      languages: event.target.checked
                        ? [...form.languages, language]
                        : form.languages.filter((item) => item !== language),
                    })
                  }
                />
              ))}
            </div>
          </Fieldset>
        ) : null}
        {showActiveToggle ? (
          <div className="sm:col-span-6">
            <Checkbox
              id={`${formId}-active`}
              label={t("knowledge.form.active")}
              description={t("knowledge.form.activeHint")}
              checked={form.isActive}
              onChange={(event) => change({ isActive: event.target.checked })}
            />
          </div>
        ) : null}
      </form>
    </Modal>
  );
}
