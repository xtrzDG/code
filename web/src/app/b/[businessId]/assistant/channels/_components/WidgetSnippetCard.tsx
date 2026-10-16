"use client";

import { useState } from "react";

import type { Query } from "@/api/useQuery";
import type { Schema } from "@/api/types";
import { Tabs } from "@/components/content/Tabs";
import { Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

/** Where an owner's website is made; each has its own place for the code. */
const SITE_PLATFORMS = ["any", "wordpress", "wix", "tilda", "shopify"] as const;

type SitePlatform = (typeof SITE_PLATFORMS)[number];

/** Brand names are the same in every language. */
const PLATFORM_NAMES: Record<Exclude<SitePlatform, "any">, string> = {
  wordpress: "WordPress",
  wix: "Wix",
  tilda: "Tilda",
  shopify: "Shopify",
};

const PLATFORM_STEPS: Record<SitePlatform, readonly [MessageKey, MessageKey, MessageKey]> = {
  any: ["channelSetup.install.steps.any.step1", "channelSetup.install.steps.any.step2", "channelSetup.install.steps.any.step3"],
  wordpress: [
    "channelSetup.install.steps.wordpress.step1",
    "channelSetup.install.steps.wordpress.step2",
    "channelSetup.install.steps.wordpress.step3",
  ],
  wix: ["channelSetup.install.steps.wix.step1", "channelSetup.install.steps.wix.step2", "channelSetup.install.steps.wix.step3"],
  tilda: ["channelSetup.install.steps.tilda.step1", "channelSetup.install.steps.tilda.step2", "channelSetup.install.steps.tilda.step3"],
  shopify: [
    "channelSetup.install.steps.shopify.step1",
    "channelSetup.install.steps.shopify.step2",
    "channelSetup.install.steps.shopify.step3",
  ],
};

/**
 * The website chat's code, as it must be pasted: one block that scrolls
 * sideways and never breaks a line inside a tag (`</script>`), with its
 * Copy button right on it; then where it goes on the owner's kind of site
 * (any site, WordPress, Wix, Tilda, Shopify), in three steps.
 */
export function WidgetSnippetCard({ snippet }: { snippet: Query<Schema<"WidgetSnippetView">> }) {
  const { t } = useI18n();
  const [platform, setPlatform] = useState<SitePlatform>("any");
  const tabs = SITE_PLATFORMS.map((key) => ({
    key,
    label: key === "any" ? t("channelSetup.install.anySite") : PLATFORM_NAMES[key],
  }));

  return (
    <Card title={t("channelSetup.install.title")} description={t("channelSetup.install.description")}>
      {snippet.error && !snippet.data ? (
        <ErrorState error={snippet.error} onRetry={snippet.reload} className="py-6" />
      ) : !snippet.data ? (
        <LoadingRegion label={t("common.loading")} className="py-1">
          <SkeletonText lines={4} />
        </LoadingRegion>
      ) : (
        <div className="space-y-5">
          <figure className="overflow-hidden rounded-xl border border-line bg-surface-muted">
            <figcaption className="flex items-center justify-between gap-3 border-b border-line py-1.5 ps-4 pe-1.5">
              <span id="widget-snippet-label" className="text-sm font-medium text-ink">
                {t("channels.widget.codeLabel")}
              </span>
              <CopyButton value={snippet.data.snippet} label={t("channels.widget.copyCode")} />
            </figcaption>
            <pre
              aria-labelledby="widget-snippet-label"
              dir="ltr"
              tabIndex={0}
              data-widget-snippet=""
              className="overflow-x-auto px-4 py-3 font-mono text-xs leading-relaxed whitespace-pre text-ink focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus sm:text-sm"
            >
              <code>{snippet.data.snippet}</code>
            </pre>
          </figure>
          <Tabs label={t("channelSetup.install.tabs")} tabs={tabs} selected={platform} onSelect={setPlatform}>
            <ol className="grid gap-3 text-sm text-ink-muted sm:grid-cols-3">
              {PLATFORM_STEPS[platform].map((step, index) => (
                <li key={step} className="flex gap-3 rounded-xl bg-surface-muted/60 p-3">
                  <span
                    className="flex size-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent"
                    aria-hidden
                  >
                    {index + 1}
                  </span>
                  <span>{t(step)}</span>
                </li>
              ))}
            </ol>
          </Tabs>
        </div>
      )}
    </Card>
  );
}
