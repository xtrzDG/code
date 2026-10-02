"use client";

import { useEffect, useId, useRef, useState, type DragEvent, type FormEvent } from "react";

import { api } from "@/api/client";
import { describeError } from "@/api/errors";
import { useApiMutation } from "@/api/hooks";
import type { KnowledgeItemDetails } from "@/api/types";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { ConfirmDialog } from "@/components/content/ConfirmDialog";
import { IconFile, IconLink, IconPencil, IconUpload } from "@/components/content/icons";
import { IconCheck } from "@/components/icons";
import {
  Alert,
  Badge,
  Button,
  ButtonLink,
  Card,
  Checkbox,
  EmptyState,
  Field,
  Input,
  Radio,
  useToast,
  type BadgeTone,
} from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { cn } from "@/lib/cn";
import {
  base64FromDataUrl,
  checkMenuFile,
  confidenceLevel,
  formatFileSize,
  initialImportSelection,
  MENU_UPLOAD_ACCEPT,
  menuLinkProblem,
  type ConfidenceLevel,
  type ImportedMenuItem,
  type MenuLinkProblemCode,
} from "@/lib/knowledge/menuImport";
import { businessPath } from "@/lib/navigation";
import { webLinkSchema } from "@/lib/validation";

import { KIND_LABELS, useKnowledgeKinds } from "../_components/hooks";
import { KnowledgeItemEditor, type KnowledgeEditorTarget } from "../_components/KnowledgeItemEditor";
import { ReassemblyNotice } from "../_components/ReassemblyNotice";

type Source = "file" | "link";

interface ImportReview {
  /** The import: discarding it deletes every draft not confirmed. */
  batchId: string;
  items: ImportedMenuItem[];
  skipped: number;
  selected: ReadonlySet<string>;
}

const LINK_PROBLEM_TEXTS: Record<MenuLinkProblemCode, MessageKey> = {
  menu_link_invalid: "knowledge.import.errors.linkInvalid",
  menu_link_unreachable: "knowledge.import.errors.linkUnreachable",
  menu_link_unreadable: "knowledge.import.errors.linkUnreadable",
};

const CONFIDENCE: Record<ConfidenceLevel, { tone: BadgeTone; label: MessageKey }> = {
  high: { tone: "success", label: "knowledge.import.confidence.high" },
  medium: { tone: "warning", label: "knowledge.import.confidence.medium" },
  low: { tone: "danger", label: "knowledge.import.confidence.low" },
};

/** Reads a chosen file as base64 (without the data URL prefix). */
function readAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(base64FromDataUrl(String(reader.result ?? "")));
    reader.onerror = () => reject(reader.error ?? new Error("The file could not be read."));
    reader.readAsDataURL(file);
  });
}

/**
 * Knowledge -> Import a menu: a photo, PDF, text file or link is read into
 * draft items (switched off); the owner checks them, fixes what is wrong and
 * adds the chosen ones. The rest of the import is discarded in one request
 * (DELETE …/knowledge/import/{batch_id}). A link the API cannot read is
 * explained by its reason code (not public, unreachable, unreadable).
 */
