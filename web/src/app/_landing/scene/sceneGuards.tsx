"use client";

/**
 * What keeps a 3D scene (the landing hero's, the setup finale's) from
 * hurting the page it is on: an error boundary that hands over to the still
 * picture, and a frame-rate watch that lowers the resolution when frames are
 * slow and gives up when they stay slow.
 */

import { useFrame, useThree } from "@react-three/fiber";
import { Component, useRef, type ReactNode } from "react";

import { isFrameRateLow } from "@/lib/heroScene";

export class SceneBoundary extends Component<{ onError: () => void; children: ReactNode }, { failed: boolean }> {
  override state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  override componentDidCatch(): void {
    this.props.onError();
  }

  override render(): ReactNode {
    return this.state.failed ? null : this.props.children;
  }
}

/** Reports the first frame, then samples frame times once: slow → lower resolution → still slow → give up. */
export function FrameWatch({ onReady, onFallback }: { onReady: () => void; onFallback: () => void }) {
  const setDpr = useThree((state) => state.setDpr);
  const watch = useRef({ startedAt: -1, samples: [] as number[], lowered: false, done: false });
  useFrame((state, delta) => {
    const current = watch.current;
    if (current.startedAt < 0) {
      current.startedAt = state.clock.elapsedTime;
      onReady();
      return;
    }
    // The first second compiles shaders and uploads textures: not representative.
    if (current.done || state.clock.elapsedTime - current.startedAt < 1) {
      return;
    }
    current.samples.push(delta * 1000);
    if (current.samples.length < 90) {
      return;
    }
    if (!isFrameRateLow(current.samples)) {
      current.done = true;
    } else if (!current.lowered) {
      current.lowered = true;
      current.samples = [];
      setDpr(1);
    } else {
      current.done = true;
      onFallback();
    }
  });
  return null;
}
