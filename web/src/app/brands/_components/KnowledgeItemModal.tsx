"use client";

import { useState, type FormEvent } from "react";

import { Button, Checkbox, Field, Input, Modal, ModalFooter, Select, Textarea, useToast } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { useI18n } from "@/i18n/client";
import { currencyFractionDigits } from "@/lib/format";

import { parsePriceMinor, SHARED_KINDS, type BrandKnowledgeItem, type SharedKind } from "../_lib/brands";
import { useBrandKnowledgeActions, type KnowledgeBody } from "../_lib/useBrands";

const PRICED: readonly SharedKind[] = ["menu_item", "product"];

/** A new shared answer, or a change to one (its key stays). */
export function KnowledgeItemModal({
  brandId,
  item,
  currency,
  onClose,
}: {
  brandId: string;
  item: BrandKnowledgeItem | "new" | null;
  currency: string | null;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const isNew = item === "new";
  return (
    <Modal open={item !== null} onClose={onClose} title={isNew ? t("brands.knowledge.addTitle") : t("brands.knowledge.editTitle")}>
      {item !== null ? (
        <ItemForm key={isNew ? "new" : item.shared_key} brandId={brandId} item={isNew ? null : item} currency={currency} onClose={onClose} />
      ) : null}
    </Modal>
  );
}

function ItemForm({
  brandId,
  item,
  currency,
  onClose,
}: {
  brandId: string;
  item: BrandKnowledgeItem | null;
  currency: string | null;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { create, update } = useBrandKnowledgeActions(brandId);
  const digits = currency ? currencyFractionDigits(currency) : 2;
  const [kind, setKind] = useState<SharedKind>(item && (SHARED_KINDS as readonly string[]).includes(item.kind) ? (item.kind as SharedKind) : "faq");
  const [title, setTitle] = useState(item?.title ?? "");
  const [body, setBody] = useState(item?.body ?? "");
  const [price, setPrice] = useState(item?.price_minor != null ? String(item.price_minor / 10 ** digits) : "");
  const [isActive, setActive] = useState(item?.is_active ?? true);
  const [errors, setErrors] = useState<{ title?: boolean; price?: boolean }>({});
  const mutation = item ? update : create;
  const isPriced = PRICED.includes(kind);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const priceMinor = isPriced ? parsePriceMinor(price, digits) : null;
    const next = { title: title.trim() === "", price: priceMinor !== null && Number.isNaN(priceMinor) };
    if (next.title || next.price) {
      setErrors(next);
      return;
    }
    const payload: KnowledgeBody = {
      kind,
      title: title.trim(),
      body: body.trim() || null,
      price_minor: priceMinor,
      is_active: isActive,
      ...(item ? { shared_key: item.shared_key, languages: item.languages ?? [], tags: item.tags ?? [] } : {}),
    };
    const result = item ? await update.run(item.shared_key, payload) : await create.run(payload);
    if (result.ok) {
      toast.success(t("brands.knowledge.saved"));
      onClose();
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <Field label={t("brands.knowledge.kind")} required>
        {(control) => (
          <Select {...control} value={kind} onChange={(event) => setKind(event.target.value as SharedKind)}>
            {SHARED_KINDS.map((option) => (
              <option key={option} value={option}>
                {t(`brands.knowledge.kinds.${option}`)}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={t("brands.knowledge.question")} required error={errors.title ? t("brands.knowledge.errors.title") : undefined}>
        {(control) => (
          <Input
            {...control}
            value={title}
            dir="auto"
            maxLength={200}
            onChange={(event) => {
              setTitle(event.target.value);
              setErrors({});
            }}
          />
        )}
      </Field>
      <Field label={t("brands.knowledge.answer")} optionalLabel={t("common.optional")}>
        {(control) => <Textarea {...control} value={body} dir="auto" rows={4} maxLength={4000} onChange={(event) => setBody(event.target.value)} />}
      </Field>
      {isPriced ? (
        <Field
          label={currency ? `${t("brands.knowledge.price")} (${currency})` : t("brands.knowledge.price")}
          hint={t("brands.knowledge.priceHint")}
          optionalLabel={t("common.optional")}
          error={errors.price ? t("brands.knowledge.errors.price") : undefined}
        >
          {(control) => (
            <Input
              {...control}
              value={price}
              inputMode="decimal"
              dir="ltr"
              onChange={(event) => {
                setPrice(event.target.value);
                setErrors({});
              }}
            />
          )}
        </Field>
      ) : null}
      <Checkbox id="brand-knowledge-active" checked={isActive} onChange={(event) => setActive(event.target.checked)} label={t("brands.knowledge.active")} />
      <InlineError error={mutation.error} />
      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={mutation.isPending}>
          {t("brands.knowledge.save")}
        </Button>
      </ModalFooter>
    </form>
  );
}
