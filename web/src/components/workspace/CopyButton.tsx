"use client";

import { useEffect, useRef, useState } from "react";

import { IconCheck, IconCopy } from "@/components/icons";
import { Button, useToast, type ButtonSize, type ButtonVariant } from "@/components/ui";
import { useI18n } from "@/i18n/client";


const COPIED_FEEDBACK_MS = 2_000;

/** Copy text with the async clipboard API, else with a hidden textarea. */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fall back below (permissions, insecure origins).
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    area.remove();
  }
}

/**
 * A button that copies `value` and says "Copied" for a moment.
 * `iconOnly` buttons keep a visible tooltip-less label for screen readers.
 */
export function CopyButton({
  value,
  label,
  iconOnly = false,
  variant = "secondary",
  size = "sm",
  className,
}: {
  value: string;
  /** Visible text (default "Copy"); the accessible name when `iconOnly`. */
  label?: string;
  iconOnly?: boolean;
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (timer.current !== null) {
        window.clearTimeout(timer.current);
      }
    },
    [],
  );

  const onCopy = async () => {
    const ok = await copyText(value);
    if (!ok) {
      toast.info(t("workspace.copyFailed"));
      return;
    }
    setCopied(true);
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
    }
    timer.current = window.setTimeout(() => setCopied(false), COPIED_FEEDBACK_MS);
  };

  const text = copied ? t("workspace.copied") : (label ?? t("workspace.copy"));
  const icon = copied ? (
    <IconCheck className="size-4 text-success" aria-hidden />
  ) : (
    <IconCopy className="size-4" aria-hidden />
  );

  if (iconOnly) {
    return (
      <button
        type="button"
        onClick={onCopy}
        aria-label={text}
        title={text}
        className={
          "inline-flex size-8 shrink-0 items-center justify-center rounded-lg text-ink-muted transition-colors " +
          "hover:bg-surface-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus " +
          (className ?? "")
        }
      >
        {icon}
        <span className="sr-only" aria-live="polite">
          {copied ? t("workspace.copied") : ""}
        </span>
      </button>
    );
  }

  return (
    <Button variant={variant} size={size} onClick={onCopy} leadingIcon={icon} className={className} aria-live="polite">
      {text}
    </Button>
  );
}
