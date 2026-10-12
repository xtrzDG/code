"use client";

import { useState } from "react";

import { IconPlus } from "@/components/icons";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, LoadingRegion, SkeletonRows, UserSentence } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatMoney } from "@/lib/format";

import type { BrandKnowledgeItem } from "../_lib/brands";
import { useBrandKnowledge, useBrandKnowledgeActions } from "../_lib/useBrands";
import { useBrandFrame } from "./BrandFrameContext";
import { KnowledgeItemModal } from "./KnowledgeItemModal";

/**
 * The facts every location's assistant knows (a location may replace one
 * with its own answer of the same key); brand owners add, edit and delete.
 */
export function BrandKnowledge() {
  const { t, tp, locale } = useI18n();
  const { brand, isOwner } = useBrandFrame();
  const knowledge = useBrandKnowledge(brand.id);
  const { remove } = useBrandKnowledgeActions(brand.id);
  const [editing, setEditing] = useState<BrandKnowledgeItem | "new" | null>(null);
  const [deleting, setDeleting] = useState<BrandKnowledgeItem | null>(null);
  const currency = brand.locations?.[0]?.currency_code ?? null;

  const onDelete = async () => {
    if (!deleting) {
      return;
    }
    const result = await remove.run(deleting.shared_key);
    if (result.ok) {
      setDeleting(null);
    }
  };

  const add = isOwner ? (
    <Button size="sm" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setEditing("new")} aria-haspopup="dialog">
      {t("brands.knowledge.add")}
    </Button>
  ) : undefined;

  let body;
  if (knowledge.error && !knowledge.data) {
    body = <ErrorState error={knowledge.error} onRetry={knowledge.reload} />;
  } else if (!knowledge.data) {
    body = (
      <LoadingRegion label={t("brands.loading")}>
        <SkeletonRows rows={3} />
      </LoadingRegion>
    );
  } else if ((knowledge.data.items ?? []).length === 0) {
    body = <EmptyState title={t("brands.knowledge.empty")} action={add} />;
  } else {
    body = (
      <ul className="divide-y divide-line">
        {(knowledge.data.items ?? []).map((item) => (
          <li key={item.shared_key} className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-start">
            <div className="min-w-0 flex-1">
              <p className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium break-words text-ink" data-user-content>
                  {item.title}
                </span>
                <Badge tone="neutral">{t(`brands.knowledge.kinds.${kindOf(item)}`)}</Badge>
                {item.is_active ? null : <Badge tone="warning">{t("brands.knowledge.hidden")}</Badge>}
                {(item.overridden_in ?? []).length > 0 ? (
                  <Badge tone="info">{tp("brands.knowledge.replaced", (item.overridden_in ?? []).length)}</Badge>
                ) : null}
              </p>
              {item.body ? (
                <p className="mt-1 line-clamp-3 text-sm whitespace-pre-line text-ink-muted" data-user-content>
                  {item.body}
                </p>
              ) : null}
              {item.price_minor !== null && item.price_minor !== undefined && item.currency_code ? (
                <p className="mt-1 text-sm font-medium text-ink tabular-nums">{formatMoney(item.price_minor, item.currency_code, locale)}</p>
              ) : null}
            </div>
            {isOwner ? (
              <div className="flex shrink-0 gap-2">
                <Button variant="ghost" size="sm" onClick={() => setEditing(item)} aria-haspopup="dialog">
                  {t("brands.team.edit")}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setDeleting(item)} aria-haspopup="dialog">
                  {t("brands.knowledge.delete")}
                </Button>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    );
  }

  return (
    <Card title={t("brands.knowledge.title")} description={t("brands.knowledge.description")} actions={add}>
      {body}
      {isOwner ? (
        <>
          <KnowledgeItemModal brandId={brand.id} item={editing} currency={currency} onClose={() => setEditing(null)} />
          <ConfirmDialog
            open={deleting !== null}
            onClose={() => setDeleting(null)}
            onConfirm={onDelete}
            title={deleting ? <UserSentence text={t("brands.knowledge.deleteTitle")} values={{ title: deleting.title }} /> : ""}
            description={t("brands.knowledge.deleteDescription")}
            confirmLabel={t("brands.knowledge.delete")}
            isPending={remove.isPending}
            error={remove.error}
          />
        </>
      ) : null}
    </Card>
  );
}

/** The item's kind among those a brand shares (anything else reads as a question and answer). */
function kindOf(item: BrandKnowledgeItem): "faq" | "policy" | "menu_item" | "product" {
  return item.kind === "policy" || item.kind === "menu_item" || item.kind === "product" ? item.kind : "faq";
}
