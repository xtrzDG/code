"use client";

import { useEffect, useRef, useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { languageName } from "@/lib/format";
import { buildChatPreviewPath, isPreviewReady, previewLookMessage, type PreviewLook } from "@/lib/hostedChat/preview";

import { initialPreviewLanguage, type WidgetLook } from "../_lib/widgetLook";

/**
 * The live preview of the website chat: the hosted chat page of this very
 * origin in its preview mode (/c/{business}?preview=1), framed here. It
 * starts with the chosen look in its address; every later change of colour,
 * corner or language reaches it at once by postMessage, without a reload.
 * It speaks the owner's language when the assistant does; chips switch it
 * to any of the assistant's languages (each with its own greeting).
 */
export function WidgetPreviewFrame({ look }: { look: WidgetLook }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const frame = useRef<HTMLIFrameElement>(null);
  const [language, setLanguage] = useState(() =>
    initialPreviewLanguage(locale, business.languages, business.default_language),
  );
  // Loaded: the page is there (shown); ready: the chat in it listens for changes.
  const [isLoaded, setIsLoaded] = useState(false);
  const [isReady, setIsReady] = useState(false);
  // The address is fixed at the first render: changes go by message, not by reloading the frame.
  const [src] = useState(() => buildChatPreviewPath(business.id, { color: look.color, position: look.position, language }));
  const latest = useRef<PreviewLook>({ color: look.color, position: look.position, language });

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      const target = frame.current?.contentWindow ?? null;
      if (isPreviewReady(event, target, window.location.origin)) {
        setIsReady(true);
        setIsLoaded(true);
        // A reloaded frame says it is ready again and gets the current look.
        target?.postMessage(previewLookMessage(latest.current), window.location.origin);
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  useEffect(() => {
    latest.current = { color: look.color, position: look.position, language };
    if (isReady) {
      frame.current?.contentWindow?.postMessage(previewLookMessage(latest.current), window.location.origin);
    }
  }, [isReady, look.color, look.position, language]);

  return (
    <div className="min-w-0 space-y-3">
      {business.languages.length > 1 ? (
        <div role="group" aria-label={t("channelSetup.preview.languages")} className="flex flex-wrap gap-1.5">
          {business.languages.map((tag) => (
            <button
              key={tag}
              type="button"
              aria-pressed={tag === language}
              onClick={() => setLanguage(tag)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
                tag === language
                  ? "border-transparent bg-accent-soft text-accent"
                  : "border-line text-ink-muted hover:border-line-strong hover:text-ink",
              )}
            >
              {languageName(tag, locale)}
            </button>
          ))}
        </div>
      ) : null}
      <div className="relative h-[34rem] overflow-hidden rounded-xl border border-line bg-surface-muted sm:h-[38rem]">
        <iframe
          ref={frame}
          src={src}
          title={t("channelSetup.preview.frameTitle")}
          loading="lazy"
          referrerPolicy="same-origin"
          onLoad={() => setIsLoaded(true)}
          className={cn("size-full border-0 transition-opacity duration-300 motion-reduce:transition-none", isLoaded ? "opacity-100" : "opacity-0")}
        />
        {!isLoaded ? (
          <div className="absolute inset-0 flex items-center justify-center text-ink-muted">
            <Spinner label={t("channelSetup.preview.loading")} />
          </div>
        ) : null}
      </div>
      <p className="text-xs text-ink-subtle">{t("channelSetup.preview.hint")}</p>
    </div>
  );
}
