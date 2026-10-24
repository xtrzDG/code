"use client";

/**
 * "What you offer" from the business's website or a menu (a photo, PDF or
 * link), inside the tunnel: the same readers and the same review as
 * Assistant → Knowledge → Import. Nothing is saved before the owner checks
 * the drafts; the ones added join the offer table.
 */

import { useEffect, useRef } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { ImportReviewCard } from "@/app/b/[businessId]/assistant/knowledge/import/_components/ImportReviewCard";
import { MenuSourceForm } from "@/app/b/[businessId]/assistant/knowledge/import/_components/MenuSourceForm";
import { useImportReview } from "@/app/b/[businessId]/assistant/knowledge/import/_lib/useImportReview";
import { useMenuSource } from "@/app/b/[businessId]/assistant/knowledge/import/_lib/useMenuSource";
import { useKnowledgeKinds } from "@/app/b/[businessId]/assistant/knowledge/_components/hooks";
import { KnowledgeItemEditor } from "@/app/b/[businessId]/assistant/knowledge/_components/KnowledgeItemEditor";
import { WebsiteImportPanel } from "@/components/knowledge/websiteImport/WebsiteImportPanel";
import { ConfirmDialog } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { profileWebsite } from "@/lib/knowledge/websiteImport";

export type ImportSource = "website" | "menu";

export function OfferImport({ businessId, source, onAdded }: { businessId: string; source: ImportSource; onAdded: (count: number) => void }) {
  const { t, tp } = useI18n();
  const kinds = useKnowledgeKinds();
  const imported = useImportReview();
  const menu = useMenuSource(imported.open);
  const { review, done, editor } = imported;
  const profile = useQuery(
    queryKeys.profile.stored(businessId),
    () => api.GET("/v1/businesses/{business_id}/profile", { params: { path: { business_id: businessId } } }),
    { enabled: source === "website" },
  );

  // Added drafts go back to the table (once per import).
  const reported = useRef<typeof done>(null);
  useEffect(() => {
    if (done && reported.current !== done) {
      reported.current = done;
      onAdded(done.added);
    }
  }, [done, onAdded]);

  if (review) {
    return (
      <>
        <ImportReviewCard
          review={review}
          isSaving={imported.isSaving}
          onToggle={imported.toggle}
          onSelectAll={imported.selectAll}
          onEdit={imported.edit}
          onAdd={() => void imported.addSelected()}
          onDiscard={() => imported.setConfirmDiscard(true)}
          onStartOver={() => {
            imported.reset();
            menu.reset();
          }}
        />
        {editor ? (
          <KnowledgeItemEditor
            key={editor.key}
            target={editor.target}
            kinds={kinds}
            showActiveToggle={false}
            onClose={imported.closeEditor}
            onSaved={imported.saveDraft}
          />
        ) : null}
        <ConfirmDialog
          open={imported.confirmDiscard}
          title={t("knowledge.import.discardTitle")}
          description={tp("knowledge.import.discardDescription", review.items.length)}
          confirmLabel={t("knowledge.import.discard")}
          isPending={imported.isDiscarding}
          onConfirm={() => void imported.discardAll()}
          onClose={() => imported.setConfirmDiscard(false)}
        />
      </>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-ink-muted">{t("tunnelOffer.offer.importHint")}</p>
      {source === "website" ? (
        <WebsiteImportPanel businessId={businessId} onReview={imported.open} suggestedUrl={profileWebsite(profile.data)} />
      ) : (
        <MenuSourceForm source={menu} />
      )}
    </div>
  );
}
