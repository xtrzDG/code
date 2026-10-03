"use client";

/**
 * One screen of the tunnel: "Step 3 of 8", the question in big type, a
 * line of help, the answer fields and the way on (Back, "Skip for now",
 * Continue). Enter continues from any field except a multi-line one, a
 * button, a link or a field that keeps Enter for itself (the test chat's
 * box, marked `data-enter="own"`); the question takes the focus when the
 * screen arrives, so keyboard and screen-reader users start at the top.
 */

import { useEffect, useRef, type KeyboardEvent, type ReactNode } from "react";

import { IconArrowLeft, IconArrowRight } from "@/components/icons";
import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { stepNumber, TUNNEL_STEPS, type TunnelStep } from "@/lib/tunnel/steps";

export interface StepActions {
  onContinue?: () => void;
  onBack?: () => void;
  onSkip?: () => void;
  continueLabel?: string;
  /** Saving or creating: the buttons wait and say so. */
  isBusy?: boolean;
  busyLabel?: string;
  /** Continue is not possible yet (shown, but disabled). */
  canContinue?: boolean;
}

const OWN_ENTER = new Set(["TEXTAREA", "BUTTON", "A", "SELECT", "SUMMARY"]);

/** Whether Enter pressed on this element means "continue". */
export function isContinueKey(event: Pick<KeyboardEvent, "key" | "shiftKey" | "altKey" | "ctrlKey" | "metaKey" | "nativeEvent">, target: HTMLElement): boolean {
  if (event.key !== "Enter" || event.shiftKey || event.altKey || event.ctrlKey || event.metaKey) {
    return false;
  }
  if ((event.nativeEvent as globalThis.KeyboardEvent).isComposing) {
    return false;
  }
  if (OWN_ENTER.has(target.tagName) || target.closest("[data-enter='own']")) {
    return false;
  }
  const type = target.getAttribute("type");
  return type !== "checkbox" && type !== "radio";
}

export function StepScreen({
  step,
  title,
  text,
  children,
  actions,
  aside,
  wide = false,
}: {
  step: TunnelStep;
  title: string;
  text?: ReactNode;
  children?: ReactNode;
  actions: StepActions;
  /** Below the buttons (the language picker on phones, a note). */
  aside?: ReactNode;
  /** A wider column (the offer table, the test chat). */
  wide?: boolean;
}) {
  const { t } = useI18n();
  const heading = useRef<HTMLHeadingElement>(null);
  const { onContinue, onBack, onSkip, isBusy = false, canContinue = true } = actions;

  useEffect(() => {
    heading.current?.focus({ preventScroll: true });
  }, [step]);

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!onContinue || isBusy || !canContinue || !(event.target instanceof HTMLElement)) {
      return;
    }
    if (isContinueKey(event, event.target)) {
      event.preventDefault();
      onContinue();
    }
  };

  return (
    <div onKeyDown={onKeyDown} className={cn("mx-auto w-full", wide ? "max-w-3xl" : "max-w-2xl")}>
      <p className="text-sm font-medium tracking-wide text-accent">
        {t("tunnel.stepOf", { number: stepNumber(step), total: TUNNEL_STEPS.length })}
      </p>
      <h1
        ref={heading}
        tabIndex={-1}
        className="mt-3 text-3xl leading-tight font-semibold tracking-tight text-balance text-ink outline-none sm:text-4xl lg:text-[2.75rem]"
      >
        {title}
      </h1>
      {text ? <p className="mt-4 max-w-xl text-base text-pretty text-ink-muted sm:text-lg">{text}</p> : null}

      {children ? <div className="mt-8 sm:mt-10">{children}</div> : null}

      <div className="sticky bottom-0 z-10 -mx-4 mt-10 flex items-center gap-3 border-t border-line/60 bg-canvas/85 px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur-md sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:p-0 sm:backdrop-blur-none">
        {onBack ? (
          <Button variant="ghost" size="lg" onClick={onBack} disabled={isBusy} leadingIcon={<IconArrowLeft className="size-4 rtl:-scale-x-100" aria-hidden />}>
            <span className="max-sm:sr-only">{t("tunnel.back")}</span>
          </Button>
        ) : null}
        <div className="ms-auto flex items-center gap-2 sm:gap-3">
          {onSkip ? (
            <Button variant="ghost" size="lg" onClick={onSkip} disabled={isBusy}>
              {t("tunnel.skip")}
            </Button>
          ) : null}
          {onContinue ? (
            <Button
              size="lg"
              onClick={onContinue}
              disabled={!canContinue}
              isLoading={isBusy}
              loadingText={actions.busyLabel ?? t("tunnel.saving")}
              trailingIcon={<IconArrowRight className="size-4 rtl:-scale-x-100" aria-hidden />}
              className="min-w-36 shadow-[0_16px_36px_-18px_var(--accent-solid)]"
            >
              {actions.continueLabel ?? t("tunnel.continue")}
            </Button>
          ) : null}
        </div>
      </div>
      {onContinue ? (
        <p className="mt-2 hidden text-end text-xs text-ink-subtle sm:block" aria-hidden>
          {t("tunnel.enterHint")} <kbd className="rounded border border-line bg-surface px-1.5 py-0.5 font-sans text-[0.6875rem]">↵</kbd>
        </p>
      ) : null}
      {aside ? <div className="mt-6">{aside}</div> : null}
    </div>
  );
}
