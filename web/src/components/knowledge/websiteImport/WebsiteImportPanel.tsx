"use client";

import { useState, type ReactNode } from "react";

import type { Schema } from "@/api/types";
import { Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { problemText } from "@/lib/knowledge/websiteImport";

import { useWebsiteImport } from "./useWebsiteImport";
import { WebsiteImportForm } from "./WebsiteImportForm";
import { WebsiteImportOutcome } from "./WebsiteImportOutcome";
import { WebsiteImportProgress } from "./WebsiteImportProgress";

export interface WebsiteImportPanelProps {
  businessId: string;
  /** Open the drafts of a finished import in the review (the import screen's drawer). */
  onReview: (result: Schema<"MenuImportResult">) => void;
  /** The address to offer before any import ran (the profile's website link). */
  suggestedUrl?: string | null;
  /** Without its own card, inside a host's (the setup wizard's step). */
  bare?: boolean;
}

/**
 * Import from the business's website, from the address to the drafts: the
 * form, the live progress of the queued import (it keeps running when the
 * owner leaves), and what it found. The drafts are reviewed by the host
 * (`onReview`); nothing is published from here.
 *
 * Used by Knowledge -> Import -> "From your website" and meant for the setup
 * wizard, which passes `bare` and its own review.
 */
export function WebsiteImportPanel({ businessId, onReview, suggestedUrl = null, bare = false }: WebsiteImportPanelProps) {
  const { t } = useI18n();
  const website = useWebsiteImport(businessId);
  const [isComposing, setComposing] = useState(false);
  const { view } = website;

  const start = async (url: string) => {
    if (await website.start(url)) {
      setComposing(false);
      website.acknowledgeFinished();
    }
  };

  let content: ReactNode;
  if (website.isLoading) {
    content = (
      <LoadingRegion label={t("common.loading")}>
        <SkeletonText lines={3} />
      </LoadingRegion>
    );
  } else if (!view && website.loadError) {
    content = <ErrorState error={website.loadError} onRetry={website.reload} />;
  } else if (view && website.isRunning) {
    content = <WebsiteImportProgress view={view} />;
  } else if (view?.status === "done" && !isComposing && hasOutcome(view)) {
    content = (
      <WebsiteImportOutcome
        view={view}
        justFinished={website.finished?.id === view.id}
        onReview={onReview}
        onAnother={() => {
          setComposing(true);
          website.acknowledgeFinished();
        }}
      />
    );
  } else {
    content = (
      <WebsiteImportForm
        initialUrl={view?.url ?? suggestedUrl ?? ""}
        failure={view?.status === "failed" && !isComposing && view.problem ? problemText(view.problem, view.problem_detail) : null}
        startError={website.startError}
        isStarting={website.isStarting}
        onStart={(url) => void start(url)}
      />
    );
  }

  if (bare) {
    return <div data-testid="website-import">{content}</div>;
  }
  return (
    <Card title={t("knowledge.website.title")} description={t("knowledge.website.description")} data-testid="website-import">
      {content}
    </Card>
  );
}

/**
 * A done import is worth showing while its drafts wait for review, or when
 * it found nothing at all; once its drafts were reviewed, the form returns.
 */
function hasOutcome(view: Schema<"WebsiteImportView">): boolean {
  const waiting = view.result?.items?.length ?? 0;
  return waiting > 0 || view.items_found === 0;
}
