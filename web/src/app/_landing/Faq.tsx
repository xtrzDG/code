import { IconChevronDown } from "@/components/icons";
import { Reveal } from "@/components/siteMotion";
import type { MessageKey, Translator } from "@/i18n/translate";

import { Section } from "./Section";

export const FAQ_QUESTIONS: [MessageKey, MessageKey][] = [
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
      {/* landing-faq: answers open smoothly where the browser can animate to auto height. */}
      <Reveal depth={1} amount={0.15} className="landing-faq divide-y divide-line rounded-2xl border border-line bg-surface">
        {FAQ_QUESTIONS.map(([question, answer]) => (
          <details key={question} className="group px-5 sm:px-6">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-5 text-base font-medium text-ink [&::-webkit-details-marker]:hidden">
              {t(question)}
              <IconChevronDown
                className="size-4 shrink-0 text-ink-subtle transition-transform duration-(--motion-spring-snappy) ease-spring-snappy group-open:rotate-180"
                aria-hidden
              />
            </summary>
            <p className="-mt-1 pb-5 text-sm text-pretty text-ink-muted">{t(answer)}</p>
          </details>
        ))}
      </Reveal>
    </Section>
  );
}
