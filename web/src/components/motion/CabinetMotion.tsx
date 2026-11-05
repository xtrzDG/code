"use client";

/**
 * The cabinet's MotionProvider as a chunk of its own. The root layout imports
 * this file on every page but renders it on cabinet pages alone, so the part
 * of the motion library MotionProvider brings (LazyMotion, MotionConfig) loads
 * only there. A static import of MotionProvider in the root layout put it on
 * every public page before the first paint, rendered or not; a server
 * component's `dynamic()` does not split a client component off, this
 * client one does.
 */

import dynamic from "next/dynamic";

export const CabinetMotion = dynamic(() => import("./MotionProvider").then((module) => module.MotionProvider));
