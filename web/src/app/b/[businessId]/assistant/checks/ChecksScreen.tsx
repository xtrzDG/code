"use client";

/**
 * Assistant → My checks (owners, under Advanced): the owner's own
 * questions with what the answer must do. Every "Apply changes" asks them;
 * each shows how it did in the latest run and the answer it got, and
 * "Check now" asks it once of what customers get now. Checks are added
 * here or saved from a fixed answer, a bad rating or a question without
 * an answer. "Open the check" elsewhere lands on one (`#check-…`).
 */

import { useEffect, useState } from "react";

import { IconPlus, IconShield } from "@/components/icons";
import { CheckDialog } from "@/components/teaching/CheckDialog";
import { useChecks } from "@/components/teaching/useTeaching";
import { Button, Card, ConfirmDialog, EmptyState, ErrorState, LoadingRegion, SkeletonCardList, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { CheckView } from "@/lib/teaching";
import { AUTO_LANGUAGE, checkFormOf, newCheckForm } from "@/lib/teachingChecks";

import { CheckRow } from "./CheckRow";

export function ChecksScreen() {
  const { t } = useI18n();
  const toast = useToast();
  const checks = useChecks();
  const [editing, setEditing] = useState<{ check: CheckView | null } | null>(null);
  const [deleting, setDeleting] = useState<CheckView | null>(null);
  const items = checks.list.data?.items;
  const limit = checks.list.data?.limit ?? 0;
  const hasItems = items !== undefined;

  // "Open the check" from an update: once the list is there, bring that check into view.
  useEffect(() => {
    const anchor = window.location.hash.slice(1);
    if (!hasItems || anchor === "") {
      return;
    }
    const row = document.getElementById(anchor);
    row?.scrollIntoView({ block: "center" });
    row?.focus({ preventScroll: true });
  }, [hasItems]);

  const toggle = async (check: CheckView) => {
    const result = await checks.update.run(check.id, { is_active: !check.is_active });
    if (result.ok) {
      checks.replace(result.data);
      toast.success(t(result.data.is_active ? "teaching.checks.resumed" : "teaching.checks.paused_toast"));
    } else {
      toast.error(result.error);
    }
  };

  const addButton = (
    <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setEditing({ check: null })} disabled={items !== undefined && items.length >= limit}>
      {t("teaching.checks.add")}
    </Button>
  );

  return (
    <div className="space-y-4">
      {items === undefined ? (
        checks.list.error ? (
          <Card>
            <ErrorState error={checks.list.error} onRetry={checks.list.reload} />
          </Card>
        ) : (
          <LoadingRegion label={t("teaching.checks.loading")}>
            <SkeletonCardList cards={3} />
          </LoadingRegion>
        )
      ) : items.length === 0 ? (
        <Card>
          <EmptyState
            icon={<IconShield className="size-6" />}
            title={t("teaching.checks.emptyTitle")}
            description={t("teaching.checks.emptyDescription")}
            action={addButton}
          />
        </Card>
      ) : (
        <>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="max-w-2xl space-y-1">
              <p className="text-sm text-ink-muted">{t("teaching.checks.description")}</p>
              <p className="text-xs text-ink-subtle">{t("teaching.checks.count", { count: items.length, limit })}</p>
            </div>
            {addButton}
          </div>
          {items.length >= limit ? <p className="text-sm text-warning">{t("teaching.checks.limitReached")}</p> : null}
          <ul className="space-y-3" data-checks="">
            {items.map((check) => (
              <CheckRow
                key={check.id}
                check={check}
                onEdit={() => setEditing({ check })}
                onToggle={() => void toggle(check)}
                onDelete={() => setDeleting(check)}
              />
            ))}
          </ul>
        </>
      )}

      {editing ? (
        <CheckDialog
          open
          initial={editing.check ? checkFormOf(editing.check) : newCheckForm(AUTO_LANGUAGE)}
          check={editing.check}
          title={t(editing.check ? "teaching.checks.editTitle" : "teaching.checks.newTitle")}
          description={editing.check ? undefined : t("teaching.checks.description")}
          onClose={() => setEditing(null)}
        />
      ) : null}

      <ConfirmDialog
        open={deleting !== null}
        tone="danger"
        title={t("teaching.checks.deleteTitle")}
        description={t("teaching.checks.deleteDescription", { question: deleting?.question ?? "" })}
        confirmLabel={t("teaching.checks.delete")}
        onClose={() => setDeleting(null)}
        onConfirm={() => {
          const check = deleting;
          setDeleting(null);
          if (check) {
            void checks.remove.run(check).then((result) => {
              if (result.ok) {
                toast.success(t("teaching.checks.deleted"));
              }
            });
          }
        }}
      />
    </div>
  );
}
