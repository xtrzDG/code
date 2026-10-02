"use client";

import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import type { Schema } from "@/api/types";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconPencil, IconSearch } from "@/components/content/icons";
import { IconX } from "@/components/icons";
import { Button, Card, Field, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";

import { KIND_LABELS } from "../hooks";

type KnowledgeItemView = Schema<"KnowledgeItemView">;

const SEARCH_LIMIT = 10;

/**
 * "What does the assistant find for this question?": the same search its
 * search_knowledge tool runs, in a customer language.
 */
export function KnowledgeSearch({ onOpen }: { onOpen: (itemId: string) => void }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState(business.default_language);
  const [searched, setSearched] = useState<{ query: string; items: KnowledgeItemView[] } | null>(null);

  const search = useApiMutation((text: string, searchLanguage: string) =>
    api.POST("/v1/businesses/{business_id}/knowledge/search", {
      params: { path: { business_id: business.id } },
      body: { query: text, language: searchLanguage, limit: SEARCH_LIMIT },
    }),
  );

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const text = query.trim();
    if (text === "") {
      setSearched(null);
      return;
    }
    const result = await search.run(text, language);
    if (result.ok) {
      setSearched({ query: text, items: result.data.items ?? [] });
    }
  };

  return (
    <Card title={t("knowledge.search.title")} description={t("knowledge.search.description")}>
      <form onSubmit={(event) => void submit(event)} className="flex flex-col gap-3 sm:flex-row sm:items-end" role="search">
        <Field label={t("knowledge.search.query")} className="min-w-0 flex-1">
          {(control) => (
            <Input
              {...control}
              type="search"
              dir="auto"
              value={query}
              maxLength={500}
              placeholder={t("knowledge.search.placeholder")}
              onChange={(event) => setQuery(event.target.value)}
            />
          )}
        </Field>
        <div className="flex items-end gap-3">
          {business.languages.length > 1 ? (
            <Field label={t("knowledge.search.language")} className="min-w-0 flex-1 sm:w-48 sm:flex-none">
              {(control) => (
                <Select {...control} value={language} onChange={(event) => setLanguage(event.target.value)}>
                  {business.languages.map((tag) => (
                    <option key={tag} value={tag}>
                      {languageName(tag, locale)}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          ) : null}
          <Button type="submit" variant="secondary" isLoading={search.isPending} leadingIcon={<IconSearch className="size-4" aria-hidden />}>
            {t("common.search")}
          </Button>
        </div>
      </form>

      {searched ? (
        <div className="mt-5 space-y-3" aria-live="polite">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium text-ink">
              {searched.items.length > 0
                ? t("knowledge.search.resultsFor", { query: searched.query })
                : t("knowledge.search.nothingFor", { query: searched.query })}
            </p>
            <Button variant="ghost" size="sm" leadingIcon={<IconX className="size-4" aria-hidden />} onClick={() => setSearched(null)}>
              {t("knowledge.search.clear")}
            </Button>
          </div>
          {searched.items.length === 0 ? (
            <p className="text-sm text-ink-muted">{t("knowledge.search.nothingHint")}</p>
          ) : (
            <ol className="divide-y divide-line rounded-xl border border-line">
              {searched.items.map((item, index) => (
                <li key={item.id} className="flex items-start gap-3 px-4 py-3">
                  <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent-ink">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium break-words text-ink" dir="auto">
                      {item.title}
                    </p>
                    <p className="text-sm text-ink-subtle">
                      {[t(KIND_LABELS[item.kind]), item.price_minor !== null && item.price_minor !== undefined ? format.money(item.price_minor) : null]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </div>
                  <Button variant="ghost" size="sm" aria-label={`${t("common.edit")}: ${item.title}`} onClick={() => onOpen(item.id)}>
                    <IconPencil className="size-4" aria-hidden />
                  </Button>
                </li>
              ))}
            </ol>
          )}
        </div>
      ) : null}
    </Card>
  );
}
