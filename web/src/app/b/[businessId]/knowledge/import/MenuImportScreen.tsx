"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { ConfirmDialog } from "@/components/content/ConfirmDialog";
import { IconCheck } from "@/components/icons";
import { Button, ButtonLink, Card, EmptyState } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { useKnowledgeKinds } from "../_components/hooks";
import { KnowledgeItemEditor } from "../_components/KnowledgeItemEditor";
import { ReassemblyNotice } from "../_components/ReassemblyNotice";
import { ImportReviewCard } from "./_components/ImportReviewCard";
import { MenuSourceForm } from "./_components/MenuSourceForm";
import { useImportReview } from "./_lib/useImportReview";
import { useMenuSource } from "./_lib/useMenuSource";

/**
 * Knowledge -> Import a menu: a photo, PDF, text file or link is read into
 * draft items (switched off); the owner checks them, fixes what is wrong and
 * adds the chosen ones. The rest of the import is discarded in one request
 * (DELETE …/knowledge/import/{batch_id}). A link the API cannot read is
 * explained by its reason code (not public, unreachable, unreadable).
 */
export function MenuImportScreen() {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const kinds = useKnowledgeKinds();
  const imported = useImportReview();
  const source = useMenuSource(imported.open);
  const { review, done, editor } = imported;

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
              <ButtonLink href={businessPath(business.id, "knowledge")}>{t("knowledge.import.openKnowledge")}</ButtonLink>
              <Button variant="secondary" onClick={startOver}>
                {t("knowledge.import.another")}
              </Button>
            </div>
          }
        />
        <ReassemblyNotice className="mt-2" />
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

  return <MenuSourceForm source={source} />;
}
