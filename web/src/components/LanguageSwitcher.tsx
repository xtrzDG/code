"use client";

import { useRouter } from "next/navigation";
import { useId, useTransition } from "react";

import { readApiError } from "@/api/errors";
import { LOCALES, LOCALE_NATIVE_NAMES, isLocale, type Locale } from "@/i18n/config";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { IconGlobe } from "./icons";
import { useToast } from "./ui/Toast";

/** POST /api/locale: cookie + the signed-in user's account language. */
export async function changeInterfaceLanguage(locale: Locale): Promise<void> {
  const response = await fetch("/api/locale", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ locale }),
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
}

/** Interface language picker (ქართული / Русский / English). */
export function LanguageSwitcher({ className, compact = false }: { className?: string; compact?: boolean }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const toast = useToast();
  const [isPending, startTransition] = useTransition();
  const id = useId();

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <label htmlFor={id} className={cn(compact ? "sr-only" : "text-sm text-ink-muted")}>
        {t("language.label")}
      </label>
      <div className="relative">
        <IconGlobe className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden />
        <select
          id={id}
          value={locale}
          disabled={isPending}
          onChange={(event) => {
            const next = event.target.value;
            if (!isLocale(next)) {
              return;
            }
            startTransition(async () => {
              try {
                await changeInterfaceLanguage(next);
                router.refresh();
              } catch (error) {
                toast.error(error);
              }
            });
          }}
          className="h-9 appearance-none rounded-lg border border-line bg-surface py-0 pr-3 pl-8 text-sm text-ink hover:border-line-strong focus:border-focus focus:ring-2 focus:ring-focus/30 focus:outline-none disabled:opacity-60"
        >
          {LOCALES.map((option) => (
            <option key={option} value={option} lang={option}>
              {LOCALE_NATIVE_NAMES[option]}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
