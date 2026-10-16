"use client";

/**
 * Step 6, "Where do your customers write?": the website chat with the
 * business's own chat page (on by default), a Telegram bot in three
 * steps, and WhatsApp, Instagram and Messenger after launch (they need the
 * owner's Meta business account, which is no first-day task).
 */

import { displayUrl } from "@/app/b/[businessId]/assistant/channels/_lib/share";
import { Switch } from "@/components/content/Switch";
import { IconChat, IconWhatsApp } from "@/components/icons";
import { Badge, ErrorState, LoadingBlock } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { StepScreen } from "../StepScreen";
import type { StepContext } from "../flow/stepContext";
import { TelegramBotCard } from "./TelegramBotCard";
import { useChannelsStep } from "./useChannelsStep";

const CARD = "rounded-2xl border bg-surface/85 p-5 backdrop-blur-sm";

export function ChannelsScreen({ ctx }: { ctx: StepContext }) {
  const { t } = useI18n();
  const step = useChannelsStep(ctx);

  return (
    <StepScreen
      step="channels"
      title={t("tunnelTeam.channels.title")}
      text={t("tunnelTeam.channels.text")}
      actions={{
        onContinue: () => void step.finish(),
        onBack: ctx.back,
        onSkip: () => void ctx.skip("channels"),
        isBusy: step.isFinishing,
        canContinue: !step.isLoading,
      }}
    >
      {step.error ? (
        <ErrorState error={step.error} onRetry={step.reload} />
      ) : step.isLoading ? (
        <LoadingBlock label={t("common.loading")} />
      ) : (
        <div className="space-y-3">
          <section aria-labelledby="tunnel-web" className={cn(CARD, step.isWebOn ? "border-accent/50" : "border-line")}>
            <div className="flex items-start gap-3">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent" aria-hidden>
                <IconChat className="size-5" />
              </span>
              <div className="min-w-0 flex-1">
                <h2 id="tunnel-web" className="text-base font-semibold text-ink">
                  {t("tunnelTeam.channels.web.title")}
                </h2>
                <p className="mt-1 text-sm text-ink-muted">{t("tunnelTeam.channels.web.text")}</p>
              </div>
              <span className="flex items-center gap-2">
                <span className="text-xs font-medium text-ink-muted" aria-hidden>
                  {step.isWebOn ? t("tunnelTeam.channels.on") : t("tunnelTeam.channels.off")}
                </span>
                <Switch checked={step.isWebOn} onChange={step.setWebOn} label={t("tunnelTeam.channels.web.toggle")} />
              </span>
            </div>
            {step.hostedUrl && step.isWebOn ? (
              <p className="mt-4 truncate text-sm">
                <a href={step.hostedUrl} target="_blank" rel="noopener noreferrer" className="font-medium text-accent hover:underline">
                  {t("tunnelTeam.channels.web.ready", { link: displayUrl(step.hostedUrl) })}
                </a>
              </p>
            ) : null}
          </section>

          <TelegramBotCard
            channel={step.telegram.channel}
            token={step.telegram.token}
            onToken={step.telegram.setToken}
            error={step.telegram.error}
            isConnecting={step.telegram.isConnecting}
            onConnect={() => void step.telegram.connect()}
          />

          <section aria-labelledby="tunnel-later" className={cn(CARD, "border-dashed border-line-strong")}>
            <div className="flex items-start gap-3">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-surface-muted text-ink-muted" aria-hidden>
                <IconWhatsApp className="size-5" />
              </span>
              <div className="min-w-0 flex-1">
                <h2 id="tunnel-later" className="text-base font-semibold text-ink">
                  {t("tunnelTeam.channels.later.title")}
                </h2>
                <p className="mt-1 text-sm text-ink-muted">{t("tunnelTeam.channels.later.text")}</p>
              </div>
              <Badge tone="neutral">{t("tunnelTeam.channels.later.badge")}</Badge>
            </div>
          </section>
        </div>
      )}
    </StepScreen>
  );
}
