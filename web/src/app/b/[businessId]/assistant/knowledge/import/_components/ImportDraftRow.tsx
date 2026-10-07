"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconPencil } from "@/components/icons";
import { Badge, Button, type BadgeTone } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { cn } from "@/lib/cn";
import { numberFormat } from "@/lib/intl/formatters";
import { confidenceLevel, type ConfidenceLevel, type ImportedMenuItem } from "@/lib/knowledge/menuImport";
import { kindHasPrice } from "@/lib/knowledge/kinds";
import { pageLabel } from "@/lib/knowledge/websiteImport";

import { KIND_LABELS } from "../../_components/hooks";

const CONFIDENCE: Record<ConfidenceLevel, { tone: BadgeTone; label: MessageKey }> = {
  high: { tone: "success", label: "knowledge.import.confidence.high" },
  medium: { tone: "warning", label: "knowledge.import.confidence.medium" },
  low: { tone: "danger", label: "knowledge.import.confidence.low" },
};

/** One draft of the import: tick box, what the reader found, how sure it was, and an edit button. */
export function ImportDraftRow({
  entry,
  isSelected,
  onToggle,
  onEdit,
}: {
  entry: ImportedMenuItem;
  isSelected: boolean;
  onToggle: (id: string, checked: boolean) => void;
  onEdit: (entry: ImportedMenuItem) => void;
}) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const level = confidenceLevel(entry.confidence);
  const checkboxId = `import-${entry.item.id}`;
  const price = entry.item.price_minor !== null && entry.item.price_minor !== undefined ? format.money(entry.item.price_minor) : null;
  // Questions and rules have no price: no "No price" under them.
  const priceLine = [
    price ?? (entry.is_currency_mismatch || !kindHasPrice(entry.item.kind) ? null : t("knowledge.import.noPrice")),
    entry.item.duration_minutes ? t("knowledge.items.minutes", { count: entry.item.duration_minutes }) : null,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <li className={cn("flex items-start gap-3 px-4 py-4 sm:px-6", !isSelected && "bg-surface-muted/40")}>
      <input
        id={checkboxId}
        type="checkbox"
        className="mt-1 size-4 shrink-0 rounded border-line-strong accent-[var(--accent-solid)]"
        checked={isSelected}
        onChange={(event) => onToggle(entry.item.id, event.target.checked)}
      />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor={checkboxId} className="cursor-pointer font-medium break-words text-ink" dir="auto" data-user-content>
            {entry.item.title}
          </label>
          <Badge>{t(KIND_LABELS[entry.item.kind])}</Badge>
          <Badge tone={CONFIDENCE[level].tone}>
            {t(CONFIDENCE[level].label, {
              percent: numberFormat(locale, { style: "percent", maximumFractionDigits: 0 }).format(entry.confidence),
            })}
          </Badge>
        </div>
        {entry.item.body ? (
          <p className="mt-1 line-clamp-2 text-sm break-words text-ink-muted" dir="auto" data-user-content>
            {entry.item.body}
          </p>
        ) : null}
        {priceLine ? <p className="mt-1.5 text-sm text-ink-subtle">{priceLine}</p> : null}
        {entry.source_page_url ? (
          <p className="mt-1 truncate text-xs text-ink-subtle">
            <a
              href={entry.source_page_url}
              target="_blank"
              rel="noopener noreferrer"
              className="underline decoration-line-strong underline-offset-2 hover:text-ink"
            >
              {t("knowledge.website.sourcePage", { page: pageLabel(entry.source_page_url) })}
            </a>
          </p>
        ) : null}
        {entry.is_currency_mismatch ? (
          <p className="mt-1.5 text-sm text-warning">
            {t("knowledge.import.currencyMismatch", {
              price: `${entry.printed_price ?? ""} ${entry.printed_currency_code ?? ""}`.trim(),
              currency: format.currency,
            })}
          </p>
        ) : null}
      </div>
      <Button
        variant="ghost"
        size="sm"
        leadingIcon={<IconPencil className="size-4" aria-hidden />}
        aria-label={`${t("common.edit")}: ${entry.item.title}`}
        onClick={() => onEdit(entry)}
      >
        <span className="hidden sm:inline">{t("common.edit")}</span>
      </Button>
    </li>
  );
}
