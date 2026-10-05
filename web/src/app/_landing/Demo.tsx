import { IconCalendar, IconCheck, IconHandoff, IconSparkles, IconWhatsApp } from "@/components/icons";
import { Stagger, StaggerItem, TiltCard, TiltLayer } from "@/components/motion";
import type { Translator } from "@/i18n/translate";

import { Section } from "./Section";

/**
 * A sample WhatsApp conversation at night: a question, the assistant's
 * answer and the booking, plus what the owner gets out of it. The messages
 * arrive one by one when the card scrolls into view; the card tilts towards
 * the mouse and its results float above it.
 */
export function Demo({ t }: { t: Translator["t"] }) {
  const bubble = "max-w-[85%] rounded-2xl px-3.5 py-2.5";
  return (
    <Section id="example" title={t("landing.demo.title")} subtitle={t("landing.demo.subtitle")} glow="right" layout="split">
      <figure aria-label={t("landing.demo.label")} className="mx-auto w-full max-w-md">
        <TiltCard className="rounded-2xl border border-line bg-surface shadow-2xl">
          <div className="flex items-center gap-3 border-b border-line px-4 py-3">
            <span className="flex size-8 items-center justify-center rounded-full bg-accent-solid text-on-accent" aria-hidden>
              <IconSparkles className="size-4" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-ink">{t("landing.demo.business")}</p>
              <p className="flex items-center gap-1 text-xs text-ink-subtle">
                <IconWhatsApp className="size-3.5" aria-hidden />
                WhatsApp · {t("landing.demo.time")}
              </p>
            </div>
            <span className="size-2 rounded-full bg-success" aria-hidden />
          </div>
          <Stagger step={0.45} delay={0.15} amount={0.4} className="space-y-3 px-4 py-5 text-sm">
            <StaggerItem as="p" className={`${bubble} ml-auto rounded-br-md bg-surface-muted text-ink`}>
              {t("landing.demo.customer")}
            </StaggerItem>
            <StaggerItem as="p" className={`${bubble} rounded-bl-md bg-accent-soft text-ink`}>
              {t("landing.demo.assistant")}
            </StaggerItem>
            <StaggerItem as="p" className={`${bubble} ml-auto rounded-br-md bg-surface-muted text-ink`}>
              {t("landing.demo.customerReply")}
            </StaggerItem>
          </Stagger>
          <TiltLayer
            depth={28}
            className="mx-3 mb-3 space-y-2 rounded-xl border border-line bg-surface-muted/80 px-3.5 py-3 text-xs shadow-lg backdrop-blur"
          >
            <p className="flex items-center gap-2 text-success">
              <IconCalendar className="size-4 shrink-0" aria-hidden />
              <span className="min-w-0 flex-1">{t("landing.demo.booked")}</span>
              <IconCheck className="size-4 shrink-0" aria-hidden />
            </p>
            <p className="flex items-center gap-2 text-ink-muted">
              <IconHandoff className="size-4 shrink-0" aria-hidden />
              <span className="min-w-0 flex-1">{t("landing.demo.handoff")}</span>
            </p>
          </TiltLayer>
        </TiltCard>
      </figure>
    </Section>
  );
}
