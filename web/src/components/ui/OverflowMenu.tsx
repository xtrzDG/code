"use client";

/**
 * "More": the less frequent actions of a place behind one button, so the
 * main action stands alone (a booking's details: Confirm, and under More
 * the rest). A WAI-ARIA menu: the first item takes the focus, arrow keys,
 * Home and End move, Escape or a click outside closes and gives the focus
 * back to the button. It opens upwards by default (a dialog's footer).
 * `iconOnly` shows just the "⋯" (the label names the button for screen
 * readers and as its tooltip): a row's actions on a phone.
 */

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { IconMore } from "@/components/icons";
import { cn } from "@/lib/cn";

import { buttonClasses } from "./Button";

export interface MenuAction {
  key: string;
  label: string;
  onSelect: () => void;
  /** A destructive action (cancel a booking): red, after a divider. */
  tone?: "danger";
}

export function OverflowMenu({
  label,
  actions,
  placement = "top",
  iconOnly = false,
  className,
}: {
  /** The button's text ("More"), also the menu's name. */
  label: string;
  actions: readonly MenuAction[];
  placement?: "top" | "bottom";
  iconOnly?: boolean;
  className?: string;
}) {
  const id = useId();
  const [isOpen, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const onPointer = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointer);
    menu.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
    return () => document.removeEventListener("pointerdown", onPointer);
  }, [isOpen]);

  const close = () => {
    setOpen(false);
    trigger.current?.focus();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const items = [...(menu.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])];
    const index = items.indexOf(document.activeElement as HTMLElement);
    const target =
      event.key === "ArrowDown"
        ? (index + 1) % items.length
        : event.key === "ArrowUp"
          ? (index - 1 + items.length) % items.length
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? items.length - 1
              : null;
    if (event.key === "Escape" || event.key === "Tab") {
      event.preventDefault();
      // Escape inside a dialog closes only the menu, never the dialog.
      event.stopPropagation();
      close();
    } else if (target !== null) {
      event.preventDefault();
      items[target]?.focus();
    }
  };

  if (actions.length === 0) {
    return null;
  }
  return (
    <div ref={root} className={cn("relative", className)}>
      <button
        ref={trigger}
        type="button"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-controls={isOpen ? `${id}-menu` : undefined}
        onClick={() => setOpen((open) => !open)}
        aria-label={iconOnly ? label : undefined}
        title={iconOnly ? label : undefined}
        className={buttonClasses({
          variant: iconOnly ? "ghost" : "secondary",
          size: "sm",
          className: iconOnly ? "w-9 px-0" : "whitespace-nowrap",
        })}
      >
        <IconMore className="size-4" aria-hidden />
        {iconOnly ? null : label}
      </button>
      {isOpen ? (
        <div
          ref={menu}
          id={`${id}-menu`}
          role="menu"
          aria-label={label}
          onKeyDown={onKeyDown}
          className={cn(
            "animate-settle absolute end-0 z-30 min-w-48 overflow-hidden rounded-xl border border-line bg-surface py-1 shadow-2xl",
            placement === "top" ? "bottom-full mb-2" : "top-full mt-2",
          )}
        >
          {actions.map((action, index) => (
            <button
              key={action.key}
              type="button"
              role="menuitem"
              tabIndex={-1}
              onClick={() => {
                setOpen(false);
                action.onSelect();
              }}
              className={cn(
                "flex w-full cursor-pointer items-center px-4 py-2 text-start text-sm whitespace-nowrap outline-none hover:bg-surface-muted focus-visible:bg-surface-muted",
                action.tone === "danger" ? cn("text-danger", index > 0 && "mt-1 border-t border-line pt-2.5") : "text-ink",
              )}
            >
              {action.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
