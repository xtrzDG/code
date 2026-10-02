"use client";

import { useRef } from "react";

import { IconPlus, IconTrash } from "@/components/icons";
import { Button, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";

const MAX_RULE_LENGTH = 300;
const MAX_RULES = 30;

/** An editable list of short rules (handoff, forbidden). */
export function RuleListEditor({
  label,
  rules,
  onChange,
  suggestions,
}: {
  label: string;
  rules: string[];
  onChange: (rules: string[]) => void;
  /** Niche defaults offered when the list is empty. */
  suggestions?: readonly string[];
}) {
  const { t } = useI18n();
  const listRef = useRef<HTMLUListElement>(null);

  const addRule = () => {
    onChange([...rules, ""]);
    // Focus the new, empty rule after it renders.
    requestAnimationFrame(() => listRef.current?.querySelector<HTMLInputElement>("li:last-child input")?.focus());
  };

  return (
    <div className="space-y-2">
      {rules.length > 0 ? (
        <ul ref={listRef} className="space-y-2">
          {rules.map((rule, index) => (
            <li key={index} className="flex items-center gap-2">
              <Input
                aria-label={`${label} ${index + 1}`}
                value={rule}
                maxLength={MAX_RULE_LENGTH}
                placeholder={t("onboarding.faq.rulePlaceholder")}
                onChange={(event) => onChange(rules.map((item, position) => (position === index ? event.target.value : item)))}
              />
              <Button
                variant="ghost"
                size="sm"
                aria-label={`${t("common.remove")}: ${rule || `${label} ${index + 1}`}`}
                onClick={() => onChange(rules.filter((_, position) => position !== index))}
              >
                <IconTrash className="size-4" aria-hidden />
              </Button>
            </li>
          ))}
        </ul>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          size="sm"
          leadingIcon={<IconPlus className="size-4" aria-hidden />}
          onClick={addRule}
          disabled={rules.length >= MAX_RULES}
        >
          {t("onboarding.faq.addRule")}
        </Button>
        {suggestions && suggestions.length > 0 && rules.every((rule) => rule.trim() === "") ? (
          <Button variant="ghost" size="sm" onClick={() => onChange([...suggestions])}>
            {t("onboarding.faq.useDefaults")}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
