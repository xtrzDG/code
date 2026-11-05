"use client";

import { Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { KnowledgeForm, KnowledgeFormErrors } from "@/lib/knowledge/form";
import { kindHasDuration } from "@/lib/knowledge/kinds";
import { MAX_BUFFER_MINUTES } from "@/lib/knowledge/offerFields";
import { kindHasBuffer } from "@/lib/offers";

/**
 * Price, duration and the break after it. A room type has a nightly rate
 * (its seasons are edited below) and no duration; services and packages
 * have a length and a break; other sold items a price and, when they last
 * a while, a duration.
 */
export function PriceFields({
  form,
  errors,
  currency,
  change,
}: {
  form: KnowledgeForm;
  errors: KnowledgeFormErrors;
  currency: string;
  change: (patch: Partial<KnowledgeForm>) => void;
}) {
  const { t } = useI18n();
  const isRoomType = form.kind === "room_type";
  const hasBuffer = kindHasBuffer(form.kind);
  const showDuration = !isRoomType && (kindHasDuration(form.kind) || form.duration.trim() !== "");
  // Three fields share a row on wide screens; two take half each.
  const span = hasBuffer ? "sm:col-span-2" : "sm:col-span-3";

  return (
    <>
      <Field
        label={t(isRoomType ? "knowledge.offer.nightlyPrice" : "knowledge.form.price", { currency })}
        optionalLabel={t("common.optional")}
        hint={t(isRoomType ? "knowledge.offer.nightlyPriceHint" : "knowledge.form.priceHint")}
        error={errors.price && t(errors.price)}
        className={span}
      >
        {(control) => (
          <Input
            {...control}
            inputMode="decimal"
            autoComplete="off"
            value={form.price}
            onChange={(event) => change({ price: event.target.value })}
          />
        )}
      </Field>
      {showDuration ? (
        <Field
          label={t("knowledge.form.duration")}
          optionalLabel={t("common.optional")}
          hint={hasBuffer ? t("knowledge.offer.durationHint") : undefined}
          error={errors.duration && t(errors.duration)}
          className={span}
        >
          {(control) => (
            <Input
              {...control}
              inputMode="numeric"
              autoComplete="off"
              value={form.duration}
              onChange={(event) => change({ duration: event.target.value })}
            />
          )}
        </Field>
      ) : null}
      {hasBuffer ? (
        <Field
          label={t("knowledge.offer.buffer")}
          optionalLabel={t("common.optional")}
          hint={t("knowledge.offer.bufferHint")}
          error={errors.buffer && t(errors.buffer)}
          className={span}
        >
          {(control) => (
            <Input
              {...control}
              inputMode="numeric"
              autoComplete="off"
              max={MAX_BUFFER_MINUTES}
              value={form.buffer}
              onChange={(event) => change({ buffer: event.target.value })}
            />
          )}
        </Field>
      ) : null}
    </>
  );
}
