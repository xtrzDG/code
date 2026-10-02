"use client";

import { IconFile } from "@/components/content/icons";
import { Button, Card, Checkbox, EmptyState } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { ImportedMenuItem } from "@/lib/knowledge/menuImport";

import type { ImportReview } from "../_lib/importReview";
import { ImportDraftRow } from "./ImportDraftRow";

/** The drafts of an import to check, fix and add (or discard all). */
export function ImportReviewCard({
  review,
  isSaving,
  onToggle,
  onSelectAll,
  onEdit,
  onAdd,
  onDiscard,
  onStartOver,
}: {
  review: ImportReview;
  isSaving: boolean;
  onToggle: (id: string, checked: boolean) => void;
  onSelectAll: (checked: boolean) => void;
  onEdit: (entry: ImportedMenuItem) => void;
  onAdd: () => void;
  onDiscard: () => void;
  onStartOver: () => void;
}) {
  const { t, tp } = useI18n();
  const selectedCount = review.selected.size;
  const allSelected = selectedCount === review.items.length && review.items.length > 0;

  if (review.items.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={<IconFile className="size-6" />}
          title={t("knowledge.import.nothingFoundTitle")}
          description={t("knowledge.import.nothingFoundDescription")}
          action={
            <Button variant="secondary" onClick={onStartOver}>
              {t("knowledge.import.another")}
            </Button>
          }
        />
      </Card>
    );
  }

  return (
    <Card
      padded={false}
      title={tp("knowledge.import.reviewTitle", review.items.length)}
      description={
        review.skipped > 0
          ? `${t("knowledge.import.reviewDescription")} ${tp("knowledge.import.skipped", review.skipped)}`
          : t("knowledge.import.reviewDescription")
      }
      footer={
        <div className="flex w-full flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-ink-muted">{t("knowledge.import.uncheckedNote")}</p>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={onDiscard} disabled={isSaving}>
              {t("knowledge.import.discard")}
            </Button>
            <Button onClick={onAdd} isLoading={isSaving} loadingText={t("common.saving")} disabled={selectedCount === 0}>
              {tp("knowledge.import.addSelected", selectedCount)}
            </Button>
          </div>
        </div>
      }
    >
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3 sm:px-6">
        <Checkbox
          id="import-select-all"
          label={t("knowledge.import.selectAll")}
          checked={allSelected}
          onChange={(event) => onSelectAll(event.target.checked)}
        />
        <span className="text-sm text-ink-muted" aria-live="polite">
          {t("knowledge.import.selectedCount", { count: selectedCount, total: review.items.length })}
        </span>
      </div>
      <ul className="divide-y divide-line">
        {review.items.map((entry) => (
          <ImportDraftRow
            key={entry.item.id}
            entry={entry}
            isSelected={review.selected.has(entry.item.id)}
            onToggle={onToggle}
            onEdit={onEdit}
          />
        ))}
      </ul>
    </Card>
  );
}
