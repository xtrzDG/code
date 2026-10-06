"use client";

/**
 * One line of the offer table: the name, an "Example" tag on the niche's
 * suggestions, the price and a way to remove it; in the profile editor
 * also the kind (when the business sells more than one) and the minutes
 * (for kinds that last a while). Its save state sits at the end. On a
 * phone the name and the price share one row, an example's tag sits on
 * the frame, and removing is in the line's "⋯" menu; with the kind and
 * minutes columns those two go to a second row under the name and price.
 */

import type { FocusEvent } from "react";

import type { KnowledgeItemKind } from "@/api/types";
import { IconX } from "@/components/icons";
import { Badge, Button, Input, OverflowMenu, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { kindHasDuration } from "@/lib/knowledge/kinds";
import type { TunnelOfferRow } from "@/lib/tunnel/offer";
import type { OfferRowErrors } from "@/lib/wizard/offers";

import { SaveMark } from "../fields/SaveMark";
import type { OfferRowPatch, RowStatus } from "./useOfferRows";

export interface OfferColumns {
  /** The kinds a line may be (shown when there is more than one). */
  kinds: readonly KnowledgeItemKind[];
  showKind: boolean;
  showDuration: boolean;
}

export function OfferLine({
  row,
  index,
  currency,
  errors,
  status,
  columns,
  onChange,
  onLeave,
  onRemove,
}: {
  row: TunnelOfferRow;
  index: number;
  currency: string;
  errors: OfferRowErrors;
  status: RowStatus | undefined;
  columns: OfferColumns;
  onChange: (patch: OfferRowPatch) => void;
  onLeave: () => void;
  onRemove: () => void;
}) {
  const { t } = useI18n();
  const name = row.title.trim() || t("tunnelOffer.offer.removeEmpty");
  const label = row.title.trim() || String(index + 1);
  const hasDuration = kindHasDuration(row.kind);
  const problem = errors.title ?? errors.price ?? errors.duration;
  const twoRows = columns.showKind || columns.showDuration;

  const leave = (event: FocusEvent<HTMLLIElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      onLeave();
    }
  };

  return (
    <li
      data-row-key={row.key}
      onBlur={leave}
      className={cn(
        "relative rounded-2xl border bg-surface/85 p-2 backdrop-blur-sm transition-colors sm:p-2.5",
        row.isSuggestion ? "border-dashed border-line-strong" : "border-line",
      )}
    >
      <div className={cn("flex items-center gap-2 sm:flex-nowrap", twoRows ? "flex-wrap" : "max-sm:gap-1.5")}>
        <div className="min-w-0 flex-1 sm:basis-auto">
          <Input
            data-offer-name
            autoFocus={row.key.startsWith("new-") && row.title === ""}
            aria-label={`${t("tunnelOffer.offer.name")} ${index + 1}`}
            aria-invalid={errors.title ? true : undefined}
            value={row.title}
            maxLength={200}
            placeholder={t("tunnelOffer.offer.namePlaceholder")}
            onChange={(event) => onChange({ title: event.target.value })}
            className="border-transparent bg-transparent shadow-none focus:border-line-strong"
          />
        </div>
        {/* On a phone the kind and the minutes (order-1) wrap under this break. */}
        {twoRows ? <span aria-hidden className="h-0 basis-full sm:hidden max-sm:order-1" /> : null}
        {row.isSuggestion ? (
          // On a phone the tag sits on the line's dashed frame, so the name and the price keep one row.
          <Badge tone="neutral" className="max-sm:absolute max-sm:-top-2.5 max-sm:start-3 max-sm:py-0 max-sm:text-[0.6875rem]">
            {t("tunnelOffer.offer.suggestion")}
          </Badge>
        ) : null}
        {columns.showKind ? (
          <Select
            aria-label={t("profileEdit.offer.kindOf", { name: label })}
            value={row.kind}
            onChange={(event) => onChange({ kind: event.target.value as KnowledgeItemKind })}
            className="w-36 shrink-0 max-sm:order-1 max-sm:w-auto max-sm:min-w-0 max-sm:flex-1"
          >
            {(columns.kinds.includes(row.kind) ? columns.kinds : [row.kind, ...columns.kinds]).map((kind) => (
              <option key={kind} value={kind}>
                {t(`onboarding.offer.kinds.${kind}`)}
              </option>
            ))}
          </Select>
        ) : null}
        <div className="relative w-32 shrink-0 max-sm:w-28">
          <Input
            aria-label={`${t("tunnelOffer.offer.price", { currency })} ${index + 1}`}
            aria-invalid={errors.price ? true : undefined}
            value={row.price}
            inputMode="decimal"
            placeholder={t("tunnelOffer.offer.pricePlaceholder")}
            onChange={(event) => onChange({ price: event.target.value })}
            className="pe-12 text-end tabular-nums"
          />
          <span className="pointer-events-none absolute end-3 top-1/2 -translate-y-1/2 text-xs text-ink-subtle">{currency}</span>
        </div>
        {columns.showDuration ? (
          <Input
            aria-label={t("profileEdit.offer.durationOf", { name: label })}
            aria-invalid={errors.duration ? true : undefined}
            value={row.duration}
            inputMode="numeric"
            disabled={!hasDuration}
            placeholder={hasDuration ? t("profileEdit.offer.durationShort") : "—"}
            title={hasDuration ? undefined : t("profileEdit.offer.noDuration")}
            onChange={(event) => onChange({ duration: event.target.value })}
            className={cn("w-24 shrink-0 text-end tabular-nums max-sm:order-1 max-sm:w-20", !hasDuration && "max-sm:hidden")}
          />
        ) : null}
        <SaveMark status={status} />
        <Button
          variant="ghost"
          size="sm"
          aria-label={t("tunnelOffer.offer.removeRow", { name })}
          title={t("tunnelOffer.offer.removeRow", { name })}
          onClick={onRemove}
          className="shrink-0 max-sm:hidden"
        >
          <IconX className="size-4" aria-hidden />
        </Button>
        <OverflowMenu
          iconOnly
          label={t("tunnelOffer.offer.rowMenu", { name: label })}
          placement="bottom"
          className="shrink-0 sm:hidden"
          // The menu already names the line; its one item stays short enough for a phone.
          actions={[{ key: "remove", label: t("common.delete"), onSelect: onRemove, tone: "danger" }]}
        />
      </div>
      {problem ? (
        <p className="mt-1.5 px-1 text-sm text-danger" role="alert">
          {t(problem)}
        </p>
      ) : null}
    </li>
  );
}
