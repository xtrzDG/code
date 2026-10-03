"use client";

/**
 * A row that scrolls sideways when it does not fit (tabs, view chips on a
 * phone or a narrow column): the side with more to see fades out, so the
 * cut reads as "there is more" and never as a clipped label. The scrollbar
 * is hidden; touch, trackpad, Shift+wheel and the keyboard (focus moves
 * into view) scroll it. Scroll padding the width of the fade keeps an item
 * scrolled into view clear of it; no scroll snapping, which would scroll
 * the row's own leading padding away and cut the first label.
 */

import { useEffect, useRef, useState, type ReactNode } from "react";

import { cn } from "@/lib/cn";
import { scrollEdges, type ScrollEdges } from "@/lib/scrollEdges";

const FADE = "2rem";

function maskFor(edges: ScrollEdges): string | undefined {
  if (edges.left && edges.right) {
    return `linear-gradient(to right, transparent, black ${FADE}, black calc(100% - ${FADE}), transparent)`;
  }
  if (edges.left) {
    return `linear-gradient(to right, transparent, black ${FADE})`;
  }
  return edges.right ? `linear-gradient(to left, transparent, black ${FADE})` : undefined;
}

export function ScrollRow({ children, className }: { children: ReactNode; className?: string }) {
  const row = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState<ScrollEdges>({ left: false, right: false });

  useEffect(() => {
    const node = row.current;
    if (!node) {
      return;
    }
    const update = () => {
      const next = scrollEdges(node.scrollLeft, node.scrollWidth, node.clientWidth, getComputedStyle(node).direction === "rtl");
      setEdges((current) => (current.left === next.left && current.right === next.right ? current : next));
    };
    update();
    node.addEventListener("scroll", update, { passive: true });
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(update);
    observer?.observe(node);
    if (node.firstElementChild) {
      observer?.observe(node.firstElementChild);
    }
    return () => {
      node.removeEventListener("scroll", update);
      observer?.disconnect();
    };
  }, []);

  const mask = maskFor(edges);
  return (
    <div
      ref={row}
      data-scroll-row=""
      data-fade-left={edges.left || undefined}
      data-fade-right={edges.right || undefined}
      style={mask ? { maskImage: mask, WebkitMaskImage: mask } : undefined}
      className={cn("scroll-px-8 overflow-x-auto overscroll-x-contain [scrollbar-width:none] [&::-webkit-scrollbar]:hidden", className)}
    >
      {children}
    </div>
  );
}
