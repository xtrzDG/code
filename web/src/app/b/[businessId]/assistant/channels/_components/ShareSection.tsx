"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { Card, ErrorState, Field, LoadingRegion, Select, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { isShareSource, SHARE_SOURCES, SOURCE_LABELS, usableLinks, type ShareLinkKind, type ShareSource } from "../_lib/share";
import { QrCard } from "./QrCard";
import { ShareAddress } from "./ShareAddress";
import { ShareLinkList } from "./ShareLinkList";

/**
 * Channels → Share: the hosted chat page's address and a link per channel,
 * tagged with where they will be put, and a QR code (PNG, SVG, a printable
 * table card) of the chosen link.
 */
export function ShareSection({ isWebChatOn, accent }: { isWebChatOn: boolean; accent: string | null }) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const [source, setSource] = useState<ShareSource>("");
  const [selected, setSelected] = useState<ShareLinkKind>("hosted_chat");
  const links = useQuery(
    queryKeys.channels.share(business.id, source),
    () =>
      api.GET("/v1/businesses/{business_id}/share-links", {
        params: { path: { business_id: business.id }, query: source ? { src: source } : {} },
      }),
    { keepPreviousData: true },
  );

  const usable = usableLinks(links.data);
  const qrLink = usable.find((link) => link.kind === selected) ?? usable[0] ?? null;

  return (
    <section aria-labelledby="channels-share" className="space-y-4">
      <div className="space-y-1">
        <h2 id="channels-share" className="text-lg font-semibold text-ink">
          {t("share.title")}
        </h2>
        <p className="text-sm text-ink-muted">{t("share.description")}</p>
      </div>
      {links.error && !links.data ? (
        <Card>
          <ErrorState error={links.error} onRetry={links.reload} className="py-6" />
        </Card>
      ) : !links.data ? (
        <Card>
          <LoadingRegion label={t("common.loading")} className="py-1">
            <SkeletonText lines={5} />
          </LoadingRegion>
        </Card>
      ) : (
        <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
          <Card className={links.isPlaceholder ? "opacity-70 transition-opacity" : undefined}>
            <div className="space-y-6">
              <Field label={t("share.sourceLabel")} hint={t("share.sourceHint")}>
                {(control) => (
                  <Select
                    {...control}
                    className="max-w-xs"
                    value={source}
                    onChange={(event) => {
                      const next = event.target.value;
                      setSource(isShareSource(next) ? next : "");
                    }}
                  >
                    {SHARE_SOURCES.map((option) => (
                      <option key={option || "none"} value={option}>
                        {t(SOURCE_LABELS[option])}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
              <ShareAddress view={links.data} isWebChatOn={isWebChatOn} canManage={isOwner} />
              <ShareLinkList
                links={links.data.links}
                selected={qrLink?.kind ?? null}
                onSelect={setSelected}
              />
            </div>
          </Card>
          {qrLink ? (
            <QrCard
              link={qrLink}
              slug={links.data.slug}
              source={source}
              accent={accent}
              businessName={business.name}
              languages={business.languages}
              defaultLanguage={business.default_language}
            />
          ) : null}
        </div>
      )}
    </section>
  );
}
