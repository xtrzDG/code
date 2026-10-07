"use client";

import { CHANNEL_LABELS } from "@/components/insights/labels";
import { formatPercent } from "@/components/insights/numbers";
import { sourceLabel } from "@/components/value/sourceLabel";
import type { CustomerSourceRow } from "@/components/value/sourcesModel";
import { useI18n } from "@/i18n/client";

/**
 * A source of "Where customers came from": its name (the share card's
 * place, the line called, an ad; the channel for conversations without a
 * tag; "N more tags" for the folded ones), its raw tag and channels under
 * it, and its share of the period's conversations as a bar.
 */
export function SourceCell({ row, share }: { row: CustomerSourceRow; share: number }) {
  const { t, tp, locale } = useI18n();
  const channels = (row.channels ?? []).map((channel) => t(CHANNEL_LABELS[channel])).join(", ");
  const name =
    row.kind === "other"
      ? tp("sources.other", row.source_count ?? 1)
      : row.kind === "untagged" || !row.acquisition_source
        ? channels || t("sources.untagged")
        : sourceLabel(row.acquisition_source, t);
  const details = row.kind === "untagged" ? t("sources.untagged") : [row.acquisition_source, channels].filter(Boolean).join(" · ");
  return (
    <span className="block min-w-0">
      <span className="block font-medium break-words text-ink">{name}</span>
      {details ? <span className="block text-xs break-all text-ink-subtle">{details}</span> : null}
      <span className="mt-1.5 block h-1.5 max-w-40 rounded-full bg-surface-muted" aria-hidden>
        <span className="block h-full rounded-full bg-accent-solid" style={{ width: `${Math.max(share, 2)}%` }} />
      </span>
      <span className="sr-only">{t("sources.share", { percent: formatPercent(share, locale) })}</span>
    </span>
  );
}

/** A stable key of a source row. */
export function sourceRowKey(row: CustomerSourceRow): string {
  return `${row.kind}:${row.acquisition_source ?? ""}:${(row.channels ?? []).join(",")}`;
}
