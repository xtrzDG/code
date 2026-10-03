"use client";

/**
 * The new assistant as a card: the business's name with a "Live" light,
 * the languages it speaks and where customers reach it. It rises out of
 * the tunnel with a slight tilt (just a fade with reduced motion).
 */

import { useReducedMotion } from "motion/react";
import * as m from "motion/react-m";

import { CHANNEL_NAMES } from "@/components/workspace/channelNames";
import type { Schema } from "@/api/types";
import { IconSparkles } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { EASINGS } from "@/lib/motion";

export function AssistantCard({
  name,
  languages,
  channels,
}: {
  name: string;
  languages: readonly string[];
  channels: readonly Schema<"ChannelKind">[];
}) {
  const { t, locale } = useI18n();
  const isReduced = useReducedMotion();

  return (
    <m.div
      initial={isReduced ? { opacity: 0 } : { opacity: 0, y: 60, rotateX: 24, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, rotateX: 0, scale: 1 }}
      transition={{ duration: isReduced ? 0.2 : 0.9, ease: [...EASINGS.emphasized], delay: isReduced ? 0 : 0.25 }}
      className="relative overflow-hidden rounded-3xl border border-accent/40 bg-surface/90 p-6 shadow-[0_40px_120px_-50px_var(--accent-solid)] backdrop-blur-md sm:p-7"
    >
      <span aria-hidden className="pointer-events-none absolute -end-16 -top-16 size-48 rounded-full bg-accent-solid/20 blur-3xl" />
      <div className="relative flex items-start gap-4">
        <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-accent-solid text-on-accent shadow-[0_12px_30px_-12px_var(--accent-solid)]" aria-hidden>
          <IconSparkles className="size-6" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xl font-semibold text-ink" dir="auto">
            {name}
          </p>
          <p className="mt-1 inline-flex items-center gap-2 rounded-full bg-success-soft px-2.5 py-0.5 text-xs font-semibold text-success">
            <span className="relative flex size-2" aria-hidden>
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-60 motion-reduce:animate-none" />
              <span className="relative inline-flex size-2 rounded-full bg-success" />
            </span>
            {t("tunnelLaunch.finale.live")}
          </p>
        </div>
      </div>
      <dl className="relative mt-6 grid gap-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-ink-subtle">{t("tunnelLaunch.finale.speaks")}</dt>
          <dd className="mt-1 font-medium text-ink">{languages.map((tag) => languageName(tag, locale)).join(", ")}</dd>
        </div>
        <div>
          <dt className="text-ink-subtle">{t("tunnelLaunch.finale.answersIn")}</dt>
          <dd className="mt-1 font-medium text-ink">
            {channels.length > 0 ? channels.map((kind) => t(CHANNEL_NAMES[kind])).join(", ") : t("tunnelLaunch.finale.webChat")}
          </dd>
        </div>
      </dl>
    </m.div>
  );
}
