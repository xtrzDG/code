import { Stagger, StaggerItem } from "@/components/motion";
import type { Translator } from "@/i18n/translate";
import { cn } from "@/lib/cn";

import { Section } from "./Section";

const STEPS = [
  ["landing.steps.profileTitle", "landing.steps.profileText"],
  ["landing.steps.testTitle", "landing.steps.testText"],
  ["landing.steps.connectTitle", "landing.steps.connectText"],
] as const;

/** On wide screens the outer cards turn towards the middle, like the walls of a corridor leading in. */
const CORRIDOR = [
  "md:origin-right md:[transform:perspective(1100px)_rotateY(16deg)]",
  "md:[transform:perspective(1100px)_translateZ(-40px)]",
  "md:origin-left md:[transform:perspective(1100px)_rotateY(-16deg)]",
];

/** How it works: profile, test and publish, connect; the steps come out of the depth one by one. */
export function Steps({ t }: { t: Translator["t"] }) {
  return (
    <Section id="how" title={t("landing.steps.title")} subtitle={t("landing.steps.subtitle")} glow="left">
      <Stagger as="ol" step={0.14} className="grid gap-4 md:grid-cols-3">
        {STEPS.map(([title, text], index) => (
          <StaggerItem as="li" key={title} depth={1}>
            <div className={cn("h-full rounded-2xl border border-line bg-surface p-6 shadow-lg", CORRIDOR[index])}>
              <span
                className="flex size-9 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent-ink tabular-nums ring-1 ring-accent/30"
                aria-hidden
              >
                {index + 1}
              </span>
              <h3 className="mt-5 text-base font-semibold tracking-tight text-ink">{t(title)}</h3>
              <p className="mt-2 text-sm text-pretty text-ink-muted">{t(text)}</p>
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}
