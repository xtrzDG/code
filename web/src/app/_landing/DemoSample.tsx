import { IconCalendar, IconCheck, IconHandoff, IconWhatsApp } from "@/components/icons";
import { Stagger, StaggerItem } from "@/components/motion";
import type { Translator } from "@/i18n/translate";

/**
 * An example WhatsApp conversation at night, shown in the hero when no
 * live demo can answer (none is configured, or the API is away). It is
 * labelled an example: nothing on it pretends to be live.
 */
export function DemoSample({ t }: { t: Translator["t"] }) {
  const bubble = "max-w-[85%] rounded-2xl px-3.5 py-2.5";
  return (
    <figure aria-label={t("landing.demo.label")} className="w-full">
      <div className="flex items-center gap-3 border-b border-line px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-ink">{t("landing.demo.business")}</p>
          <p className="flex items-center gap-1 text-xs text-ink-subtle">
            <IconWhatsApp className="size-3.5" aria-hidden />
            WhatsApp · {t("landing.demo.time")}
          </p>
        </div>
        <span className="rounded-full border border-line px-2 py-0.5 text-xs text-ink-muted">{t("publicDemo.sampleBadge")}</span>
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
      <div className="mx-3 mb-3 space-y-2 rounded-xl border border-line bg-surface-muted/80 px-3.5 py-3 text-xs">
        <p className="flex items-center gap-2 text-ink">
          <IconCalendar className="size-4 shrink-0 text-accent" aria-hidden />
          <span className="min-w-0 flex-1">{t("landing.demo.booked")}</span>
          <IconCheck className="size-4 shrink-0 text-accent" aria-hidden />
        </p>
        <p className="flex items-center gap-2 text-ink-muted">
          <IconHandoff className="size-4 shrink-0" aria-hidden />
          <span className="min-w-0 flex-1">{t("landing.demo.handoff")}</span>
        </p>
      </div>
    </figure>
  );
}
