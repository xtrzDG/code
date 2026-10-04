"use client";

/**
 * The offer as a short table: a name and a price per line, saved when the
 * owner leaves the line. The niche's examples carry an "Example" tag until
 * they get a price or are edited; a line is removed with its ×. Enter
 * goes to the next line's name (a new line after the last one).
 *
 * In the profile editor the table also has the kind and the minutes,
 * shows a line's problems as soon as it could not be saved, and takes
 * lines pasted from a spreadsheet (name, price, minutes).
 */

import type { ClipboardEvent, KeyboardEvent } from "react";

import type { KnowledgeItemKind } from "@/api/types";
import { IconPlus } from "@/components/icons";
import { Button, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { kindHasDuration } from "@/lib/knowledge/kinds";
import { parsePastedOffer } from "@/lib/tunnel/offerPaste";
import { validateOfferRow } from "@/lib/wizard/offers";

import type { StepMode } from "../stepMode";
import { OfferLine, type OfferColumns } from "./OfferLine";
import type { OfferRows } from "./useOfferRows";

function ColumnHeads({ columns, currency }: { columns: OfferColumns; currency: string }) {
  const { t } = useI18n();
  return (
    <div aria-hidden className="hidden items-center gap-2 px-2.5 text-xs font-medium tracking-wide text-ink-subtle uppercase sm:flex">
      <span className="min-w-0 flex-1 ps-3">{t("tunnelOffer.offer.name")}</span>
      {columns.showKind ? <span className="w-36 shrink-0 ps-3">{t("profileEdit.offer.kind")}</span> : null}
      <span className="w-32 shrink-0 pe-3 text-end">{t("tunnelOffer.offer.price", { currency })}</span>
      {columns.showDuration ? <span className="w-24 shrink-0 pe-3 text-end">{t("profileEdit.offer.duration")}</span> : null}
      <span className="w-4 shrink-0" />
      <span className="w-9 shrink-0" />
    </div>
  );
}

export function OfferTable({
  table,
  currency,
  mode = "tunnel",
  kinds = [],
}: {
  table: OfferRows;
  currency: string;
  mode?: StepMode;
  /** The niche's kinds of offer (the edit mode's kind column). */
  kinds?: readonly KnowledgeItemKind[];
}) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const isEdit = mode === "edit";
  const hasSuggestions = table.rows.some((row) => row.isSuggestion);
  const columns: OfferColumns = { kinds, showKind: isEdit && kinds.length > 1, showDuration: isEdit && kinds.some(kindHasDuration) };

  // Enter in a line goes to the next line's name (a new line after the last one).
  const onKeyDown = (event: KeyboardEvent<HTMLUListElement>) => {
    const target = event.target as HTMLElement;
    if (event.key !== "Enter" || target.tagName !== "INPUT" || event.nativeEvent.isComposing) {
      return;
    }
    event.preventDefault();
    const names = Array.from(event.currentTarget.querySelectorAll<HTMLInputElement>("input[data-offer-name]"));
    const index = names.findIndex((input) => input.closest("li")?.contains(target));
    const next = names[index + 1];
    if (next) {
      next.focus();
    } else {
      table.add();
    }
  };

  // Several lines pasted at once (from a spreadsheet): each becomes a line of its own.
  const onPaste = (event: ClipboardEvent<HTMLUListElement>) => {
    const target = event.target as HTMLElement;
    const pasted = target.tagName === "INPUT" ? parsePastedOffer(event.clipboardData.getData("text/plain")) : null;
    if (!pasted || pasted.length === 0) {
      return;
    }
    event.preventDefault();
    const count = table.paste(pasted, target.closest("li")?.dataset.rowKey ?? "");
    toast.success(tp("profileEdit.offer.pasted", count));
  };

  return (
    <div className="space-y-3">
      {isEdit && table.rows.length > 0 ? <ColumnHeads columns={columns} currency={currency} /> : null}
      <ul
        aria-label={t("tunnelOffer.offer.tableLabel")}
        data-enter="own"
        onKeyDown={onKeyDown}
        onPaste={isEdit ? onPaste : undefined}
        className="space-y-2.5"
      >
        {table.rows.map((row, index) => (
          <OfferLine
            key={row.key}
            row={row}
            index={index}
            currency={currency}
            errors={table.showErrors || (isEdit && table.status[row.key] === "failed") ? validateOfferRow(row, currency) : {}}
            status={table.status[row.key]}
            columns={columns}
            onChange={(patch) => table.update(row.key, patch)}
            onLeave={() => void table.save(row.key)}
            onRemove={() => void table.remove(row.key)}
          />
        ))}
      </ul>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button variant="secondary" onClick={table.add} leadingIcon={<IconPlus className="size-4" aria-hidden />}>
          {t("tunnelOffer.offer.addRow")}
        </Button>
        {hasSuggestions ? (
          <p className="text-sm text-ink-muted">{t("tunnelOffer.offer.suggestionsHint")}</p>
        ) : isEdit ? (
          <p className="text-sm text-ink-muted">{t("profileEdit.offer.pasteHint")}</p>
        ) : null}
      </div>
    </div>
  );
}
