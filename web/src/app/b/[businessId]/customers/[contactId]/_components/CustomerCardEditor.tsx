"use client";

/**
 * The team's card on a customer: tags (typed, or picked from the ones the
 * business already uses) and the VIP mark. Any member may change it; the
 * change shows at once and is undone if the API refuses.
 */

import { useId, useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import type { Query } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { Switch } from "@/components/content/Switch";
import { IconPlus, IconStar, IconX } from "@/components/icons";
import { Button, Card, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  cardOf,
  changedCard,
  cleanTag,
  MAX_TAG_LENGTH,
  tagProblem,
  tagSuggestions,
  withCard,
  type CardChange,
  type CustomerDetail,
} from "../../_lib/customerModel";

export function CustomerCardEditor({ detail, knownTags }: { detail: Query<CustomerDetail>; knownTags: readonly string[] }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const inputId = useId();
  const errorId = useId();
  const hintId = useId();
  const [typed, setTyped] = useState("");
  const [problem, setProblem] = useState<"tooLong" | "tooMany" | null>(null);
  const data = detail.data;
  const contactId = data?.contact.id ?? "";

  const change = useMutation(
    (body: CardChange) =>
      api.PATCH("/v1/businesses/{business_id}/contacts/{contact_id}/card", {
        params: { path: { business_id: business.id, contact_id: contactId } },
        body,
      }),
    {
      optimistic: (body) => {
        const before = detail.data;
        detail.setData((current) => (current ? withCard(current, changedCard(cardOf(current), body)) : current));
        return () => detail.setData(() => before);
      },
      stale: [queryKeys.customers.all(business.id)],
    },
  );

  if (!data) {
    return null;
  }
  const tags = data.contact.tags ?? [];
  const isErased = Boolean(data.contact.erased_at);
  const suggestions = tagSuggestions(knownTags, tags, typed);

  const run = async (body: CardChange) => {
    const result = await change.run(body);
    if (result.ok) {
      detail.setData((current) => (current ? withCard(current, result.data) : current));
    }
  };

  const addTag = (text: string) => {
    const found = tagProblem(text, tags);
    if (found === "tooLong" || found === "tooMany") {
      setProblem(found);
      return;
    }
    setProblem(null);
    setTyped("");
    if (found === null) {
      void run({ add_tags: [cleanTag(text)] });
    }
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    addTag(typed);
  };

  return (
    <Card title={t("customers.card.title")} description={t("customers.card.description")}>
      <div className="space-y-5">
        <div>
          <h3 className="text-sm font-medium text-ink">{t("customers.card.tags")}</h3>
          {tags.length === 0 ? (
            <p className="mt-1 text-sm text-ink-muted">{t("customers.card.noTags")}</p>
          ) : (
            <ul className="mt-2 flex flex-wrap gap-1.5" aria-label={t("customers.card.tags")}>
              {tags.map((tag) => (
                <li key={tag} className="flex items-center gap-1 rounded-full bg-surface-muted py-0.5 ps-2.5 pe-1 text-sm text-ink">
                  <span dir="auto">{tag}</span>
                  <button
                    type="button"
                    disabled={isErased}
                    aria-label={t("customers.card.removeTag", { tag })}
                    onClick={() => void run({ remove_tags: [tag] })}
                    className="flex size-6 cursor-pointer items-center justify-center rounded-full text-ink-subtle hover:bg-surface hover:text-ink"
                  >
                    <IconX className="size-3.5" aria-hidden />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {isErased ? null : (
          <form onSubmit={onSubmit} className="space-y-2">
            <label htmlFor={inputId} className="block text-sm font-medium text-ink">
              {t("customers.card.addTag")}
            </label>
            <div className="flex gap-2">
              <Input
                id={inputId}
                value={typed}
                maxLength={MAX_TAG_LENGTH + 8}
                placeholder={t("customers.card.tagPlaceholder")}
                aria-invalid={problem ? true : undefined}
                aria-describedby={problem ? errorId : suggestions.length > 0 ? hintId : undefined}
                onChange={(event) => {
                  setTyped(event.target.value);
                  setProblem(null);
                }}
              />
              <Button type="submit" variant="secondary" leadingIcon={<IconPlus className="size-4" aria-hidden />} disabled={cleanTag(typed) === ""}>
                {t("customers.card.add")}
              </Button>
            </div>
            {problem ? (
              <p id={errorId} className="text-xs text-danger" role="alert">
                {t(problem === "tooLong" ? "customers.card.tooLong" : "customers.card.tooMany")}
              </p>
            ) : null}
            {suggestions.length > 0 ? (
              <div>
                <p id={hintId} className="text-xs text-ink-subtle">
                  {t("customers.card.suggestions")}
                </p>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {suggestions.map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      dir="auto"
                      onClick={() => addTag(tag)}
                      className="motion-press cursor-pointer rounded-full border border-line px-2.5 py-0.5 text-xs text-ink-muted hover:border-line-strong hover:text-ink"
                    >
                      + {tag}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </form>
        )}

        <div className="flex items-start justify-between gap-4 border-t border-line pt-4">
          <div className="min-w-0">
            <p className="flex items-center gap-1.5 text-sm font-medium text-ink">
              <IconStar className="size-4 text-accent" aria-hidden />
              {t("customers.card.vip")}
            </p>
            <p className="mt-1 text-sm text-ink-muted">{t("customers.card.vipHint")}</p>
          </div>
          <Switch
            checked={data.contact.is_vip ?? false}
            disabled={isErased}
            label={t("customers.card.vip")}
            onChange={(checked) => void run({ is_vip: checked })}
          />
        </div>
      </div>
    </Card>
  );
}
