# syntax=docker/dockerfile:1.7
#
# Backend image of Assistant Workshop: the API, the background worker and the
# migration runner share it (see docker/entrypoint.sh):
#
#   docker build -t assistant-workshop-backend .
#   docker run -p 8000:8000 --env-file .env assistant-workshop-backend api
#   docker run --env-file .env assistant-workshop-backend worker
#   docker run --env-file .env assistant-workshop-backend migrate
#   docker run --env-file .env assistant-workshop-backend backup

# Base images are named once, in FROM lines, so Dependabot can update them.
FROM ghcr.io/astral-sh/uv:0.12.21 AS uv
FROM python:3.14-slim AS python-base

# --- Dependencies ------------------------------------------------------------
FROM python-base AS builder

COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app
# Only the lock decides what is installed: no dev tools, nothing resolved.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-install-project

# --- Runtime -----------------------------------------------------------------
FROM python-base AS runtime

# Take the Debian security fixes published since the base image was built
# (image scans fail on fixable HIGH/CRITICAL findings). The Postgres client
# (pg_dump, pg_restore) serves `workshop backup` and `workshop restore-check`
# (docs/operations/backup-restore.md); it reads servers of older majors.
RUN apt-get update \
    && apt-get upgrade --yes --no-install-recommends \
    && apt-get install --yes --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 workshop \
    && useradd --system --uid 10001 --gid workshop --home-dir /app \
       --no-create-home --shell /usr/sbin/nologin workshop

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app ./app
COPY migrations ./migrations
# Texts of the data processing agreement served by GET /v1/legal/dpa/{version}.
COPY docs/legal ./docs/legal
COPY docker/entrypoint.sh /usr/local/bin/workshop

# Call recordings kept on this server (RECORDINGS_DIRECTORY); mount a volume
# here to keep them across deploys. The service never installs packages at
# runtime (the virtual environment comes from uv.lock), so the base image's
# pip is removed: less to attack and nothing for image scans to flag.
RUN python -m pip uninstall --yes --root-user-action=ignore pip \
    && chmod 0755 /usr/local/bin/workshop \
    && mkdir -p /app/var/recordings \
    && chown -R workshop:workshop /app/var

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    PORT=8000 \
    RECORDINGS_DIRECTORY=/app/var/recordings

USER 10001:10001
EXPOSE 8000

# The API answers GET /healthz; the worker and migrate containers turn the
# check off (docker-compose.yml) because they serve no HTTP.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT', '8000'), timeout=4)"]

ENTRYPOINT ["workshop"]
CMD ["api"]
