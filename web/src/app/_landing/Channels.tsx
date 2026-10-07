import { IconChannelMark } from "@/components/icons";
import { Reveal } from "@/components/siteMotion";
import type { MessageKey, Translator } from "@/i18n/translate";
import { CHANNEL_MARKS } from "@/lib/channelMarks";
import type { ChannelMarkKey } from "@/lib/heroScene";

import { Section } from "./Section";

const CHANNELS: { kind: ChannelMarkKey; name: MessageKey; text: MessageKey }[] = [
  { kind: "phone", name: "channels.kinds.phone", text: "landing.channels.phone" },
  { kind: "whatsapp", name: "channels.kinds.whatsapp", text: "landing.channels.whatsapp" },
  { kind: "instagram", name: "channels.kinds.instagram", text: "landing.channels.instagram" },
  { kind: "messenger", name: "channels.kinds.messenger", text: "landing.channels.messenger" },
  { kind: "telegram", name: "channels.kinds.telegram", text: "landing.channels.telegram" },
  { kind: "web_chat", name: "channels.kinds.web_chat", text: "landing.channels.web_chat" },
];

/** The channel's mark in white on its own colours, like the bubbles orbiting the hero's orb. */
function ChannelBadge({ kind }: { kind: ChannelMarkKey }) {
  const [from, to] = CHANNEL_MARKS[kind].colors;
  return (
    <span
      className="flex size-10 shrink-0 items-center justify-center rounded-xl text-white shadow-md"
      style={{ backgroundImage: `linear-gradient(135deg, ${from}, ${to})` }}
      aria-hidden
    >
      <IconChannelMark mark={kind} className="size-5" strokeWidth={1.9} />
    </span>
  );
}

/** The six customer channels, one assistant behind them. */
export function Channels({ t }: { t: Translator["t"] }) {
  return (
    <Section id="channels" title={t("landing.channels.title")} subtitle={t("landing.channels.subtitle")}>
      <Reveal depth={1} amount={0.2}>
        <ul className="grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          {CHANNELS.map(({ kind, name, text }) => (
            <li key={kind} className="group flex items-center gap-4 bg-surface p-5 transition-colors hover:bg-surface-muted/60">
              <span className="transition-transform duration-(--motion-spring-snappy) ease-spring-snappy group-hover:-translate-y-0.5 group-hover:scale-105">
                <ChannelBadge kind={kind} />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-ink">{t(name)}</p>
                <p className="text-sm text-ink-muted">{t(text)}</p>
              </div>
            </li>
          ))}
        </ul>
      </Reveal>
    </Section>
  );
}
