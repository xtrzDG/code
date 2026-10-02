import type { Translator } from "@/i18n/translate";

import { Section } from "./Section";

const STEPS = [
  ["landing.steps.profileTitle", "landing.steps.profileText"],
  ["landing.steps.testTitle", "landing.steps.testText"],
  ["landing.steps.connectTitle", "landing.steps.connectText"],
] as const;

/** How it works: profile, test and publish, connect. */
export function Steps({ t }: { t: Translator["t"] }) {
  return (
    <Section id="how" title={t("landing.steps.title")} subtitle={t("landing.steps.subtitle")}>
      <ol className="grid gap-4 md:grid-cols-3">
        {STEPS.map(([title, text], index) => (
          <li key={title} className="rounded-2xl border border-line bg-surface p-6">
            <span
              className="flex size-8 items-center justify-center rounded-full border border-line bg-surface-muted text-sm font-semibold text-accent tabular-nums"
              aria-hidden
            >
              {index + 1}
            </span>
            <h3 className="mt-5 text-base font-semibold tracking-tight text-ink">{t(title)}</h3>
            <p className="mt-2 text-sm text-pretty text-ink-muted">{t(text)}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}
