import type { ComponentType } from "react";

import { IconCard, IconGlobe, IconPhone, type IconProps } from "@/components/icons";
import { Stagger, StaggerItem, TiltCard } from "@/components/motion";
import { TILT_DEGREES } from "@/lib/motion";
import type { MessageKey, Translator } from "@/i18n/translate";

import { IconTile, Section } from "./Section";

const POINTS: { icon: ComponentType<IconProps>; title: MessageKey; text: MessageKey }[] = [
  { icon: IconPhone, title: "landing.world.phoneTitle", text: "landing.world.phoneText" },
  { icon: IconGlobe, title: "landing.world.languageTitle", text: "landing.world.languageText" },
  { icon: IconCard, title: "landing.world.currencyTitle", text: "landing.world.currencyText" },
];

/** Any country: phone numbers, customer languages, currency and time zone. */
export function World({ t, countryCount }: { t: Translator["t"]; countryCount: number }) {
  return (
    <Section id="world" title={t("landing.world.title")} subtitle={t("landing.world.subtitle")} glow="left">
      <Stagger as="ul" className="grid gap-4 md:grid-cols-3">
        {POINTS.map(({ icon: Icon, title, text }) => (
          <StaggerItem as="li" key={title} depth={1}>
            <TiltCard maxDegrees={TILT_DEGREES.subtle} className="h-full space-y-4 rounded-2xl border border-line bg-surface p-6">
              <IconTile>
                <Icon className="size-[1.125rem]" />
              </IconTile>
              <h3 className="text-base font-semibold tracking-tight text-ink">{t(title)}</h3>
              <p className="text-sm text-pretty text-ink-muted">{t(text, { count: countryCount })}</p>
            </TiltCard>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}
