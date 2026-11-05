"use client";

import { useSearchParams } from "next/navigation";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { Tabs } from "@/components/content/Tabs";
import { IconCheck, IconGlobe, IconUpload } from "@/components/icons";
import { WebsiteImportPanel } from "@/components/knowledge/websiteImport/WebsiteImportPanel";
import { Button, ButtonLink, Card, ConfirmDialog, EmptyState } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { profileWebsite } from "@/lib/knowledge/websiteImport";
import { businessPath } from "@/lib/navigation";

import { useKnowledgeKinds } from "../_components/hooks";
import { KnowledgeItemEditor } from "../_components/KnowledgeItemEditor";
import { ImportReviewCard } from "./_components/ImportReviewCard";
import { MenuSourceForm } from "./_components/MenuSourceForm";
import { useImportReview } from "./_lib/useImportReview";
import { useMenuSource } from "./_lib/useMenuSource";

type ImportSource = "menu" | "website";

/** Shows the chosen source in the address (`?source=website`) without a navigation. */
function showSourceInUrl(source: ImportSource): void {
  const query = new URLSearchParams(window.location.search);
  if (source === "website") {
    query.set("source", source);
  } else {
    query.delete("source");
  }
  const search = query.toString();
  window.history.replaceState(null, "", `${window.location.pathname}${search ? `?${search}` : ""}`);
}

/**
 * Knowledge -> Import, from two sources: a menu (a photo, PDF, text file or
 * link, read at once) or the business's website (up to 15 pages, read by a
 * queued job whose progress shows live). Either way the result is draft
 * items (switched off); the owner checks them in the same review, fixes what
 * is wrong and adds the chosen ones. The rest of the import is discarded in
 * one request (DELETE …/knowledge/import/{batch_id}). A link the API cannot
 * read is explained by its reason code (not public, unreachable, unreadable).
 */
export function MenuImportScreen() {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const kinds = useKnowledgeKinds();
  const imported = useImportReview();
  const source = useMenuSource(imported.open);
  const { review, done, editor } = imported;
  const tab: ImportSource = useSearchParams().get("source") === "website" ? "website" : "menu";
  const profile = useQuery(
    queryKeys.profile.stored(business.id),
    () => api.GET("/v1/businesses/{business_id}/profile", { params: { path: { business_id: business.id } } }),
    { enabled: tab === "website" },
  );

  const startOver = () => {
    imported.reset();
    source.reset();
  };

  if (done) {
    return (
      <Card>
        <EmptyState
          icon={<IconCheck className="size-6" />}
          title={tp("knowledge.import.doneTitle", done.added)}
          description={t("knowledge.import.doneDescription")}
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <ButtonLink href={businessPath(business.id, "assistant/knowledge")}>{t("knowledge.import.openKnowledge")}</ButtonLink>
              <Button variant="secondary" onClick={startOver}>
                {t("knowledge.import.another")}
              </Button>
            </div>
          }
        />
      </Card>
    );
  }

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
          onStartOver={startOver}
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
    <Tabs
      label={t("knowledge.website.tabsLabel")}
      tabs={[
        {
          key: "menu",
          label: (
            <>
              <IconUpload className="size-4" aria-hidden />
              {t("knowledge.website.tabMenu")}
            </>
          ),
        },
        {
          key: "website",
          label: (
            <>
              <IconGlobe className="size-4" aria-hidden />
              {t("knowledge.website.tabWebsite")}
            </>
          ),
        },
      ]}
      selected={tab}
      onSelect={showSourceInUrl}
    >
      {tab === "website" ? (
        <WebsiteImportPanel businessId={business.id} onReview={imported.open} suggestedUrl={profileWebsite(profile.data)} />
      ) : (
        <MenuSourceForm source={source} />
      )}
    </Tabs>
  );
}
