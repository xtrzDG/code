"use client";

/**
 * The edge between the conversation list and the open conversation (large
 * screens): drag it, or focus it and use the arrow keys, Home and End, to
 * make the list 320–520 px wide; a double click goes back to the usual
 * width. The width shows while dragging and is remembered when let go.
 */

import { useRef, type KeyboardEvent, type PointerEvent } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { clampListWidth, MAX_LIST_WIDTH, MIN_LIST_WIDTH, widthAfterKey } from "../../_lib/inboxLayout";

export function ListResizer({
  width,
  measure,
  onPreview,
  onCommit,
  onReset,
}: {
  /** The width shown now (null: the responsive default). */
  width: number | null;
  /** The list column's width on screen now. */
  measure: () => number;
  /** While dragging: the width to show. */
  onPreview: (width: number) => void;
  /** The width to remember. */
  onCommit: (width: number) => void;
  onReset: () => void;
}) {
  const { t } = useI18n();
  const drag = useRef<{ startX: number; startWidth: number; sign: number; last: number } | null>(null);
  const current = width ?? clampListWidth(measure());

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) {
      return;
    }
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    const isRtl = getComputedStyle(event.currentTarget).direction === "rtl";
    const startWidth = clampListWidth(measure());
    drag.current = { startX: event.clientX, startWidth, sign: isRtl ? -1 : 1, last: startWidth };
  };

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const state = drag.current;
    if (!state) {
      return;
    }
    const next = clampListWidth(state.startWidth + state.sign * (event.clientX - state.startX));
    if (next !== state.last) {
      state.last = next;
      onPreview(next);
    }
  };

  const onPointerUp = () => {
    const state = drag.current;
    drag.current = null;
    if (state && state.last !== state.startWidth) {
      onCommit(state.last);
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const next = widthAfterKey(event.key, current);
    if (next !== null) {
      event.preventDefault();
      onCommit(next);
    }
  };

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={t("inboxTriage.resize.label")}
      aria-valuemin={MIN_LIST_WIDTH}
      aria-valuemax={MAX_LIST_WIDTH}
      aria-valuenow={current}
      title={t("inboxTriage.resize.hint")}
      tabIndex={0}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onKeyDown={onKeyDown}
      onDoubleClick={onReset}
      data-list-resizer=""
      className={cn(
        "group/resize absolute inset-y-0 -end-3.5 z-10 hidden w-3 cursor-col-resize touch-none items-center justify-center lg:flex",
        "focus-visible:outline-none",
      )}
    >
      <span
        aria-hidden
        className="h-12 w-1 rounded-full bg-line transition-colors group-hover/resize:bg-line-strong group-focus-visible/resize:bg-accent-solid group-active/resize:bg-accent-solid"
      />
    </div>
  );
}
