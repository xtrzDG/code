# syntax=docker/dockerfile:1.7
#
# Owner cabinet (Next.js). A regular `next build` + `next start` image (the
# config does not use the standalone output).
#
#   docker build -t assistant-workshop-web web
#   docker run -p 3000:3000 -e BACKEND_URL=http://api:8000 assistant-workshop-web
#
# Runtime variables: BACKEND_URL (the Python API, server side only) and
# COOKIE_SECURE ("false" only when served over plain http).

# The base image is named once, in a FROM line, so Dependabot can update it.
FROM node:22-bookworm-slim AS node-base

# --- Dependencies ------------------------------------------------------------
FROM node-base AS deps
WORKDIR /web
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

# --- Build -------------------------------------------------------------------
FROM node-base AS build
WORKDIR /web
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /web/node_modules ./node_modules
COPY . .
# The server renders Georgian and Russian dates and plurals: refuse a Node
# without full ICU (scripts/check-intl.mjs).
RUN node scripts/check-intl.mjs \
    && npm run build \
    && npm prune --omit=dev --no-audit --no-fund

# --- Runtime -----------------------------------------------------------------
FROM node-base AS runtime
WORKDIR /web
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

COPY --from=build --chown=node:node /web/package.json /web/package-lock.json ./
COPY --from=build --chown=node:node /web/next.config.ts /web/tsconfig.json ./
COPY --from=build --chown=node:node /web/public ./public
COPY --from=build --chown=node:node /web/node_modules ./node_modules
COPY --from=build --chown=node:node /web/.next ./.next

# The server runs node_modules/.bin/next with node alone: package managers
# (npm, npx, corepack, yarn) and their bundled dependencies are removed so
# they are neither an attack surface nor a source of image-scan findings.
RUN rm -rf /usr/local/lib/node_modules /opt/yarn-* \
        /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
        /usr/local/bin/yarn /usr/local/bin/yarnpkg

# The image's unprivileged "node" user.
USER 1000:1000
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:' + (process.env.PORT || 3000) + '/login').then((r) => process.exit(r.status < 500 ? 0 : 1), () => process.exit(1))"]

CMD ["sh", "-c", "exec node_modules/.bin/next start --hostname 0.0.0.0 --port \"${PORT:-3000}\""]
