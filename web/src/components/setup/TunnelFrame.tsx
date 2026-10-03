"use client";

/**
 * The full-screen frame of "Create an AI assistant": the tunnel behind,
 * the top bar with the progress rail, the current screen in the middle
 * moving with depth, and a polite live region that tells screen readers
 * where they are after every move ("Step 3 of 8: What you offer").
 */

import type { ReactNode } from "react";

import { useI18n } from "@/i18n/client";
import { FINALE, placeIndex, stepNumber, TUNNEL_STEPS, type RailState, type TunnelPlace, type TunnelStep } from "@/lib/tunnel/steps";

import { TunnelBackdrop } from "./TunnelBackdrop";
import { TunnelHeader, type SaveState } from "./TunnelHeader";
import { TunnelRail } from "./TunnelRail";
import { TunnelStage } from "./TunnelStage";

export interface TunnelFrameProps {
  place: TunnelPlace;
  direction: 1 | -1 | 0;
  states: Record<TunnelStep, RailState>;
  canOpen: (step: TunnelStep) => boolean;
  onOpen: (step: TunnelStep) => void;
  saveState: SaveState;
  exitHref: string | null;
  homeHref: string;
  children: ReactNode;
}

export function TunnelFrame({ place, direction, states, canOpen, onOpen, saveState, exitHref, homeHref, children }: TunnelFrameProps) {
  const { t } = useI18n();
  const announcement =
    place === FINALE
      ? t("tunnel.announceFinale")
      : t("tunnel.announce", { number: stepNumber(place), total: TUNNEL_STEPS.length, title: t(`tunnel.steps.${place}`) });

  return (
    <div className="relative isolate flex min-h-dvh flex-col overflow-x-clip bg-canvas">
      <TunnelBackdrop depth={placeIndex(place)} burst={place === FINALE} />
      <TunnelHeader
        rail={place === FINALE ? <div className="flex-1" /> : <TunnelRail place={place} states={states} canOpen={canOpen} onOpen={onOpen} />}
        saveState={saveState}
        exitHref={place === FINALE ? false : exitHref}
        homeHref={homeHref}
      />
      <main id="main" className="relative z-10 flex flex-1 flex-col px-4 pt-6 pb-10 sm:px-6 sm:pt-12 lg:pt-16">
        <TunnelStage placeKey={place} direction={direction}>
          {children}
        </TunnelStage>
      </main>
      <p className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement}
      </p>
    </div>
  );
}
