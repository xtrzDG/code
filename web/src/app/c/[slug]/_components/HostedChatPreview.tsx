import type { CSSProperties } from "react";

import type { PreviewLook } from "@/lib/hostedChat/preview";
import type { HostedChatView } from "@/server/hostedChat";

import type { PageLanguage } from "../_lib/hostedChatRequest";

import "@/styles/hostedChatPreview.css";

/**
 * The cabinet's live preview (/c/{address}?preview=1): the chat open in its
 * corner over a sketch of a website, as a visitor of the owner's site sees
 * it. The widget runs in its live-preview mode: it shows the chat even
 * while it is switched off, sends nothing, keeps nothing, and follows the
 * colour, corner and language the Channels page sends it.
 */
export function HostedChatPreview({
  view,
  page,
  look,
  apiBase,
  nonce,
}: {
  view: HostedChatView;
  page: PageLanguage;
  look: PreviewLook;
  apiBase: string;
  nonce: string | undefined;
}) {
  const accent = look.color ?? view.accent_color;
  const style = accent ? ({ "--hc-accent": accent } as CSSProperties) : undefined;
  return (
    <main className="hc-preview" lang={page.language} dir={page.direction} style={style}>
      {/* A website shape only: the chat is what the owner looks at. */}
      <div className="hc-preview-site" aria-hidden>
        <div className="hc-preview-bar">
          <span className="hc-preview-logo" />
          <span className="hc-preview-name" dir="auto" data-user-content>
            {view.business_name}
          </span>
          <span className="hc-preview-nav">
            <i />
            <i />
            <i />
          </span>
        </div>
        <div className="hc-preview-hero">
          <i className="hc-preview-line hc-preview-title" />
          <i className="hc-preview-line" />
          <i className="hc-preview-line hc-preview-short" />
          <i className="hc-preview-button" />
        </div>
        <div className="hc-preview-cards">
          <i />
          <i />
          <i />
        </div>
      </div>
      <script
        async
        nonce={nonce}
        src={view.widget_script_url ?? `${apiBase}/widget.js`}
        data-tenant={view.business_id}
        data-api-base={apiBase}
        data-preview="live"
        data-open="true"
        data-language={page.language}
        data-color={look.color ?? undefined}
        data-position={look.position ?? undefined}
      />
    </main>
  );
}
