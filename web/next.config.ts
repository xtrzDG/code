import type { NextConfig } from "next";

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
  reactStrictMode: true,
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
    ];
  },
};

export default nextConfig;
