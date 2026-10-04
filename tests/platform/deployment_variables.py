"""The variables the deployment files set, and how to read Render and Compose."""

import re

from tests.platform.environment_sources import read

# Deployment-only: read when the image starts (docker/entrypoint.sh runs
# uvicorn), not by the application. The Dockerfile, docker-compose.yml and
# render.yaml set them, so README.md describes them and .env.example does
# not list them.
DEPLOYMENT_VARIABLES: frozenset[str] = frozenset(
    {
        # uvicorn --port; the Dockerfile sets 8000, Render sets it too.
        "PORT",
        # uvicorn --proxy-headers: address ranges of the trusted proxies.
        "FORWARDED_ALLOW_IPS",
    }
)

# Docker Compose interpolation only (docker-compose.yml), for a local run:
# published ports and the local database roles.
COMPOSE_VARIABLES: frozenset[str] = frozenset(
    {
        "API_PORT",
        "WEB_PORT",
        "POSTGRES_PASSWORD",
        "WORKSHOP_DB_USER",
        "WORKSHOP_DB_PASSWORD",
        "WORKSHOP_DB_NAME",
    }
)

# What every deployment of the backend (API and worker) sets: without them
# production refuses to start, keeps no data, cannot be reached by webhooks
# or cannot send owners back to the cabinet.
REQUIRED_BACKEND_VARIABLES: frozenset[str] = frozenset(
    {
        "APP_ENV",
        "APP_BASE_URL",
        "CABINET_BASE_URL",
        "CORS_ALLOWED_ORIGINS",
        "DATABASE_URL",
        "ENCRYPTION_KEY",
        "FORWARDED_ALLOW_IPS",
    }
)
REQUIRED_CABINET_VARIABLES: frozenset[str] = frozenset({"BACKEND_URL", "COOKIE_SECURE"})

# .env.example variables without a default value that the Render API may
# leave out; the Blueprint asks for every other one when it is created.
RENDER_OPTIONAL_VARIABLES: frozenset[str] = frozenset(
    {
        # The default follows LLM_PROVIDER (gpt-5-mini, claude-opus-5-5).
        "LLM_MODEL_ID",
        "LLM_JUDGE_MODEL_ID",
        # Call summaries use LLM_MODEL_ID when it is unset.
        "LLM_SUMMARY_MODEL_ID",
        # The default follows LLM_PROVIDER (the other provider's model).
        "LLM_FALLBACK_MODEL_ID",
        # The default follows LLM_PROVIDER (its cheap model; none: scripted).
        "LLM_VERIFIER_MODEL_ID",
        # Development and tests only; refused in production.
        "OTP_LOG_CODES",
        # The default follows APP_ENV (json in production) and THREADPOOL_SIZE.
        "LOG_FORMAT",
        "DB_POOL_SIZE",
        # Render sets RENDER_GIT_COMMIT itself on every service; APP_RELEASE
        # names the build on other platforms.
        "RENDER_GIT_COMMIT",
        "APP_RELEASE",
        # Render's database is a direct connection, so LISTEN works on
        # DATABASE_URL; only a transaction pooler needs a second address.
        "LIVE_EVENTS_DATABASE_URL",
        # Empty until a key rotation; then set in the env group
        # workshop-backend (docs/operations/backup-restore.md).
        "ENCRYPTION_KEYS",
        # Optional contacts of "Help and support"; set in the env group
        # workshop-backend when the team has them (docs/LAUNCH.md).
        "SUPPORT_WHATSAPP",
        "SUPPORT_TELEGRAM",
        "SUPPORT_EMAIL",
        # The restore drill runs in GitHub Actions (restore-drill.yml), never
        # on Render: production holds no private backup key.
        "BACKUP_AGE_IDENTITY",
        "RESTORE_CHECK_DATABASE_URL",
        # The image has the Postgres client on the PATH.
        "POSTGRES_CLIENT_BIN_DIRECTORY",
    }
)

# Read only by the backup cron job (workshop-backup), which Render asks for
# them; the API and the worker never get the bucket's credentials.
BACKUP_JOB_VARIABLES: frozenset[str] = frozenset(
    {
        "BACKUP_S3_ENDPOINT_URL",
        "BACKUP_S3_REGION",
        "BACKUP_S3_BUCKET",
        "BACKUP_S3_ACCESS_KEY_ID",
        "BACKUP_S3_SECRET_ACCESS_KEY",
        "BACKUP_AGE_PUBLIC_KEY",
    }
)


def indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def render_services(blueprint_path: str = "render.yaml") -> dict[str, set[str]]:
    """Variables of each Render service, those of its groups included."""

    blueprint: str = read(blueprint_path)
    groups_text, services_text = blueprint.split("\nservices:\n", 1)
    groups_text = groups_text.split("\nenvVarGroups:\n", 1)[1]
    groups: dict[str, set[str]] = {}
    for chunk in re.split(r"^  - name: ", groups_text, flags=re.MULTILINE)[1:]:
        group_name: str = chunk.split("\n", 1)[0].strip()
        groups[group_name] = set(re.findall(r"- key: ([A-Z0-9_]+)", chunk))

    services: dict[str, set[str]] = {}
    for chunk in re.split(r"^  - type: ", services_text, flags=re.MULTILINE)[1:]:
        name_match = re.search(r"^    name: (\S+)$", chunk, re.MULTILINE)
        assert name_match is not None
        variables: set[str] = set(re.findall(r"- key: ([A-Z0-9_]+)", chunk))
        for group_name in re.findall(r"- fromGroup: (\S+)", chunk):
            variables |= groups[group_name]
        services[name_match.group(1)] = variables

    return services


def compose_environment(block_line: str) -> dict[str, str]:
    """`environment:` of the Compose block that starts with this line."""

    lines: list[str] = read("docker-compose.yml").splitlines()
    start: int = lines.index(block_line)
    block_indentation: int = indentation(block_line)
    environment_indentation: int | None = None
    variables: dict[str, str] = {}
    for line in lines[start + 1 :]:
        if line.strip() == "" or line.lstrip().startswith("#"):
            continue

        line_indentation: int = indentation(line)
        if line_indentation <= block_indentation:
            break

        if environment_indentation is None:
            if line.strip() == "environment:":
                environment_indentation = line_indentation
            continue

        if line_indentation <= environment_indentation:
            break

        name, value = line.strip().split(": ", 1)
        variables[name] = value

    return variables


def compose_default(value: str) -> str:
    """The default of `${NAME:-default}`."""

    match = re.fullmatch(r"\$\{[A-Z][A-Z0-9_]*:-(.+)\}", value)
    assert match is not None, value
    return match.group(1)
