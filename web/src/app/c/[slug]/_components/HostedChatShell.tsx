import type { CSSProperties, ReactNode } from "react";

import type { PageLanguage } from "../_lib/hostedChatRequest";

import "@/styles/hostedChat.css";

const ACCENT_PATTERN = /^#[0-9a-fA-F]{6}$/;

/**
 * The page around the hosted chat and its notices: the visitor's language
 * and direction, the business's accent colour, the system's colours.
 */
export function HostedChatShell({
  page,
  accent,
  children,
}: {
  page: PageLanguage;
  accent?: string | null;
  children: ReactNode;
}) {
  const style = accent && ACCENT_PATTERN.test(accent) ? ({ "--hc-accent": accent } as CSSProperties) : undefined;
  return (
    <main className="hc-page" lang={page.language} dir={page.direction} style={style}>
      {children}
    </main>
  );
}

/** A message in place of the chat: the chat is off, not found or could not be loaded. */
export function HostedChatNotice({ title, lead, hint }: { title?: string; lead: string; hint?: string }) {
  return (
    <div className="hc-frame">
      <div className="hc-notice">
        <span className="hc-mark" aria-hidden>
          <svg viewBox="0 0 24 24" focusable="false">
            <path d="M5 18l-1.5 3 4-1.5A8.5 8.5 0 1012 3.5 8.5 8.5 0 003.5 12c0 2.2.6 4.2 1.5 6z" />
          </svg>
        </span>
        {title ? <h1 dir="auto">{title}</h1> : null}
        {title ? <p className="hc-notice-lead">{lead}</p> : <h1>{lead}</h1>}
        {hint ? <p>{hint}</p> : null}
      </div>
    </div>
  );
}
