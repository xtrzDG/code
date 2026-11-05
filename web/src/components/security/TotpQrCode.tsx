"use client";

/**
 * The QR code an authenticator app scans: the otpauth:// link, drawn in the
 * browser (uqr; the secret never leaves the page). Black on white with the
 * standard quiet zone, so phone cameras read it in the dark theme too.
 */

import { useMemo } from "react";
import { encode } from "uqr";

const QUIET_ZONE = 4;

function modulePath(modules: boolean[][]): string {
  const parts: string[] = [];
  modules.forEach((row, y) => {
    let x = 0;
    while (x < row.length) {
      if (!row[x]) {
        x += 1;
        continue;
      }
      const start = x;
      while (x < row.length && row[x]) {
        x += 1;
      }
      parts.push(
        `M${start + QUIET_ZONE} ${y + QUIET_ZONE}h${x - start}v1h-${x - start}z`,
      );
    }
  });
  return parts.join("");
}

export function TotpQrCode({ uri, label }: { uri: string; label: string }) {
  const { side, path } = useMemo(() => {
    const result = encode(uri, { ecc: "M", border: 0 });
    return {
      side: result.size + 2 * QUIET_ZONE,
      path: modulePath(result.data),
    };
  }, [uri]);

  return (
    <svg
      role="img"
      aria-label={label}
      viewBox={`0 0 ${side} ${side}`}
      shapeRendering="crispEdges"
      className="size-44 shrink-0 rounded-lg border border-line bg-white"
    >
      <rect width={side} height={side} fill="#ffffff" />
      <path d={path} fill="#000000" />
    </svg>
  );
}
