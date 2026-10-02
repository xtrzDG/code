import type { ComponentType } from "react";

import { IconChat, IconGlobe, IconPhone, type IconProps } from "@/components/icons";
import type { MessageKey, Translator } from "@/i18n/translate";

import { IconTile, Section } from "./Section";

const CHANNELS: { kind: string; name: MessageKey; text: MessageKey; icon: ComponentType<IconProps> }[] = [
  { kind: "phone", name: "channels.kinds.phone", text: "landing.channels.phone", icon: IconPhone },
  { kind: "whatsapp", name: "channels.kinds.whatsapp", text: "landing.channels.whatsapp", icon: IconChat },
  { kind: "instagram", name: "channels.kinds.instagram", text: "landing.channels.instagram", icon: IconChat },
  { kind: "messenger", name: "channels.kinds.messenger", text: "landing.channels.messenger", icon: IconChat },
  { kind: "telegram", name: "channels.kinds.telegram", text: "landing.channels.telegram", icon: IconChat },
  { kind: "web_chat", name: "channels.kinds.web_chat", text: "landing.channels.web_chat", icon: IconGlobe },
];

/** The six customer channels, one assistant behind them. */
export function Channels({ t }: { t: Translator["t"] }) {
  return (
    <Section id="channels" title={t("landing.channels.title")} subtitle={t("landing.channels.subtitle")}>
      <ul className="grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
        {CHANNELS.map(({ kind, name, text, icon: Icon }) => (
          <li key={kind} className="flex items-center gap-4 bg-surface p-5">
            <IconTile>
              <Icon className="size-[1.125rem]" />
            </IconTile>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-ink">{t(name)}</p>
              <p className="text-sm text-ink-muted">{t(text)}</p>
            </div>
          </li>
        ))}
      </ul>
    </Section>
  );
}
