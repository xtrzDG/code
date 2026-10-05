"use client";

/**
 * The drafts in "Apply changes": updates built by hand after the one
 * customers get, which never reached them ("Draft of 5 Oct, 14:20"), each
 * with a way to look at it and to discard it. Discarding keeps the
 * owner's changes: the next "Apply changes" builds from them again.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { VERSION_STATUS_LABELS } from "@/app/b/[businessId]/assistant/_components/VersionStatusBadge";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconTrash } from "@/components/icons";
import { Button, ButtonLink, ConfirmDialog, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { PendingDraft } from "@/lib/assistant/ownerChecks";
import { businessPath } from "@/lib/navigation";

export function PendingDrafts({
  drafts,
  labelId,
  onNavigate,
}: {
  drafts: readonly PendingDraft[];
  labelId: string;
  onNavigate: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const [discarding, setDiscarding] = useState<PendingDraft | null>(null);
  const history = businessPath(business.id, "assistant/versions");

  const discard = useMutation(
    (draft: PendingDraft) =>
      api.DELETE("/v1/businesses/{business_id}/assistant/drafts/{version_id}", {
        params: { path: { business_id: business.id, version_id: draft.assistant_version_id } },
      }),
    // The versions, the test chat's choices and the pending changes follow.
    { invalidate: [queryKeys.assistant.all(business.id)] },
  );

  const dateOf = (draft: PendingDraft) => format.dateTime(draft.created_at);

  return (
    <>
      <ul aria-labelledby={labelId} className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
        {drafts.map((draft) => (
          <li key={draft.assistant_version_id} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2.5" data-draft={draft.assistant_version_id}>
            <span className="min-w-0 flex-1 text-sm">
              <span className="block font-medium text-ink">{t("updates.pending.draft", { date: dateOf(draft) })}</span>
              <span className="block text-xs text-ink-subtle">{t(VERSION_STATUS_LABELS[draft.status])}</span>
            </span>
            <span className="flex gap-1.5">
              <ButtonLink
                href={`${history}/${encodeURIComponent(draft.assistant_version_id)}`}
                onClick={onNavigate}
                variant="ghost"
                size="sm"
              >
                {t("updates.pending.open")}
              </ButtonLink>
              <Button
                variant="danger-ghost"
                size="sm"
                leadingIcon={<IconTrash className="size-4" aria-hidden />}
                aria-label={t("updates.pending.discardLabel", { date: dateOf(draft) })}
                onClick={() => setDiscarding(draft)}
              >
                {t("updates.pending.discard")}
              </Button>
            </span>
          </li>
        ))}
      </ul>
      <ConfirmDialog
        open={discarding !== null}
        title={t("updates.pending.discardTitle")}
        description={t("updates.pending.discardDescription")}
        confirmLabel={t("updates.pending.discard")}
        isPending={discard.isPending}
        onClose={() => setDiscarding(null)}
        onConfirm={async () => {
          if (!discarding) {
            return;
          }
          const result = await discard.run(discarding);
          if (result.ok) {
            setDiscarding(null);
            toast.success(t("updates.pending.discarded"));
          }
        }}
      />
    </>
  );
}
