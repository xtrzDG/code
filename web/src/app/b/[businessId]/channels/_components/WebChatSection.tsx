"use client";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";

import type { ChannelView } from "../_lib/channels";
import { WidgetAppearanceCard } from "./WidgetAppearanceCard";
import { WidgetSnippetCard } from "./WidgetSnippetCard";

/** The switched-on website chat: its look with a live preview, and the embed code. */
export function WebChatSection({
  channel,
  canManage,
  onSaved,
}: {
  channel: ChannelView;
  canManage: boolean;
  onSaved: (channel: ChannelView) => void;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const snippet = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/channels/web/snippet", {
        params: { path: { business_id: business.id } },
      }),
    [business.id],
  );

  return (
    <section aria-labelledby="channels-web-chat" className="space-y-4">
      <h2 id="channels-web-chat" className="text-lg font-semibold text-ink">
        {t("channels.kinds.web_chat")}
      </h2>
      {/* Remounted when the saved look changes, so the form starts from it. */}
      <WidgetAppearanceCard
        key={`${channel.widget_color ?? ""}:${channel.widget_position ?? ""}`}
        channel={channel}
        demoUrl={snippet.data?.demo_url}
        canManage={canManage}
        onSaved={onSaved}
      />
      <WidgetSnippetCard snippet={snippet} />
    </section>
  );
}
