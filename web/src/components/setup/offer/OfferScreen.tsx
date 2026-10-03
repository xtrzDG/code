"use client";

/**
 * Step 3, "What do you offer?": type the offer into a short table (the
 * niche's examples waiting for prices), or bring it from the website or a
 * menu. Optional: Continue without prices remembers it as skipped, so the
 * setup knows it is still open.
 */

import { useState, type ReactNode } from "react";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Tabs } from "@/components/content/Tabs";
import { IconFile, IconGlobe, IconPencil } from "@/components/icons";
import { ErrorState, LoadingRegion, SkeletonRows, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { pricedCount } from "@/lib/tunnel/offer";
import { offerKinds } from "@/lib/wizard/offers";

import { StepScreen } from "../StepScreen";
import type { StepContext } from "../flow/stepContext";
import { OfferImport, type ImportSource } from "./OfferImport";
import { OfferTable } from "./OfferTable";
import { useOfferRows } from "./useOfferRows";

type Source = "type" | ImportSource;

export function OfferScreen({ ctx }: { ctx: StepContext }) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const { currency } = useBusinessFormat();
  const [source, setSource] = useState<Source>("type");
  const [isSaving, setSaving] = useState(false);
  const kind = offerKinds(ctx.wizard.knowledge_kinds)[0] ?? "service";
  const table = useOfferRows(business.id, ctx.starters.offer_examples ?? [], currency, kind);
  const priced = pricedCount(table.rows, currency);

  const leave = async (skip: boolean) => {
    setSaving(true);
    const saved = await table.saveAll();
    setSaving(false);
    if (!saved) {
      setSource("type");
      return;
    }
    ctx.refresh();
    if (skip || priced === 0) {
      await ctx.skip("offer");
    } else {
      ctx.next();
    }
  };

  const onAdded = (count: number) => {
    toast.success(tp("tunnelOffer.offer.importedTitle", count));
    table.reload();
    setSource("type");
  };

  return (
    <StepScreen
      step="offer"
      title={t("tunnelOffer.offer.title")}
      text={t("tunnelOffer.offer.text")}
      wide
      actions={{ onContinue: () => void leave(false), onBack: ctx.back, onSkip: () => void leave(true), isBusy: isSaving }}
    >
      <Tabs
        label={t("tunnelOffer.offer.sourcesLabel")}
        tabs={[
          { key: "type", label: <Label icon={<IconPencil className="size-4" aria-hidden />} text={t("tunnelOffer.offer.sources.type")} /> },
          { key: "website", label: <Label icon={<IconGlobe className="size-4" aria-hidden />} text={t("tunnelOffer.offer.sources.website")} /> },
          { key: "menu", label: <Label icon={<IconFile className="size-4" aria-hidden />} text={t("tunnelOffer.offer.sources.menu")} /> },
        ]}
        selected={source}
        onSelect={(next) => {
          // What was typed is kept before the import opens.
          void table.saveAll().then(() => setSource(next));
        }}
      >
        <div className="pt-5">
          {source === "type" ? (
            table.error && table.isLoading ? (
              <ErrorState error={table.error} onRetry={table.reload} />
            ) : table.isLoading ? (
              <LoadingRegion label={t("common.loading")}>
                <SkeletonRows rows={3} />
              </LoadingRegion>
            ) : (
              <div className="space-y-4">
                <OfferTable table={table} currency={currency} />
                <p className="text-sm font-medium text-ink-muted" aria-live="polite">
                  {tp("tunnelOffer.offer.priced", priced)}
                </p>
              </div>
            )
          ) : (
            <OfferImport businessId={business.id} source={source} onAdded={onAdded} />
          )}
        </div>
      </Tabs>
    </StepScreen>
  );
}

function Label({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <>
      {icon}
      {text}
    </>
  );
}
