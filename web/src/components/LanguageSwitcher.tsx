"use client";

import { useRouter } from "next/navigation";
import { useId, useTransition } from "react";

import { readApiError } from "@/api/errors";
import { LOCALES, LOCALE_NATIVE_NAMES, isLocale, type Locale } from "@/i18n/config";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { switchPathLocale } from "@/lib/publicSite/paths";

import { IconChevronDown, IconGlobe } from "./icons";
import { useToast } from "./ui/Toast";

/** POST /api/locale: cookie + the signed-in user's account language. */
async function changeInterfaceLanguage(locale: Locale): Promise<void> {
  const response = await fetch("/api/locale", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ locale }),
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
}

/**
 * Interface language picker: a globe, the current language by its own name
 * (ქართული / Русский / English) and a native select, so it works with the
 * keyboard, screen readers and phone pickers. The page stays where it is and
 * re-renders in the new language; a public page that has its language in
 * its address (/ru/for/hotel) opens in the new one (/ka/for/hotel).
 */
export function LanguageSwitcher({ className, compact = false }: { className?: string; compact?: boolean }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const toast = useToast();
  const [isPending, startTransition] = useTransition();
  const id = useId();

  return (
    <div className={cn("flex min-w-0 items-center gap-2", className)}>
      <label htmlFor={id} className={cn(compact ? "sr-only" : "text-sm text-ink-muted")}>
        {t("language.label")}
      </label>
      <div className="relative min-w-0">
        {/* Below 360 px the globe makes room for the language's name. */}
        <IconGlobe
          className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-ink-muted max-[359px]:hidden"
          aria-hidden
        />
        <select
          id={id}
          value={locale}
          disabled={isPending}
          title={t("language.label")}
          onChange={(event) => {
            const next = event.target.value;
            if (!isLocale(next)) {
              return;
            }
            startTransition(async () => {
              try {
                await changeInterfaceLanguage(next);
                const { pathname, search, hash } = window.location;
                const localized = switchPathLocale(pathname, next);
                if (localized === pathname) {
                  router.refresh();
                } else {
                  // A full load: the root layout (the page's lang, the
                  // dictionary) belongs to the language too.
                  window.location.assign(new URL(`${localized}${search}${hash}`, window.location.origin));
                }
              } catch (error) {
                toast.error(error);
              }
            });
          }}
          className={cn(
            "h-8 w-full cursor-pointer appearance-none truncate rounded-lg border border-line bg-surface py-0 pr-7 pl-8 text-sm font-medium text-ink max-[359px]:pl-2.5",
            "transition-colors hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus disabled:opacity-60",
          )}
        >
          {LOCALES.map((option) => (
            <option key={option} value={option} lang={option}>
              {LOCALE_NATIVE_NAMES[option]}
            </option>
          ))}
        </select>
        <IconChevronDown
          className="pointer-events-none absolute top-1/2 right-2 size-3.5 -translate-y-1/2 text-ink-subtle"
          aria-hidden
        />
      </div>
    </div>
  );
}