export function MenuImportScreen() {
  const { t, tp, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const kinds = useKnowledgeKinds();
  const inputId = useId();
  const fileInput = useRef<HTMLInputElement>(null);

  const [source, setSource] = useState<Source>("file");
  const [file, setFile] = useState<{ file: File; mediaType: string } | null>(null);
  const [fileError, setFileError] = useState<MessageKey | null>(null);
  const [link, setLink] = useState("");
  const [linkError, setLinkError] = useState<MessageKey | null>(null);
  const [isDragging, setDragging] = useState(false);
  const [isReading, setReading] = useState(false);
  const [readError, setReadError] = useState<unknown>(null);
  const [review, setReview] = useState<ImportReview | null>(null);
  const [editor, setEditor] = useState<{ key: number; target: KnowledgeEditorTarget } | null>(null);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [done, setDone] = useState<{ added: number } | null>(null);

  const importMenu = useApiMutation(
    (body: { media_type: string; data_base64?: string; url?: string }) =>
      api.POST("/v1/businesses/{business_id}/knowledge/import", {
        params: { path: { business_id: business.id } },
        body,
      }),
    { errorToast: false },
  );
  const confirm = useApiMutation((itemIds: string[]) =>
    api.POST("/v1/businesses/{business_id}/knowledge/import/confirm", {
      params: { path: { business_id: business.id } },
      body: { item_ids: itemIds },
    }),
  );
  const discardBatch = useApiMutation(
    (batchId: string) =>
      api.DELETE("/v1/businesses/{business_id}/knowledge/import/{batch_id}", {
        params: { path: { business_id: business.id, batch_id: batchId } },
      }),
    { errorToast: false },
  );

  // Leaving mid-review keeps the drafts switched off in the knowledge base: warn first.
  const isReviewing = review !== null && review.items.length > 0;
  useEffect(() => {
    if (!isReviewing) {
      return;
    }
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isReviewing]);

  const chooseFile = (chosen: File | undefined) => {
    setReadError(null);
    if (!chosen) {
      return;
    }
    const check = checkMenuFile(chosen);
    if (!check.ok) {
      setFile(null);
      setFileError(check.error);
      return;
    }
    setFileError(null);
    setFile({ file: chosen, mediaType: check.mediaType });
  };

  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragging(false);
    chooseFile(event.dataTransfer.files[0]);
  };

  const read = async (event: FormEvent) => {
    event.preventDefault();
    setReadError(null);
    let body: { media_type: string; data_base64?: string; url?: string };
    if (source === "file") {
      if (!file) {
        setFileError("knowledge.import.errors.fileRequired");
        return;
      }
      setReading(true);
      try {
        body = { media_type: file.mediaType, data_base64: await readAsBase64(file.file) };
      } catch {
        setReading(false);
        setFileError("knowledge.import.errors.fileUnreadable");
        return;
      }
    } else {
      const parsed = webLinkSchema.safeParse(link);
      if (!parsed.success) {
        setLinkError(link.trim() === "" ? "validation.required" : "validation.url");
        return;
      }
      setReading(true);
      body = { media_type: "text/html", url: parsed.data };
    }
    const result = await importMenu.run(body);
    setReading(false);
    if (!result.ok) {
      setReadError(result.error);
      return;
    }
    const items = result.data.items ?? [];
    setReview({
      batchId: result.data.batch_id,
      items,
      skipped: result.data.skipped_line_count ?? 0,
      selected: initialImportSelection(items),
    });
  };

  const addSelected = async () => {
    if (!review) {
      return;
    }
    const chosen = review.items.filter((item) => review.selected.has(item.item.id)).map((item) => item.item.id);
    const result = await confirm.run(chosen);
    if (!result.ok) {
      return;
    }
    // The confirmed items left the import; discarding it deletes the unticked rest.
    if (chosen.length < review.items.length) {
      const discarded = await discardBatch.run(review.batchId);
      if (!discarded.ok) {
        toast.show({ tone: "info", title: t("knowledge.import.someDraftsLeft") });
      }
    }
    toast.success(tp("knowledge.import.added", (result.data.activated_items ?? []).length));
    setDone({ added: (result.data.activated_items ?? []).length });
    setReview(null);
  };

  const discardAll = async () => {
    if (!review) {
      return;
    }
    const result = await discardBatch.run(review.batchId);
    setConfirmDiscard(false);
    if (!result.ok) {
      toast.show({ tone: "error", title: t("knowledge.import.discardFailed") });
      return;
    }
    toast.success(t("knowledge.import.discarded"));
    setReview(null);
  };

  const startOver = () => {
    setDone(null);
    setReview(null);
    setFile(null);
    setLink("");
    setReadError(null);
    if (fileInput.current) {
      fileInput.current.value = "";
    }
  };

  const updateDraft = (saved: KnowledgeItemDetails) =>
    setReview((current) =>
      current
        ? {
            ...current,
            items: current.items.map((entry) =>
              entry.item.id === saved.id
                ? {
                    ...entry,
                    is_currency_mismatch: entry.is_currency_mismatch && (saved.price_minor === null || saved.price_minor === undefined),
                    item: {
                      id: saved.id,
                      kind: saved.kind,
                      title: saved.title,
                      body: saved.body,
                      price_minor: saved.price_minor,
                      currency_code: saved.currency_code,
                      duration_minutes: saved.duration_minutes,
                      formatted_price: saved.formatted_price,
                      tags: saved.tags,
                    },
                  }
                : entry,
            ),
          }
        : current,
    );

  const linkProblem = source === "link" ? menuLinkProblem(readError) : null;
  const readFailure =
    readError && !linkProblem
      ? describeError(readError, t, { external_service_error: "knowledge.import.errors.service" })
      : null;

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
          isSaving={confirm.isPending || discardBatch.isPending}
          onToggle={(id, checked) =>
            setReview((current) => {
              if (!current) {
                return current;
              }
              const selected = new Set(current.selected);
              if (checked) {
                selected.add(id);
              } else {
                selected.delete(id);
              }
              return { ...current, selected };
            })
          }
          onSelectAll={(checked) =>
            setReview((current) =>
              current ? { ...current, selected: checked ? new Set(current.items.map((item) => item.item.id)) : new Set() } : current,
            )
          }
          onEdit={(entry) =>
            setEditor((current) => ({
              key: (current?.key ?? 0) + 1,
              target: { mode: "edit", id: entry.item.id, item: { ...entry.item, is_active: false } },
            }))
          }
          onAdd={() => void addSelected()}
          onDiscard={() => setConfirmDiscard(true)}
          onStartOver={startOver}
        />
        {editor ? (
          <KnowledgeItemEditor
            key={editor.key}
            target={editor.target}
            kinds={kinds}
            showActiveToggle={false}
            onClose={() => setEditor(null)}
            onSaved={(saved) => {
              updateDraft(saved);
              setEditor(null);
            }}
          />
        ) : null}
        <ConfirmDialog
          open={confirmDiscard}
          title={t("knowledge.import.discardTitle")}
          description={tp("knowledge.import.discardDescription", review.items.length)}
          confirmLabel={t("knowledge.import.discard")}
          isPending={discardBatch.isPending}
          onConfirm={() => void discardAll()}
          onClose={() => setConfirmDiscard(false)}
        />
      </>
    );
  }

  return (
    <Card title={t("knowledge.import.title")} description={t("knowledge.import.description")}>
      <form onSubmit={(event) => void read(event)} noValidate className="space-y-5">
        <fieldset className="space-y-2">
          <legend className="mb-2 text-sm font-medium text-ink">{t("knowledge.import.sourceLabel")}</legend>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <Radio
              id={`${inputId}-source-file`}
              name="menu-source"
              label={t("knowledge.import.sourceFile")}
              checked={source === "file"}
              onChange={() => {
                setSource("file");
                setReadError(null);
              }}
            />
            <Radio
              id={`${inputId}-source-link`}
              name="menu-source"
              label={t("knowledge.import.sourceLink")}
              checked={source === "link"}
              onChange={() => {
                setSource("link");
                setReadError(null);
              }}
            />
          </div>
        </fieldset>

        {source === "file" ? (
          <div className="space-y-2">
            <label
              htmlFor={inputId}
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              className={cn(
                "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors",
                "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-focus",
                isDragging ? "border-accent-solid bg-accent-soft" : "border-line-strong hover:border-ink-subtle hover:bg-surface-muted/60",
                fileError ? "border-danger" : null,
              )}
            >
              {file ? <IconFile className="size-8 text-accent" aria-hidden /> : <IconUpload className="size-8 text-ink-subtle" aria-hidden />}
              {file ? (
                <span className="max-w-full space-y-0.5">
                  <span className="block truncate text-sm font-medium text-ink">{file.file.name}</span>
                  <span className="block text-sm text-ink-muted">
                    {formatFileSize(file.file.size, locale)} · {t("knowledge.import.chooseAnother")}
                  </span>
                </span>
              ) : (
                <span className="space-y-0.5">
                  <span className="block text-sm font-medium text-ink">{t("knowledge.import.dropTitle")}</span>
                  <span className="block text-sm text-ink-muted">{t("knowledge.import.dropHint")}</span>
                </span>
              )}
              <input
                ref={fileInput}
                id={inputId}
                type="file"
                accept={MENU_UPLOAD_ACCEPT}
                className="sr-only"
                aria-describedby={fileError ? `${inputId}-error` : `${inputId}-hint`}
                aria-invalid={fileError ? true : undefined}
                onChange={(event) => chooseFile(event.target.files?.[0])}
              />
            </label>
            {fileError ? (
              <p id={`${inputId}-error`} className="text-sm text-danger">
                {t(fileError)}
              </p>
            ) : null}
            <p id={`${inputId}-hint`} className="text-sm text-ink-muted">
              {t("knowledge.import.fileHint")}
            </p>
          </div>
        ) : (
          <Field label={t("knowledge.import.link")} hint={t("knowledge.import.linkHint")} error={linkError && t(linkError)} required>
            {(control) => (
              <Input
                {...control}
                type="url"
                inputMode="url"
                autoComplete="url"
                placeholder="https://"
                value={link}
                onChange={(event) => {
                  setLink(event.target.value);
                  setLinkError(null);
                }}
              />
            )}
          </Field>
        )}

        {linkProblem ? (
          <Alert tone="danger" title={t("knowledge.import.errors.readFailed")}>
            {linkProblem.status !== null
              ? t("knowledge.import.errors.linkHttpStatus", { status: linkProblem.status })
              : t(LINK_PROBLEM_TEXTS[linkProblem.code])}
          </Alert>
        ) : null}
        {readFailure ? (
          <Alert tone="danger" title={t("knowledge.import.errors.readFailed")}>
            {[readFailure.title, readFailure.detail, readFailure.requestId ? t("common.requestId", { id: readFailure.requestId }) : null]
              .filter(Boolean)
              .join(" ")}
          </Alert>
        ) : null}

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" isLoading={isReading} loadingText={t("knowledge.import.reading")} leadingIcon={source === "file" ? <IconUpload className="size-4" aria-hidden /> : <IconLink className="size-4" aria-hidden />}>
            {t("knowledge.import.read")}
          </Button>
          {isReading ? <p className="text-sm text-ink-muted" role="status">{t("knowledge.import.readingHint")}</p> : null}
        </div>
        <p className="text-sm text-ink-subtle">{t("knowledge.import.draftsNote")}</p>
      </form>
    </Card>
  );
}

