"use client";

/**
 * The item's names in the business's other languages, as chips under one
 * heading per language: the owner's names (solid, removable) and the
 * model's suggestions (dashed, accept or remove), with a field per
 * language to type one more. Enter in that field adds the name instead of
 * submitting the editor's form. Nothing is saved until the editor is.
 */

import { useId, useState, type KeyboardEvent } from "react";

import { IconCheck, IconPlus, IconSparkles, IconX } from "@/components/icons";
import { Button, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { languageName } from "@/lib/format";
import { acceptAlias, addAlias, MAX_ALIAS_LENGTH, removeAlias, type AliasRow } from "@/lib/knowledge/aliases";

/** The model's suggestions for a stored item: none while its title has unsaved changes. */
export interface AliasSuggestAction {
  onSuggest: () => void;
  isPending: boolean;
  /** Why it cannot be asked now (shown instead of asking), or null. */
  blockedReason: string | null;
}

export function AliasChips({
  languages,
  rows,
  onChange,
  suggest,
}: {
  languages: readonly string[];
  rows: readonly AliasRow[];
  onChange: (rows: AliasRow[]) => void;
  suggest?: AliasSuggestAction;
}) {
  const { t, locale } = useI18n();
  const id = useId();
  const [typed, setTyped] = useState<Record<string, string>>({});
  const [problems, setProblems] = useState<Record<string, MessageKey | undefined>>({});
  const hasSuggestions = rows.some((row) => row.status === "suggested");

  const add = (language: string) => {
    const result = addAlias(rows, language, typed[language] ?? "");
    if (!result.ok) {
      setProblems((current) => ({ ...current, [language]: result.error }));
      return;
    }
    onChange(result.rows);
    setTyped((current) => ({ ...current, [language]: "" }));
  };

  const onKeyDown = (language: string) => (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !event.nativeEvent.isComposing) {
      event.preventDefault();
      add(language);
    }
  };

  return (
    <section aria-labelledby={`${id}-title`} className="space-y-4 sm:col-span-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 max-w-prose">
          <h3 id={`${id}-title`} className="text-sm font-medium text-ink">
            {t("knowledge.aliases.title")}
          </h3>
          <p className="mt-1 text-sm text-ink-muted">{t("knowledge.aliases.hint")}</p>
        </div>
        {suggest ? (
          <Button
            variant="secondary"
            size="sm"
            leadingIcon={<IconSparkles className="size-4" aria-hidden />}
            isLoading={suggest.isPending}
            loadingText={t("knowledge.aliases.suggesting")}
            disabled={suggest.blockedReason !== null}
            aria-describedby={suggest.blockedReason ? `${id}-blocked` : undefined}
            onClick={suggest.onSuggest}
          >
            {t("knowledge.aliases.suggest")}
          </Button>
        ) : null}
      </div>
      {suggest?.blockedReason ? (
        <p id={`${id}-blocked`} className="text-xs text-ink-subtle">
          {suggest.blockedReason}
        </p>
      ) : null}
      {hasSuggestions ? <p className="text-xs text-ink-subtle">{t("knowledge.aliases.suggestedHint")}</p> : null}

      <div className="grid gap-4 md:grid-cols-2">
        {languages.map((language) => {
          const name = languageName(language, locale);
          const headingId = `${id}-${language}-name`;
          const inputId = `${id}-${language}-input`;
          const errorId = `${id}-${language}-error`;
          const problem = problems[language];
          const here = rows.map((row, index) => ({ row, index })).filter(({ row }) => row.language === language);
          return (
            <div
              key={language}
              role="group"
              aria-labelledby={headingId}
              className="min-w-0 space-y-2 rounded-xl border border-line p-3"
              data-alias-language={language}
            >
              <p id={headingId} className="text-xs font-medium tracking-wide text-ink-subtle uppercase">
                {name}
              </p>
              {here.length === 0 ? (
                <p className="text-sm text-ink-muted">{t("knowledge.aliases.none", { language: name })}</p>
              ) : (
                <ul
                  className="flex flex-wrap gap-1.5"
                  aria-label={t("knowledge.aliases.listLabel", {
                    language: name,
                  })}
                >
                  {here.map(({ row, index }) => (
                    <AliasChip
                      key={`${row.language}-${row.text}`}
                      row={row}
                      suggestedLabel={t("knowledge.aliases.suggested")}
                      acceptLabel={t("knowledge.aliases.accept", {
                        text: row.text,
                      })}
                      removeLabel={t("knowledge.aliases.remove", {
                        text: row.text,
                      })}
                      onAccept={() => onChange(acceptAlias(rows, index))}
                      onRemove={() => onChange(removeAlias(rows, index))}
                    />
                  ))}
                </ul>
              )}
              <label htmlFor={inputId} className="sr-only">
                {t("knowledge.aliases.placeholder", { language: name })}
              </label>
              <div className="flex gap-2">
                <Input
                  id={inputId}
                  dir="auto"
                  lang={language}
                  value={typed[language] ?? ""}
                  maxLength={MAX_ALIAS_LENGTH + 8}
                  placeholder={t("knowledge.aliases.placeholder", {
                    language: name,
                  })}
                  aria-invalid={problem ? true : undefined}
                  aria-describedby={problem ? errorId : undefined}
                  onKeyDown={onKeyDown(language)}
                  onChange={(event) => {
                    setTyped((current) => ({
                      ...current,
                      [language]: event.target.value,
                    }));
                    setProblems((current) => ({
                      ...current,
                      [language]: undefined,
                    }));
                  }}
                />
                {/* Named for its language: the dialog has its own "Add" (save) button. */}
                <Button
                  variant="secondary"
                  aria-label={t("knowledge.aliases.addLabel", { language: name })}
                  leadingIcon={<IconPlus className="size-4" aria-hidden />}
                  onClick={() => add(language)}
                >
                  {t("knowledge.aliases.add")}
                </Button>
              </div>
              {problem ? (
                <p id={errorId} className="text-xs text-danger" role="alert">
                  {t(problem)}
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function AliasChip({
  row,
  suggestedLabel,
  acceptLabel,
  removeLabel,
  onAccept,
  onRemove,
}: {
  row: AliasRow;
  suggestedLabel: string;
  acceptLabel: string;
  removeLabel: string;
  onAccept: () => void;
  onRemove: () => void;
}) {
  const isSuggested = row.status === "suggested";
  const iconButton =
    "flex size-7 shrink-0 cursor-pointer items-center justify-center rounded-full text-ink-subtle hover:bg-surface hover:text-ink focus-visible:outline-2 focus-visible:outline-focus pointer-coarse:size-9";
  return (
    <li
      data-alias-status={row.status}
      className={
        isSuggested
          ? "flex min-w-0 max-w-full items-center gap-1 rounded-full border border-dashed border-accent bg-accent-soft/60 py-0.5 ps-2.5 pe-1 text-sm text-ink"
          : "flex min-w-0 max-w-full items-center gap-1 rounded-full bg-surface-muted py-0.5 ps-2.5 pe-1 text-sm text-ink"
      }
    >
      <span className="min-w-0 truncate" dir="auto" lang={row.language} data-user-content>
        {row.text}
      </span>
      {isSuggested ? (
        <>
          <span className="shrink-0 text-xs text-accent-ink">{suggestedLabel}</span>
          <button type="button" aria-label={acceptLabel} title={acceptLabel} onClick={onAccept} className={iconButton}>
            <IconCheck className="size-3.5" aria-hidden />
          </button>
        </>
      ) : null}
      <button type="button" aria-label={removeLabel} title={removeLabel} onClick={onRemove} className={iconButton}>
        <IconX className="size-3.5" aria-hidden />
      </button>
    </li>
  );
}
