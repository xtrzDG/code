"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { KnowledgeItemDetails, Schema } from "@/api/types";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Badge, Button, Card, ErrorState, LoadingRegion, SkeletonText, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

type SharedItem = Schema<"LocationSharedItemView">;

/**
 * Knowledge -> "Shared by the brand", for a location of a brand: the
 * answers every location knows, which of them this location replaces with
 * its own, and writing or editing that own answer (it starts as a copy of
 * the brand's and opens in the editor).
 */
export function BrandSharedAnswers({
  onOpenOwn,
  onCreated,
}: {
  /** Opens this location's own answer (by id) in the editor. */
  onOpenOwn: (itemId: string) => void;
  /** Opens a just created own answer in the editor. */
  onCreated: (item: KnowledgeItemDetails) => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const shared = useQuery(queryKeys.brands.locationShared(business.id), () =>
    api.GET("/v1/businesses/{business_id}/brand/knowledge", { params: { path } }),
  );
  const replace = useMutation(
    (sharedKey: string) =>
      api.POST("/v1/businesses/{business_id}/knowledge/brand-overrides", { params: { path }, body: { shared_key: sharedKey } }),
    {
      invalidate: [queryKeys.knowledge.all(business.id), queryKeys.brands.locationShared(business.id)],
      stale: [queryKeys.assistant.all(business.id)],
    },
  );

  const onReplace = async (item: SharedItem) => {
    const result = await replace.run(item.shared_key);
    if (result.ok) {
      toast.success(t("brands.locationKnowledge.created"));
      onCreated(result.data);
    }
  };

  const items = shared.data?.items ?? [];
  return (
    <Card padded={false} aria-label={t("brands.locationKnowledge.title")} data-testid="brand-shared-answers">
      <div className="border-b border-line px-4 py-4 sm:px-6">
        <h2 className="text-base font-semibold text-ink">{t("brands.locationKnowledge.title")}</h2>
        <p className="mt-1 text-sm text-ink-muted">{t("brands.locationKnowledge.description")}</p>
      </div>
      {shared.error && !shared.data ? (
        <ErrorState error={shared.error} onRetry={shared.reload} className="py-6" />
      ) : !shared.data ? (
        <LoadingRegion label={t("brands.locationKnowledge.loading")} className="px-4 py-4 sm:px-6">
          <SkeletonText lines={3} />
        </LoadingRegion>
      ) : items.length === 0 ? (
        <p className="px-4 py-4 text-sm text-ink-muted sm:px-6">{t("brands.locationKnowledge.empty")}</p>
      ) : (
        <ul className="divide-y divide-line">
          {items.map((item) => (
            <SharedRow
              key={item.shared_key}
              item={item}
              isPending={replace.isPending}
              onReplace={() => void onReplace(item)}
              onOpenOwn={onOpenOwn}
            />
          ))}
        </ul>
      )}
    </Card>
  );
}

function SharedRow({
  item,
  isPending,
  onReplace,
  onOpenOwn,
}: {
  item: SharedItem;
  isPending: boolean;
  onReplace: () => void;
  onOpenOwn: (itemId: string) => void;
}) {
  const { t, tDynamic } = useI18n();
  const format = useBusinessFormat();
  const ownId = item.own_item_id ?? null;
  const price =
    item.price_minor !== null && item.price_minor !== undefined ? format.money(item.price_minor, item.currency_code ?? undefined) : null;
  return (
    <li className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start sm:gap-6 sm:px-6">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium break-words text-ink" dir="auto" data-user-content>
            {item.title}
          </p>
          <Badge tone="neutral">{tDynamic(`brands.knowledge.kinds.${item.kind}`, item.kind)}</Badge>
          {ownId ? <Badge tone="accent">{t("brands.locationKnowledge.own")}</Badge> : null}
          {item.is_active ? null : <Badge tone="warning">{t("brands.locationKnowledge.hidden")}</Badge>}
        </div>
        {item.body ? (
          <p className="mt-1 line-clamp-2 text-sm break-words text-ink-muted" dir="auto" data-user-content>
            {item.body}
          </p>
        ) : null}
        {price ? <p className="mt-1 text-xs text-ink-subtle tabular-nums">{price}</p> : null}
      </div>
      <div className="shrink-0">
        {ownId ? (
          <Button variant="secondary" size="sm" onClick={() => onOpenOwn(ownId)} aria-haspopup="dialog">
            {t("brands.locationKnowledge.editOwn")}
          </Button>
        ) : (
          <Button variant="secondary" size="sm" onClick={onReplace} disabled={isPending} aria-haspopup="dialog">
            {t("brands.locationKnowledge.replace")}
          </Button>
        )}
      </div>
    </li>
  );
}
