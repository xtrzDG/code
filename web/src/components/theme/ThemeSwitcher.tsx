"use client";

import { useId, type ComponentType } from "react";

import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { cn } from "@/lib/cn";
import { THEMES, type Theme } from "@/lib/theme";

import { IconMonitor, IconMoon, IconSun, type IconProps } from "../icons";
import { useTheme } from "./ThemeProvider";

const OPTIONS: Record<Theme, { label: MessageKey; icon: ComponentType<IconProps> }> = {
  dark: { label: "theme.dark", icon: IconMoon },
  light: { label: "theme.light", icon: IconSun },
  system: { label: "theme.system", icon: IconMonitor },
};

/**
 * Dark / light / system as a radio group of three icon buttons: Tab reaches
 * the group, the arrow keys move between the themes, each has its name for
 * screen readers and as a tooltip.
 */
export function ThemeSwitcher({ className }: { className?: string }) {
  const { t } = useI18n();
  const { theme, setTheme } = useTheme();
  const name = useId();

  return (
    <fieldset
      className={cn("inline-flex shrink-0 items-center gap-0.5 rounded-lg border border-line bg-surface p-0.5", className)}
    >
      <legend className="sr-only">{t("theme.label")}</legend>
      {THEMES.map((option) => {
        const { label, icon: Icon } = OPTIONS[option];
        const isChecked = theme === option;
        return (
          <label
            key={option}
            title={t(label)}
            className={cn(
              "flex size-7 cursor-pointer items-center justify-center rounded-md transition-colors",
              "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-1 has-[:focus-visible]:outline-focus",
              isChecked ? "bg-surface-muted text-ink ring-1 ring-line ring-inset" : "text-ink-subtle hover:text-ink",
            )}
          >
            <input
              type="radio"
              name={name}
              value={option}
              checked={isChecked}
              onChange={() => setTheme(option)}
              className="sr-only"
            />
            <Icon className="size-4" aria-hidden />
            <span className="sr-only">{t(label)}</span>
          </label>
        );
      })}
    </fieldset>
  );
}
