"use client";

/**
 * A QR code of a link, drawn in the browser (nothing is sent anywhere):
 * dark modules on white whatever the theme, so every phone camera reads it.
 */

import { useMemo } from "react";

import { encodeQr, qrPath, qrSide } from "@/app/b/[businessId]/assistant/channels/_lib/qrCode";
import { cn } from "@/lib/cn";

export function QrImage({ value, label, className }: { value: string; label: string; className?: string }) {
  const matrix = useMemo(() => encodeQr(value), [value]);
  const side = qrSide(matrix);
  return (
    <div className={cn("rounded-xl bg-white p-1.5 shadow-sm ring-1 ring-line", className)}>
      <svg viewBox={`0 0 ${side} ${side}`} role="img" aria-label={label} shapeRendering="crispEdges" className="block size-full">
        <rect width={side} height={side} fill="#ffffff" />
        <path d={qrPath(matrix)} fill="#000000" />
      </svg>
    </div>
  );
}
