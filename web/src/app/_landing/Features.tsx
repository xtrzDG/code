import type { ComponentType } from "react";

import {
  IconBook,
  IconCalendar,
  IconChat,
  IconGlobe,
  IconHandoff,
  IconInbox,
  type IconProps,
} from "@/components/icons";
import { Stagger, StaggerItem } from "@/components/siteMotion";
import type { MessageKey, Translator } from "@/i18n/translate";

import { IconTile, Section } from "./Section";

const FEATURES: { icon: ComponentType<IconProps>; title: MessageKey; text: MessageKey }[] = [
  { icon: IconChat, title: "landing.features.answerTitle", text: "landing.features.answerText" },
  { icon: IconGlobe, title: "landing.features.languageTitle", text: "landing.features.languageText" },
  { icon: IconCalendar, title: "landing.features.bookTitle", text: "landing.features.bookText" },
  { icon: IconBook, title: "landing.features.knowTitle", text: "landing.features.knowText" },
  { icon: IconInbox, title: "landing.features.leadsTitle", text: "landing.features.leadsText" },
  { icon: IconHandoff, title: "landing.features.handoffTitle", text: "landing.features.handoffText" },
];

/** What the assistant does, in six short blocks arriving one after another. */
export function Features({ t }: { t: Translator["t"] }) {
  return (
    <Section id="features" title={t("landing.features.title")}>
      <Stagger as="ul" className="grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, text }) => (
          <StaggerItem as="li" key={title} className="flex gap-4">
            <IconTile>
              <Icon className="size-[1.125rem]" />
            </IconTile>
            <div className="space-y-1.5">
              <h3 className="text-base font-semibold tracking-tight text-ink">{t(title)}</h3>
              <p className="text-sm text-pretty text-ink-muted">{t(text)}</p>
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}
