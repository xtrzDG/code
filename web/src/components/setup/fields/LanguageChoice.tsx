"use client";

/**
 * The languages the business's customers write in (chips to tick, the
 * country's usual ones first), which of them greets first, and the time
 * zone when the country has several.
 */

import type { LanguageOption } from "@/api/types";
import { Field, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { languageName } from "@/lib/format";

export function LanguageChoice({
  options,
  languages,
  defaultLanguage,
  onToggle,
  onDefault,
  error,
}: {
  options: readonly LanguageOption[];
  languages: readonly string[];
  defaultLanguage: string | undefined;
  onToggle: (tag: string, checked: boolean) => void;
  onDefault: (tag: string) => void;
  error?: string;
}) {
  const { t, locale } = useI18n();
  const nameOf = (tag: string) => options.find((option) => option.tag === tag)?.native_name ?? languageName(tag, locale);

  return (
    <div className="space-y-5">
      <fieldset aria-describedby={error ? "tunnel-languages-error" : undefined}>
        <legend className="text-sm font-medium text-ink">{t("tunnelBusiness.place.languages")}</legend>
        <p className="mt-1 text-sm text-ink-muted">{t("tunnelBusiness.place.languagesHint")}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {options.map((option) => {
            const checked = languages.includes(option.tag);
            return (
              <label
                key={option.tag}
                className={cn(
                  "inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-full border px-3.5 text-sm transition-colors",
                  "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-focus",
                  checked ? "border-accent bg-accent-soft text-accent-ink" : "border-line bg-surface/80 text-ink hover:border-line-strong",
                )}
              >
                <input
                  type="checkbox"
                  className="sr-only"
                  checked={checked}
                  onChange={(event) => onToggle(option.tag, event.target.checked)}
                />
                <span lang={option.tag} className="font-medium">
                  {option.native_name}
                </span>
                {option.display_name !== option.native_name ? <span className="text-xs text-ink-muted">{option.display_name}</span> : null}
              </label>
            );
          })}
        </div>
        {error ? (
          <p id="tunnel-languages-error" className="mt-2 text-sm text-danger" role="alert">
            {error}
          </p>
        ) : null}
      </fieldset>

      {languages.length > 1 ? (
        <Field label={t("tunnelBusiness.place.defaultLanguage")}>
          {(control) => (
            <Select {...control} value={defaultLanguage} onChange={(event) => onDefault(event.target.value)}>
              {languages.map((tag) => (
                <option key={tag} value={tag}>
                  {nameOf(tag)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      ) : null}
    </div>
  );
}
