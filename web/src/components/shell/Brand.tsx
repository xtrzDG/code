"use client";

import Link from "next/link";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { IconSparkles } from "../icons";

/** The product mark and name, linking home (businesses when signed in, the landing page otherwise). */
export function Brand({
  href,
  hideNameOnPhones = false,
  hideName = false,
  className,
}: {
  href: string;
  /** Only the mark below `sm`, to leave room for the switches in a phone's top bar. */
  hideNameOnPhones?: boolean;
  /** Only the mark (the collapsed sidebar); the name stays for screen readers. */
  hideName?: boolean;
  className?: string;
}) {
  const { t } = useI18n();
  return (
    <Link href={href} className={cn("flex min-w-0 items-center gap-2.5 rounded-md", className)} title={hideName ? t("common.appName") : undefined}>
      <span
        className="flex size-7 shrink-0 items-center justify-center rounded-md bg-accent-solid text-on-accent shadow-[0_6px_18px_-6px_var(--accent-solid)]"
        aria-hidden
      >
        <IconSparkles className="size-4" />
      </span>
      <span
        className={cn(
          "text-sm leading-tight font-semibold tracking-tight [overflow-wrap:anywhere] text-ink",
          hideNameOnPhones && "sr-only sm:not-sr-only",
          hideName && "sr-only",
        )}
      >
        {t("common.appName")}
      </span>
    </Link>
  );
}
