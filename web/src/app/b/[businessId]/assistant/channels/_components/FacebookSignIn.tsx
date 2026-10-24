"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconFacebook } from "@/components/icons";
import { Alert, Button } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import type { ChannelView } from "../_lib/channels";
import { META_ERROR_OVERRIDES, metaRefusalKey } from "../_lib/metaRefusals";
import type { MetaChannel } from "../_lib/metaSignIn";
import { useFacebookSignIn, type FacebookNotice } from "../_lib/useFacebookSignIn";
import { MetaPagePicker } from "./MetaPagePicker";

const INTROS: Record<MetaChannel, MessageKey> = {
  whatsapp: "metaConnect.intro.whatsapp",
  instagram: "metaConnect.intro.instagram",
  messenger: "metaConnect.intro.messenger",
};

const NOTICES: Record<FacebookNotice, MessageKey> = {
  cancelled: "metaConnect.notices.cancelled",
  failed: "metaConnect.notices.failed",
  unavailable: "metaConnect.notices.unavailable",
};

/**
 * "Continue with Facebook" in a Meta channel's connect dialog: WhatsApp
 * Embedded Signup, or the page picker of Instagram and Messenger
 * (_lib/useFacebookSignIn.ts). `onConnected` gets the connected channel.
 */
export function FacebookSignIn({ kind, onConnected }: { kind: MetaChannel; onConnected: (channel: ChannelView) => void }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const signIn = useFacebookSignIn({ businessId: business.id, kind, locale, isOffered: true, onConnected });
  const { step, notice, error } = signIn;
  const isWaiting = step.name === "window" || step.name === "finishing";
  const status = step.name === "window" ? t("metaConnect.waiting") : step.name === "finishing" ? t("metaConnect.finishing") : "";
  const refusal = metaRefusalKey(error);

  return (
    <section aria-label={t("metaConnect.continue")} className="space-y-3 rounded-xl border border-line bg-surface-muted/60 p-4">
      <p className="text-sm text-ink-muted">{t(INTROS[kind])}</p>

      {kind !== "whatsapp" && (step.name === "pages" || step.name === "connecting") ? (
        <MetaPagePicker
          kind={kind}
          pages={step.pages}
          pickingId={step.name === "connecting" ? step.pageId : null}
          onPick={signIn.pickPage}
        />
      ) : step.name === "ready" ? (
        <div className="space-y-2">
          <p className="text-sm text-ink-muted">{t("metaConnect.openHint")}</p>
          <Button onClick={signIn.openWindow} leadingIcon={<IconFacebook aria-hidden className="size-4" />}>
            {t("metaConnect.openWindow")}
          </Button>
        </div>
      ) : (
        <Button
          onClick={signIn.begin}
          disabled={notice === "unavailable"}
          isLoading={step.name === "starting" || isWaiting || (!signIn.isSdkReady && notice === null)}
          loadingText={step.name === "idle" ? t("metaConnect.preparing") : t("metaConnect.starting")}
          leadingIcon={<IconFacebook aria-hidden className="size-4" />}
        >
          {t("metaConnect.continue")}
        </Button>
      )}

      <p role="status" aria-live="polite" className={status ? "text-sm text-ink-muted" : "sr-only"}>
        {status}
      </p>
      {notice ? <Alert tone="warning">{t(NOTICES[notice])}</Alert> : null}
      {refusal ? (
        <Alert tone="danger">{t(refusal)}</Alert>
      ) : (
        <InlineError error={error} overrides={META_ERROR_OVERRIDES} />
      )}
    </section>
  );
}
