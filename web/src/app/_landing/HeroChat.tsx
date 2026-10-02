import { IconCalendar, IconCheck, IconHandoff, IconSparkles } from "@/components/icons";
import type { Translator } from "@/i18n/translate";

/** A sample WhatsApp conversation: a question at night, a booking and a handoff. */
export function HeroChat({ t }: { t: Translator["t"] }) {
  return (
    <figure className="relative mx-auto w-full max-w-md" aria-label={t("landing.demo.label")}>
      <div className="overflow-hidden rounded-2xl border border-line bg-surface">
        <div className="flex items-center gap-3 border-b border-line px-4 py-3">
          <span className="flex size-8 items-center justify-center rounded-full bg-accent-solid text-on-accent" aria-hidden>
            <IconSparkles className="size-4" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-ink">{t("landing.demo.business")}</p>
            <p className="text-xs text-ink-subtle">WhatsApp · {t("landing.demo.time")}</p>
          </div>
          <span className="size-2 rounded-full bg-success" aria-hidden />
        </div>
        <div className="space-y-3 px-4 py-5 text-sm">
          <p className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-surface-muted px-3.5 py-2.5 text-ink">
            {t("landing.demo.customer")}
          </p>
          <p className="max-w-[85%] rounded-2xl rounded-bl-md bg-accent-soft px-3.5 py-2.5 text-ink">
            {t("landing.demo.assistant")}
          </p>
          <p className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-surface-muted px-3.5 py-2.5 text-ink">
            {t("landing.demo.customerReply")}
          </p>
        </div>
        <div className="space-y-2 border-t border-line px-4 py-3 text-xs">
          <p className="flex items-center gap-2 text-success">
            <IconCalendar className="size-4 shrink-0" aria-hidden />
            <span className="min-w-0 flex-1">{t("landing.demo.booked")}</span>
            <IconCheck className="size-4 shrink-0" aria-hidden />
          </p>
          <p className="flex items-center gap-2 text-ink-muted">
            <IconHandoff className="size-4 shrink-0" aria-hidden />
            <span className="min-w-0 flex-1">{t("landing.demo.handoff")}</span>
          </p>
        </div>
      </div>
    </figure>
  );
}
