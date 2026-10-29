"use client";

import { useId, useState, type ReactNode } from "react";

/**
 * The hours and the address under one toggle on phones (the chat keeps the
 * screen); wide screens show them always and hide the toggle (CSS).
 */
export function InfoDisclosure({ label, children }: { label: string; children: ReactNode }) {
  const [isOpen, setOpen] = useState(false);
  const bodyId = useId();
  return (
    <div className="hc-info-more" data-open={isOpen ? "true" : "false"}>
      <button
        type="button"
        className="hc-info-toggle"
        aria-expanded={isOpen}
        aria-controls={bodyId}
        onClick={() => setOpen((open) => !open)}
      >
        <span>{label}</span>
        <svg viewBox="0 0 24 24" aria-hidden focusable="false">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      <div id={bodyId} className="hc-info-body">
        {children}
      </div>
    </div>
  );
}
