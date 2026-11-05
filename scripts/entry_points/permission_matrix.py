"""
The written permission matrix (`docs/security/permission-matrix.md`):
which role reaches which operations, generated from the classified API
operations and the platform admin roles' permissions in code, so it cannot
drift from what the authorization tests prove.
"""

from collections import Counter
from collections.abc import Sequence

from app.schemas.constants.access import PlatformAdminPermission, PlatformAdminRole
from app.utilities.security.admin_permissions import has_permission
from scripts.entry_points.access_classes import (
    ACCESS_CLASSES,
    OWNER,
    STAFF,
    HttpEntryPoint,
)
from scripts.entry_points.api_routes import BRAND_PREFIX, BUSINESS_PREFIX
from scripts.entry_points.permission_matrix_texts import (
    BUSINESS_AREAS_INTRO,
    HEADER,
    roles_section,
)


def area_of(path: str, prefix: str) -> str:
    """`/bookings` of `/v1/businesses/{business_id}/bookings/{booking_id}`."""

    rest: str = path.removeprefix(prefix).strip("/")
    return "/" + rest.split("/")[0] if rest else "(itself)"


def class_counts(
    api: Sequence[HttpEntryPoint], cabinet: Sequence[HttpEntryPoint]
) -> list[str]:
    totals: Counter[str] = Counter(entry.access for entry in api)
    changing: Counter[str] = Counter(e.access for e in api if e.changes_state)
    in_cabinet: Counter[str] = Counter(entry.access for entry in cabinet)
    lines: list[str] = [
        "| Access class | API operations | Of them changing state | Cabinet routes |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name in ACCESS_CLASSES:
        if totals[name] or in_cabinet[name]:
            lines.append(
                f"| `{name}` | {totals[name]} | {changing[name]} | {in_cabinet[name]} |"
            )
    lines.append(
        f"| **All** | {len(api)} | {sum(changing.values())} | {len(cabinet)} |"
    )
    return lines


def area_rows(api: Sequence[HttpEntryPoint], prefix: str) -> list[str]:
    """Per area: operations, owner-only ones, what members may read and change."""

    areas: dict[str, list[HttpEntryPoint]] = {}
    for entry in api:
        if entry.access in (OWNER, STAFF) and (
            entry.path == prefix or entry.path.startswith(prefix + "/")
        ):
            areas.setdefault(area_of(entry.path, prefix), []).append(entry)
    lines: list[str] = [
        "| Area | Operations | Owner only | Members may read | Members may change |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for area, entries in sorted(areas.items()):
        owners: int = sum(1 for entry in entries if entry.access == OWNER)
        reads: int = sum(
            1 for e in entries if e.access == STAFF and not e.changes_state
        )
        writes: int = sum(1 for e in entries if e.access == STAFF and e.changes_state)
        lines.append(f"| `{area}` | {len(entries)} | {owners} | {reads} | {writes} |")
    return lines


def admin_rows() -> list[str]:
    roles: list[PlatformAdminRole] = list(PlatformAdminRole)
    lines: list[str] = [
        "| Permission | " + " | ".join(f"`{role.value}`" for role in roles) + " |",
        "| --- |" + " :---: |" * len(roles),
    ]
    for permission in PlatformAdminPermission:
        cells: list[str] = [
            "yes" if has_permission(role, permission) else "no" for role in roles
        ]
        lines.append(f"| `{permission.value}` | " + " | ".join(cells) + " |")
    return lines


def render_permission_matrix(
    api: Sequence[HttpEntryPoint], cabinet: Sequence[HttpEntryPoint]
) -> str:
    """The whole document, ending with a newline."""

    sections: list[str] = [
        HEADER,
        roles_section(),
        "## Entry points by access class\n",
        "\n".join(class_counts(api, cabinet)) + "\n",
        BUSINESS_AREAS_INTRO,
        "\n".join(area_rows(api, BUSINESS_PREFIX)) + "\n",
        "## A brand's operations (`/v1/brands/{brand_id}`)\n",
        "A brand owner holds every one; a regional manager reads, and is "
        "refused (403) the owner-only ones "
        "(`tests/platform/test_brand_authorization_matrix.py`).\n",
        "\n".join(area_rows(api, BRAND_PREFIX)) + "\n",
        "## Platform admin roles\n",
        "Each admin operation (`/v1/admin/*`) asks its use case for one "
        "permission; a role holds a fixed set "
        "(`app/utilities/security/admin_permissions.py`, proven by "
        "`tests/users/access/test_admin_team.py`, "
        "`tests/users/access/test_support_access_roles.py` and "
        "`tests/users/access/test_admin_role_sessions.py`).\n",
        "\n".join(admin_rows()) + "\n",
    ]
    return "\n".join(sections)
