import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs/config";

import { legacyRedirects } from "./src/lib/legacyRoutes";
import { sourceMapUploadOptions } from "./src/lib/monitoring/sourceMaps";

/**
 * Browsers take HSTS only over HTTPS, so a production build always sends it
 * (two years, subdomains, preload-ready); `next dev` does not. The Content
 * Security Policy needs a nonce per page view, so the proxy sets it
 * (src/proxy.ts, src/server/contentSecurityPolicy.ts).
 */
const STRICT_TRANSPORT_SECURITY =
  process.env.NODE_ENV === "production"
    ? [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" }]
    : [];

const nextConfig: NextConfig = {
  // The cabinet talks to the Python API only through its own route handlers
  // (src/app/api/*), so no rewrites or CORS are needed.
  poweredByHeader: false,
  experimental: {
    // Fewer, larger JavaScript chunks: a first visit (the public site above
    // all, budgets in lighthouserc.json) pays a round trip per file, while a
    // later page reuses what is cached either way. Sizes are of unminified
    // code (about 5x the gzipped size).
    turbopackChunking: { minChunkSize: 100_000, maxChunkCountPerGroup: 10 },
  },
  reactStrictMode: true,
  // Addresses from before the five sections (src/lib/legacyRoutes.ts).
  redirects: async () => legacyRedirects(),
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Permissions-Policy",
            value: "camera=(), geolocation=(), microphone=(self)",
          },
          // No other window keeps a handle on the cabinet, and no other site
          // may embed its files.
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
          { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
          ...STRICT_TRANSPORT_SECURITY,
        ],
      },
      {
        // The cabinet's live preview of the website chat frames the hosted
        // chat page of its own origin (src/lib/hostedChat/preview.ts); the
        // later rule wins, and the page's policy says frame-ancestors 'self'.
        source: "/c/:address",
        has: [{ type: "query", key: "preview", value: "1" }],
        headers: [{ key: "X-Frame-Options", value: "SAMEORIGIN" }],
      },
    ];
  },
};

// With SENTRY_AUTH_TOKEN (CI on main) the build uploads its source maps to
// Sentry and deletes them; otherwise the config is used as it is
// (src/lib/monitoring/sourceMaps.ts).
const sourceMapUpload = sourceMapUploadOptions(process.env);

export default sourceMapUpload === null ? nextConfig : withSentryConfig(nextConfig, sourceMapUpload);
