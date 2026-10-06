import { Stagger, StaggerItem } from "@/components/motion";
import type { Translator } from "@/i18n/translate";
import { cn } from "@/lib/cn";

const FACTS = [
  ["landing.facts.alwaysTitle", "landing.facts.alwaysText"],
  ["landing.facts.channelsTitle", "landing.facts.channelsText"],
  ["landing.facts.languagesTitle", "landing.facts.languagesText"],
  ["landing.facts.peopleTitle", "landing.facts.peopleText"],
] as const;

/** Four short facts under the hero, in one hairline grid; they arrive one after another. */
export function Facts({ t }: { t: Translator["t"] }) {
  return (
    <section aria-label={t("landing.facts.label")} className="border-t border-line">
      <Stagger as="dl" className="mx-auto grid w-full max-w-6xl grid-cols-2 lg:grid-cols-4">
        {FACTS.map(([title, text], index) => (
          <StaggerItem
            key={title}
            // Hairlines between the cells: two columns on phones, four in a row on large screens.
            className={cn(
              "space-y-1 border-line px-4 py-8 sm:px-6",
              index % 2 === 1 && "border-s",
              index >= 2 && "border-t lg:border-t-0",
              index === 2 && "lg:border-s",
            )}
          >
            <dt className="text-base font-semibold tracking-tight text-ink sm:text-lg">{t(title)}</dt>
            <dd className="text-sm text-ink-muted">{t(text)}</dd>
          </StaggerItem>
        ))}
      </Stagger>
    </section>
  );
}
