import { IconChevronDown } from "@/components/icons";
import type { MessageKey, Translator } from "@/i18n/translate";

import { Section } from "./Section";

const QUESTIONS: [MessageKey, MessageKey][] = [
  ["landing.faq.aiQuestion", "landing.faq.aiAnswer"],
  ["landing.faq.unknownQuestion", "landing.faq.unknownAnswer"],
  ["landing.faq.numberQuestion", "landing.faq.numberAnswer"],
  ["landing.faq.languagesQuestion", "landing.faq.languagesAnswer"],
  ["landing.faq.setupQuestion", "landing.faq.setupAnswer"],
  ["landing.faq.dataQuestion", "landing.faq.dataAnswer"],
];

/** Frequent questions as native disclosure widgets (keyboard and screen reader friendly, no script). */
export function Faq({ t }: { t: Translator["t"] }) {
  return (
    <Section id="faq" title={t("landing.faq.title")}>
      <div className="divide-y divide-line rounded-2xl border border-line bg-surface">
        {QUESTIONS.map(([question, answer]) => (
          <details key={question} className="group px-5 sm:px-6">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-5 text-base font-medium text-ink [&::-webkit-details-marker]:hidden">
              {t(question)}
              <IconChevronDown className="size-4 shrink-0 text-ink-subtle transition-transform group-open:rotate-180" aria-hidden />
            </summary>
            <p className="-mt-1 pb-5 text-sm text-pretty text-ink-muted">{t(answer)}</p>
          </details>
        ))}
      </div>
    </Section>
  );
}
