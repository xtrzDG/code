"use client";

/**
 * "Confirm it is you", mounted once in the root layout so every page has
 * it: it listens to the step-up broker (src/api/stepUp.ts) and loads the
 * form (StepUpForm) only when a sensitive action asks for a confirmation,
 * so pages that never need one (the landing page, the hosted chat) do not
 * carry it.
 */

import dynamic from "next/dynamic";
import { useSyncExternalStore } from "react";

import { isStepUpPending, subscribeStepUp } from "@/api/stepUp";

const StepUpForm = dynamic(() => import("./StepUpForm"), { ssr: false });

export function StepUpDialog() {
  const open = useSyncExternalStore(subscribeStepUp, isStepUpPending, () => false);
  return open ? <StepUpForm /> : null;
}
