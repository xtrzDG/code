"use client";

/**
 * The toasts themselves, animated: a toast rises from the corner tipping
 * forward (3D), the others make room with a spring, a dismissed one shrinks
 * away. Its own chunk with the motion library under it, fetched when the
 * first toast of a visit appears (./toastList.ts): most visits to the public
 * site never show one.
 */

import { AnimatePresence, LazyMotion, MotionConfig } from "motion/react";
import * as m from "motion/react-m";
import { useEffect, useRef, useState, type ReactNode, type Ref } from "react";

import domMax from "@/components/motion/motionFeatures";
import { cn } from "@/lib/cn";
import { springTransition, tweenTransition } from "@/lib/motion";

import { IconAlert, IconCheck, IconInfo, IconX } from "../icons";
import type { ToastItem, ToastTone } from "./ToastViewport";
import { UserSentence } from "./UserContent";

const TOAST_MOTION = {
  initial: { opacity: 0, y: 16, rotateX: -24, scale: 0.96, transformPerspective: 640 },
  animate: { opacity: 1, y: 0, rotateX: 0, scale: 1, transition: springTransition("snappy") },
  exit: { opacity: 0, scale: 0.94, transition: tweenTransition("fast", "exit") },
  transition: { layout: springTransition("layout") },
} as const;

const TONE_STYLES: Record<ToastTone, { icon: typeof IconCheck; className: string }> = {
  success: { icon: IconCheck, className: "text-success" },
  error: { icon: IconAlert, className: "text-danger" },
  info: { icon: IconInfo, className: "text-info" },
};

/** Closes the toast after its time; the time stands still while `isPaused`. */
function useDismissTimer(durationMs: number, isPaused: boolean, onExpire: () => void): void {
  const remaining = useRef(durationMs);
  const onExpireRef = useRef(onExpire);
  useEffect(() => {
    onExpireRef.current = onExpire;
  });

  useEffect(() => {
    if (isPaused) {
      return;
    }
    const startedAt = Date.now();
    const timer = window.setTimeout(() => onExpireRef.current(), remaining.current);
    return () => {
      window.clearTimeout(timer);
      remaining.current = Math.max(0, remaining.current - (Date.now() - startedAt));
    };
  }, [isPaused]);
}

function ToastCard({
  item,
  onDismiss,
  closeLabel,
  ref,
}: {
  item: ToastItem;
  onDismiss: (id: number) => void;
  closeLabel: string;
  /** Set by AnimatePresence ("popLayout" measures a leaving toast). */
  ref?: Ref<HTMLDivElement>;
}) {
  const [isHovered, setHovered] = useState(false);
  const [isFocused, setFocused] = useState(false);
  // Only a toast with an action (Undo) waits while it is pointed at or
  // focused: someone is reaching for the button. A plain message keeps its
  // time, so it never sits on top of what the person clicks next.
  const isPaused = item.action !== undefined && (isHovered || isFocused);
  useDismissTimer(item.durationMs, isPaused, () => onDismiss(item.id));
  const { icon: Icon, className } = TONE_STYLES[item.tone];

  return (
    <m.div
      ref={ref}
      layout="position"
      {...TOAST_MOTION}
      role={item.tone === "error" ? "alert" : "status"}
      onPointerEnter={() => setHovered(true)}
      onPointerLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setFocused(false);
        }
      }}
      className="pointer-events-auto relative flex w-full max-w-sm origin-bottom items-start gap-3 overflow-hidden rounded-xl border border-line bg-surface p-3.5 shadow-lg"
    >
      <Icon className={cn("mt-0.5 size-5 shrink-0", className)} aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-ink">{typeof item.title === "string" ? item.title : <UserSentence {...item.title} />}</p>
        {item.description ? <p className="mt-1 text-sm break-words text-ink-muted">{item.description}</p> : null}
      </div>
      {item.action ? (
        <button
          type="button"
          onClick={() => {
            onDismiss(item.id);
            item.action?.onAction();
          }}
          className="-my-1 shrink-0 rounded-md px-2 py-1 text-sm font-semibold text-accent transition-colors hover:bg-accent-soft focus-visible:outline-2 focus-visible:outline-focus"
        >
          {item.action.label}
        </button>
      ) : null}
      <button
        type="button"
        onClick={() => onDismiss(item.id)}
        className="-m-1 rounded-md p-1 text-ink-subtle hover:bg-surface-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-focus"
        aria-label={closeLabel}
      >
        <IconX className="size-4" aria-hidden />
      </button>
      {item.action ? (
        // The undo window running down; it stops while the toast is paused.
        <span
          aria-hidden
          className="absolute inset-x-0 bottom-0 h-0.5 origin-left animate-countdown rtl:origin-right bg-accent-solid/70 motion-reduce:hidden"
          style={{ animationDuration: `${item.durationMs}ms`, animationPlayState: isPaused ? "paused" : "running" }}
        />
      ) : null}
    </m.div>
  );
}

export interface ToastListProps {
  items: ToastItem[];
  onDismiss: (id: number) => void;
  closeLabel: string;
}

/** Whether a list has been on screen before (see ToastList). */
let hasMounted = false;

function ToastList({ items, onDismiss, closeLabel }: ToastListProps) {
  // The first toasts of a visit rise in; when the list moves into a dialog
  // and back (a remount), the toasts on screen stay where they are.
  const [risesIn] = useState(() => !hasMounted);
  useEffect(() => {
    hasMounted = true;
  }, []);
  return (
    // Its own animation features and reduced-motion rule: the public site loads no other motion (MotionProvider).
    <LazyMotion features={domMax}>
      <MotionConfig reducedMotion="user">
        <AnimatePresence initial={risesIn} mode="popLayout">
          {items.map((item) => (
            <ToastCard key={item.id} item={item} onDismiss={onDismiss} closeLabel={closeLabel} />
          ))}
        </AnimatePresence>
      </MotionConfig>
    </LazyMotion>
  );
}

/** The list as an element: what the viewport renders once this module has arrived (./toastList.ts). */
export function renderToastList(props: ToastListProps): ReactNode {
  return <ToastList {...props} />;
}
