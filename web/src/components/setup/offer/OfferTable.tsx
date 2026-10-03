"use client";

/**
 * The offer as a short table: a name and a price per line, saved when the
 * owner leaves the line. The niche's examples carry an "Example" tag until
 * they get a price or are edited; a line is removed with its ×.
 */

import type { FocusEvent, KeyboardEvent } from "react";

import { IconAlert, IconCheck, IconPlus, IconX } from "@/components/icons";
import { Badge, Button, Input, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { validateOfferRow } from "@/lib/wizard/offers";

import type { OfferRows, RowStatus } from "./useOfferRows";

function StatusMark({ status }: { status: RowStatus | undefined }) {
  const { t } = useI18n();
  if (!status) {
    return <span className="size-4" aria-hidden />;
  }
  const label = status === "saving" ? t("tunnelOffer.offer.rowSaving") : status === "saved" ? t("tunnelOffer.offer.rowSaved") : t("tunnelOffer.offer.rowFailed");
  return (
    <span title={label} className="flex size-4 items-center justify-center">
      {status === "saving" ? (
        <Spinner size="sm" />
      ) : status === "saved" ? (
        <IconCheck className="size-4 text-success" aria-hidden />
      ) : (
        <IconAlert className="size-4 text-warning" aria-hidden />
      )}
      <span className="sr-only">{label}</span>
    </span>
  );
}

export function OfferTable({ table, currency }: { table: OfferRows; currency: string }) {
  const { t } = useI18n();
  const hasSuggestions = table.rows.some((row) => row.isSuggestion);

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

  const leaveRow = (key: string) => (event: FocusEvent<HTMLLIElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      void table.save(key);
    }
  };

  return (
    <div className="space-y-3">
      <ul aria-label={t("tunnelOffer.offer.tableLabel")} data-enter="own" onKeyDown={onKeyDown} className="space-y-2.5">
        {table.rows.map((row, index) => {
          const errors = table.showErrors ? validateOfferRow(row, currency) : {};
          const name = row.title.trim() || t("tunnelOffer.offer.removeEmpty");
          return (
            <li
              key={row.key}
              onBlur={leaveRow(row.key)}
              className={cn(
                "rounded-2xl border bg-surface/85 p-3 backdrop-blur-sm transition-colors sm:p-2.5",
                row.isSuggestion ? "border-dashed border-line-strong" : "border-line",
              )}
            >
              <div className="flex flex-wrap items-center gap-2 sm:flex-nowrap">
                <div className="min-w-0 flex-1 basis-full sm:basis-auto">
                  <Input
                    data-offer-name
                    autoFocus={row.key.startsWith("new-")}
                    aria-label={`${t("tunnelOffer.offer.name")} ${index + 1}`}
                    aria-invalid={errors.title ? true : undefined}
                    value={row.title}
                    maxLength={200}
                    placeholder={t("tunnelOffer.offer.namePlaceholder")}
                    onChange={(event) => table.update(row.key, { title: event.target.value })}
                    className="border-transparent bg-transparent shadow-none focus:border-line-strong"
                  />
                </div>
                {row.isSuggestion ? <Badge tone="neutral">{t("tunnelOffer.offer.suggestion")}</Badge> : null}
                <div className="relative w-32 shrink-0">
                  <Input
                    aria-label={`${t("tunnelOffer.offer.price", { currency })} ${index + 1}`}
                    aria-invalid={errors.price ? true : undefined}
                    value={row.price}
                    inputMode="decimal"
                    placeholder={t("tunnelOffer.offer.pricePlaceholder")}
                    onChange={(event) => table.update(row.key, { price: event.target.value })}
                    className="pe-12 text-end tabular-nums"
                  />
                  <span className="pointer-events-none absolute end-3 top-1/2 -translate-y-1/2 text-xs text-ink-subtle">{currency}</span>
                </div>
                <StatusMark status={table.status[row.key]} />
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={t("tunnelOffer.offer.removeRow", { name })}
                  title={t("tunnelOffer.offer.removeRow", { name })}
                  onClick={() => void table.remove(row.key)}
                >
                  <IconX className="size-4" aria-hidden />
                </Button>
              </div>
              {errors.title || errors.price ? (
                <p className="mt-1.5 px-1 text-sm text-danger" role="alert">
                  {t(errors.title ?? errors.price ?? "validation.required")}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button variant="secondary" onClick={table.add} leadingIcon={<IconPlus className="size-4" aria-hidden />}>
          {t("tunnelOffer.offer.addRow")}
        </Button>
        {hasSuggestions ? <p className="text-sm text-ink-muted">{t("tunnelOffer.offer.suggestionsHint")}</p> : null}
      </div>
    </div>
  );
}
