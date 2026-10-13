"use client";

import { formatPercent } from "@/components/insights/numbers";
import { sourceChannels, sourceRowName } from "@/components/value/sourceLabel";
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
  const channels = sourceChannels(row, t);
  const name = sourceRowName(row, t, tp);
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