function ImportReviewCard({
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
  const { t, tp, locale } = useI18n();
  const format = useBusinessFormat();
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
        {review.items.map((entry) => {
          const level = confidenceLevel(entry.confidence);
          const checkboxId = `import-${entry.item.id}`;
          const price =
            entry.item.price_minor !== null && entry.item.price_minor !== undefined ? format.money(entry.item.price_minor) : null;
          return (
            <li key={entry.item.id} className={cn("flex items-start gap-3 px-4 py-4 sm:px-6", !review.selected.has(entry.item.id) && "bg-surface-muted/40")}>
              <input
                id={checkboxId}
                type="checkbox"
                className="mt-1 size-4 shrink-0 rounded border-line-strong accent-[var(--accent-solid)]"
                checked={review.selected.has(entry.item.id)}
                onChange={(event) => onToggle(entry.item.id, event.target.checked)}
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <label htmlFor={checkboxId} className="cursor-pointer font-medium break-words text-ink" dir="auto">
                    {entry.item.title}
                  </label>
                  <Badge>{t(KIND_LABELS[entry.item.kind])}</Badge>
                  <Badge tone={CONFIDENCE[level].tone}>
                    {t(CONFIDENCE[level].label, {
                      percent: new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 0 }).format(entry.confidence),
                    })}
                  </Badge>
                </div>
                {entry.item.body ? (
                  <p className="mt-1 line-clamp-2 text-sm break-words text-ink-muted" dir="auto">
                    {entry.item.body}
                  </p>
                ) : null}
                <p className="mt-1.5 text-sm text-ink-subtle">
                  {price ?? (entry.is_currency_mismatch ? null : t("knowledge.import.noPrice"))}
                  {entry.item.duration_minutes ? ` · ${t("knowledge.items.minutes", { count: entry.item.duration_minutes })}` : null}
                </p>
                {entry.is_currency_mismatch ? (
                  <p className="mt-1.5 text-sm text-warning">
                    {t("knowledge.import.currencyMismatch", {
                      price: `${entry.printed_price ?? ""} ${entry.printed_currency_code ?? ""}`.trim(),
                      currency: format.currency,
                    })}
                  </p>
                ) : null}
              </div>
              <Button
                variant="ghost"
                size="sm"
                leadingIcon={<IconPencil className="size-4" aria-hidden />}
                aria-label={`${t("common.edit")}: ${entry.item.title}`}
                onClick={() => onEdit(entry)}
              >
                <span className="hidden sm:inline">{t("common.edit")}</span>
              </Button>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
