"use client";

import { IconFile, IconUpload } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatFileSize, MENU_UPLOAD_ACCEPT } from "@/lib/knowledge/menuImport";

import type { MenuSource } from "../_lib/useMenuSource";

/** The drop zone (and hidden file input) for a menu photo, PDF or text file. */
export function MenuFileDrop({ source }: { source: MenuSource }) {
  const { t, locale } = useI18n();
  const { inputId, file, fileError, isDragging, setDragging, onDrop, chooseFile, fileInput } = source;

  return (
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
  );
}
