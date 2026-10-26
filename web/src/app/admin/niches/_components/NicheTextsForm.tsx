"use client";

/**
 * The texts of one niche in one language: each part of the template in
 * its own card (the niche, each profile question, the default rules, the
 * starter answers), folded to its title until opened (a part with
 * reworded texts opens by itself), the preview beside them, and the
 * draft's actions.
 * Saving keeps the draft (owners read nothing of it); publishing saves the
 * language's changes first, then makes the draft the next version.
 */

import { useState } from "react";

import { IconChevronRight } from "@/components/icons";
import { Badge, Button, Card, ConfirmDialog, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  draftBody,
  fieldGroups,
  hasProblems,
  isDirty,
  shownText,
  startingValues,
  type FieldGroup,
  type FormValues,
  type NicheTextEditor,
} from "../_lib/nicheTexts";
import type { useNicheEditor } from "../_lib/useNicheTexts";
import { NicheFieldRow } from "./NicheFieldRow";
import { NichePreview } from "./NichePreview";

type NicheEditing = ReturnType<typeof useNicheEditor>;
type Confirming = "publish" | "discard" | null;

export function NicheTextsForm({ editor, niche, nicheName }: { editor: NicheTextEditor; niche: NicheEditing; nicheName: string }) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const start = startingValues(editor);
  const [values, setValues] = useState<FormValues>(start);
  const [confirming, setConfirming] = useState<Confirming>(null);
  const dirty = isDirty(values, start);
  const invalid = hasProblems(editor, values);
  const name = nicheName;
  const fields = new Map(editor.fields.map((field) => [field.field_key, field]));
  const onChange = (fieldKey: string, value: string) => setValues((current) => ({ ...current, [fieldKey]: value }));

  const save = async (): Promise<boolean> => (dirty ? niche.save(draftBody(editor, values)) : true);
  const onSave = async () => {
    if (await save()) {
      toast.success(t("adminNiches.editor.draftSaved"));
    }
  };
  const onPublish = async () => {
    if (!(await save())) {
      return;
    }
    const release = await niche.publish();
    if (release) {
      setConfirming(null);
      toast.success(t("adminNiches.editor.published", { version: release.version }));
    }
  };
  const onDiscard = async () => {
    if (await niche.discard()) {
      setConfirming(null);
      toast.success(t("adminNiches.editor.discarded"));
    }
  };

  const questionPositions = new Map(editor.questions.map((question, index) => [question.key, index + 1]));
  const groupTitle = (group: FieldGroup) =>
    group.questionKey
      ? `${t("adminNiches.editor.question", { position: questionPositions.get(group.questionKey) ?? 0 })} · ${shownText(
          fields.get(`questions.${group.questionKey}.label`),
          start,
        )}`
      : t(`adminNiches.editor.sections.${group.section}`);

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div className="space-y-6">
        <div className="sticky top-0 z-10 flex flex-wrap items-center gap-2 rounded-xl bg-surface py-2">
          <Button onClick={() => void onSave()} disabled={!dirty || invalid} isLoading={niche.saving.isPending}>
            {t("adminNiches.editor.saveDraft")}
          </Button>
          <Button
            variant="secondary"
            onClick={() => setConfirming("publish")}
            disabled={invalid || (!dirty && !editor.status.has_draft)}
          >
            {t("adminNiches.editor.publish")}
          </Button>
          {editor.status.has_draft ? (
            <Button variant="ghost" onClick={() => setConfirming("discard")}>
              {t("adminNiches.editor.discard")}
            </Button>
          ) : null}
          {dirty ? <Badge tone="warning">{t("adminNiches.editor.unsaved")}</Badge> : null}
        </div>
        {fieldGroups(editor).map((group) => {
          const title = groupTitle(group);
          const reworded = group.fields.filter((field) => (start[field.field_key] ?? "") !== "").length;
          return (
            <Card key={`${group.section}:${group.questionKey ?? ""}`} aria-label={title} padded={false}>
              <details open={reworded > 0 || undefined} className="group/part">
                <summary className="flex min-h-11 cursor-pointer list-none items-center gap-3 rounded-2xl px-5 py-3 focus-visible:outline-2 focus-visible:outline-focus [&::-webkit-details-marker]:hidden">
                  <IconChevronRight
                    className="size-4 shrink-0 text-ink-subtle transition-transform group-open/part:rotate-90 rtl:-scale-x-100 rtl:group-open/part:-rotate-90"
                    aria-hidden
                  />
                  <span className="min-w-0 flex-1 text-sm font-medium text-ink">{title}</span>
                  {reworded > 0 ? <Badge>{tp("adminNiches.reworded", reworded)}</Badge> : null}
                </summary>
                <fieldset className="space-y-3 border-t border-line px-5 py-4">
                  <legend className="sr-only">{title}</legend>
                  {group.fields.map((field) => (
                    <NicheFieldRow
                      key={field.field_key}
                      field={field}
                      language={editor.language}
                      value={values[field.field_key] ?? ""}
                      onChange={onChange}
                    />
                  ))}
                </fieldset>
              </details>
            </Card>
          );
        })}
      </div>
      <div className="lg:sticky lg:top-4 lg:self-start">
        <NichePreview editor={editor} values={values} />
      </div>

      <ConfirmDialog
        open={confirming === "publish"}
        onClose={() => setConfirming(null)}
        onConfirm={onPublish}
        tone="primary"
        isPending={niche.saving.isPending || niche.publishing.isPending}
        error={niche.publishing.error}
        title={t("adminNiches.editor.publishTitle", { niche: name })}
        description={t("adminNiches.editor.publishDescription")}
        confirmLabel={t("adminNiches.editor.publish")}
      />
      <ConfirmDialog
        open={confirming === "discard"}
        onClose={() => setConfirming(null)}
        onConfirm={onDiscard}
        isPending={niche.discarding.isPending}
        error={niche.discarding.error}
        title={t("adminNiches.editor.discardTitle", { niche: name })}
        description={t("adminNiches.editor.discardDescription")}
        confirmLabel={t("adminNiches.editor.discard")}
      />
    </div>
  );
}
