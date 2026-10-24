"use client";

/**
 * Motion for the cabinet, mounted once by the root layout on its pages
 * (inside MotionPreferenceProvider), through CabinetMotion: a chunk of its
 * own, which public pages never load.
 *
 * - LazyMotion: the `m.*` elements ship without their animation code, which
 *   loads right after the page (`motionFeatures.ts`, domMax: gestures,
 *   in-view, layout and shared-layout animations). `strict` makes a stray
 *   `motion.div` (the heavy, all-inclusive element) throw: use `m.div`.
 * - MotionConfig: with the device's `prefers-reduced-motion` ("user") or
 *   the cabinet's own "Reduce motion" ("always") every transform and
 *   layout animation jumps to its end and fades stay short. It carries the
 *   page's nonce: AnimatePresence's "popLayout" writes a <style> element,
 *   which the Content Security Policy refuses without it.
 *
 * The public site moves in CSS alone (src/components/siteMotion; a policy
 * test keeps `motion/react` out of its pages): the root layout renders no
 * CabinetMotion there, so not even this provider's part of the library
 * loads. The toast list brings its own.
 */

import { LazyMotion, MotionConfig } from "motion/react";
import type { ReactNode } from "react";

import { useNonce } from "@/components/csp/NonceProvider";

import { useMotionPreference } from "./MotionPreference";

const loadFeatures = () => import("./motionFeatures").then((module) => module.default);

export function MotionProvider({ children }: { children: ReactNode }) {
  const { preference } = useMotionPreference();
  const nonce = useNonce();
  return (
    <LazyMotion features={loadFeatures} strict>
      <MotionConfig reducedMotion={preference === "reduce" ? "always" : "user"} nonce={nonce}>
        {children}
      </MotionConfig>
    </LazyMotion>
  );
}
