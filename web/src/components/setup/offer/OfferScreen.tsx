"use client";

/**
 * Step 3, "What do you offer?": type the offer into a short table (the
 * niche's examples waiting for prices), or bring it from the website or a
 * menu. Optional: Continue without prices remembers it as skipped, so the
 * setup knows it is still open.
 *
 * In the edit mode it is "Offer" of Assistant → Business profile: the
 * same table with the kind and the minutes, saving itself, the same
 * imports, and the niche's questions about the offer under it.
 */

import { useState, type ReactNode } from "react";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Tabs } from "@/components/content/Tabs";
import { IconFile, IconGlobe, IconPencil } from "@/components/icons";
import { ErrorState, LoadingRegion, SkeletonRows, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { pricedCount } from "@/lib/tunnel/offer";
import { offerKinds } from "@/lib/wizard/offers";

import { SectionQuestions } from "../edit/SectionQuestions";
import { StepScreen } from "../StepScreen";
import type { StepContext } from "../flow/stepContext";
import type { StepMode } from "../stepMode";
import { OfferImport, type ImportSource } from "./OfferImport";
import { OfferTable } from "./OfferTable";
import { useOfferRows } from "./useOfferRows";

type Source = "type" | ImportSource;

export function OfferScreen({ ctx, mode = "tunnel" }: { ctx: StepContext; mode?: StepMode }) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const { currency } = useBusinessFormat();
  const [source, setSource] = useState<Source>("type");
  const [isSaving, setSaving] = useState(false);
  const isEdit = mode === "edit";
  const kinds = offerKinds(ctx.wizard.knowledge_kinds);
  const table = useOfferRows(business.id, ctx.starters.offer_examples ?? [], currency, kinds[0] ?? "service", mode);
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
      mode={mode}
      title={isEdit ? t("profileEdit.sections.offer.title") : t("tunnelOffer.offer.title")}
      text={isEdit ? t("profileEdit.sections.offer.text") : t("tunnelOffer.offer.text")}
      wide
      actions={isEdit ? {} : { onContinue: () => void leave(false), onBack: ctx.back, onSkip: () => void leave(true), isBusy: isSaving }}
    >
      <div className="space-y-8">
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
                  <OfferTable table={table} currency={currency} mode={mode} kinds={kinds} />
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
        {isEdit ? <SectionQuestions ctx={ctx} section="offer" title={t("profileEdit.offer.questionsTitle")} /> : null}
      </div>
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
