import type { Metadata, Viewport } from "next";
import { notFound } from "next/navigation";

import { hostedChatTexts } from "@/lib/hostedChat/texts";
import { SCHEME_BACKGROUNDS } from "@/lib/theme";
import { chatApiBase } from "@/server/hostedChat";

import { HostedChatNotice, HostedChatShell } from "./_components/HostedChatShell";
import { chatLanguage, readHostedChatRequest, visitorLanguage } from "./_lib/hostedChatRequest";
import { visitSourceOf } from "./_lib/visitSource";

/** The element the widget fills (its data-container). */
const CONTAINER_ID = "hosted-chat";

export async function generateMetadata(): Promise<Metadata> {
  const { lookup } = await readHostedChatRequest();
  return {
    ...(lookup.kind === "found" ? { title: { absolute: lookup.view.business_name } } : {}),
    robots: { index: false, follow: false },
  };
}

/** On phones the browser's bar takes the chat header's colour; the keyboard shrinks the page. */
export async function generateViewport(): Promise<Viewport> {
  const { lookup } = await readHostedChatRequest();
  const accent = lookup.kind === "found" ? lookup.view.accent_color : null;
  return {
    width: "device-width",
    initialScale: 1,
    viewportFit: "cover",
    interactiveWidget: "resizes-content",
    themeColor: accent
      ? accent
      : [
          { media: "(prefers-color-scheme: light)", color: SCHEME_BACKGROUNDS.light },
          { media: "(prefers-color-scheme: dark)", color: SCHEME_BACKGROUNDS.dark },
        ],
  };
}

/**
 * /c/{address}: a business's chat on a page of its own, for links and QR
 * codes (no website needed). The proxy has looked the address up, moved
 * older addresses here and allowed the API in the page's policy; the
 * widget (page mode) does the rest with its usual limits. The visitor key
 * stays in the browser's storage, never in the address; the link's
 * `?src=` goes to the widget as the visitor's source.
 */
export default async function HostedChatPage({ searchParams }: PageProps<"/c/[slug]">) {
  const { lookup, acceptLanguage, nonce } = await readHostedChatRequest();
  if (lookup.kind === "missing") {
    notFound();
  }
  if (lookup.kind === "failed") {
    const page = visitorLanguage(acceptLanguage);
    const texts = hostedChatTexts(page.language);
    return (
      <HostedChatShell page={page}>
        <HostedChatNotice lead={texts.unavailable} hint={texts.tryLater} />
      </HostedChatShell>
    );
  }

  const view = lookup.view;
  const page = chatLanguage(view, acceptLanguage);
  const texts = hostedChatTexts(page.language);
  if (!view.is_enabled) {
    return (
      <HostedChatShell page={page} accent={view.accent_color}>
        <HostedChatNotice title={view.business_name} lead={texts.unavailable} hint={texts.tryLater} />
      </HostedChatShell>
    );
  }

  const apiBase = chatApiBase(view);
  const source = visitSourceOf(await searchParams);
  return (
    <HostedChatShell page={page} accent={view.accent_color}>
      <div className="hc-frame">
        <div className="hc-placeholder">
          <span className="hc-spinner" aria-hidden />
          <p role="status">{texts.loading}</p>
          <noscript>
            <p>{texts.noScript}</p>
          </noscript>
        </div>
        {/* The widget adds its own element here: React leaves the inside alone. */}
        <div id={CONTAINER_ID} className="hc-widget" suppressHydrationWarning dangerouslySetInnerHTML={{ __html: "" }} />
      </div>
      <script
        async
        nonce={nonce}
        src={view.widget_script_url ?? `${apiBase}/widget.js`}
        data-tenant={view.business_id}
        data-mode="page"
        data-container={CONTAINER_ID}
        data-api-base={apiBase}
        data-source={source ?? undefined}
      />
    </HostedChatShell>
  );
}
