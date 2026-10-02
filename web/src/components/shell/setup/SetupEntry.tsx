"use client";

/**
 * Before the assistant exists the sidebar holds only this: one big
 * "Create an AI assistant" entry with a light running around its edge,
 * leading into the setup flow. Staff (who cannot fill the profile) see a
 * quiet note instead. Collapsed, it is a glowing square with the sparkles.
 */

import Link from "next/link";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconSparkles } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { setupPath } from "@/lib/navigation";

export function SetupEntry({ isActive, collapsed = false, canSetUp }: { isActive: boolean; collapsed?: boolean; canSetUp: boolean }) {
  const { t } = useI18n();
  const { business } = useBusiness();

  if (!canSetUp) {
    return collapsed ? null : (
      <p className="rounded-2xl border border-dashed border-line px-3 py-3 text-sm text-ink-muted">{t("setup.staffTitle")}</p>
    );
  }

  return (
    <nav aria-label={t("nav.mainNavigation")}>
      <Link
        href={setupPath(business.id)}
        aria-current={isActive ? "page" : undefined}
        title={collapsed ? t("setup.navEntry") : undefined}
        className={cn(
          "setup-glow motion-lift group flex rounded-2xl text-ink shadow-[0_18px_40px_-24px_var(--accent-solid)]",
          collapsed ? "size-12 items-center justify-center" : "flex-col gap-3 p-4",
        )}
      >
        <span
          aria-hidden
          className="flex size-9 items-center justify-center rounded-xl bg-accent-solid text-on-accent shadow-[0_8px_20px_-8px_var(--accent-solid)] transition-transform duration-(--motion-base) group-hover:scale-110 group-hover:rotate-6"
        >
          <IconSparkles className="size-5" />
        </span>
        <span className={cn(collapsed && "sr-only")}>
          <span className="block text-[0.9375rem] leading-snug font-semibold">{t("setup.navEntry")}</span>
          <span className="mt-1 block text-xs text-ink-muted">{t("setup.navEntryHint")}</span>
        </span>
      </Link>
    </nav>
  );
}
