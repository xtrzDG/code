"""
The repository settings the project's security relies on but no file can
hold: protection of the default branch, private vulnerability reporting and
Dependabot security updates (SECURITY.md, "Repository settings").

.github/workflows/repo-settings.yml reads them with `gh api --include`, one
file per endpoint, and scripts/check_repository_settings.py judges the files
against the reviewed expectations in .github/repository-settings.json:

    protection-<branch>.http  GET repos/{repo}/branches/{branch}/protection
    rules-<branch>.http       GET repos/{repo}/rules/branches/{branch}
    reporting.http            GET repos/{repo}/private-vulnerability-reporting
    security-fixes.http       GET repos/{repo}/automated-security-fixes

A branch is protected by its classic protection, by the active rulesets
that apply to it, or by both: GitHub enforces every one of them, so a
requirement holds when either source sets it.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, cast

STATUS_LINE: re.Pattern[str] = re.compile(r"^HTTP/\S+ (\d{3})")
# GitHub's 404 for a branch without classic protection; any other 404
# means the token cannot see the repository or the branch.
NOT_PROTECTED_MESSAGE: str = "Branch not protected"
NOT_FOUND: int = 404


class SettingsError(ValueError):
    """An expectation or a response cannot be used: the check proves nothing."""


@dataclass(frozen=True)
class Response:
    status: int
    body: object

    @property
    def message(self) -> str:
        return str(mapping(self.body).get("message", ""))


@dataclass(frozen=True)
class BranchExpectation:
    branch: str
    pull_request_required: bool
    required_approving_review_count: int
    required_status_checks: tuple[str, ...]
    force_pushes_blocked: bool
    deletions_blocked: bool


@dataclass(frozen=True)
class Expectations:
    branches: tuple[BranchExpectation, ...]
    private_vulnerability_reporting: bool
    dependabot_security_updates: bool


@dataclass(frozen=True)
class BranchProtection:
    pull_request_required: bool = False
    approving_review_count: int = 0
    status_checks: frozenset[str] = frozenset()
    force_pushes_blocked: bool = False
    deletions_blocked: bool = False


def parse_response(text: str) -> Response:
    """The status and JSON body of `gh api --include` output."""

    head, separator, body = text.replace("\r\n", "\n").partition("\n\n")
    status = STATUS_LINE.match(head)
    if status is None or separator == "":
        raise SettingsError("not a `gh api --include` answer (no HTTP status line)")
    try:
        parsed: object = json.loads(body) if body.strip() else None
    except ValueError as error:
        raise SettingsError(f"HTTP {status.group(1)}: the body is not JSON") from error
    return Response(int(status.group(1)), parsed)


def unusable(endpoint: str, response: Response) -> SettingsError:
    if response.status == 401:
        reason = "the token is missing, expired or revoked"
    elif response.status == 403:
        reason = "the token may not read it (it needs Administration: read)"
    else:
        reason = f"HTTP {response.status} {response.message}".rstrip()
    return SettingsError(f"{endpoint}: {reason}")


def is_object(value: object) -> bool:
    """A JSON object, without narrowing the value's type (it stays unknown)."""

    return isinstance(value, dict)


def is_array(value: object) -> bool:
    return isinstance(value, list)


def mapping(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if is_object(value) else {}


def items(value: object) -> list[Any]:
    return cast(list[Any], value) if is_array(value) else []


def is_enabled(setting: object) -> bool:
    return mapping(setting).get("enabled") is True


def classic_protection(branch: str, response: Response) -> BranchProtection:
    endpoint = f"branches/{branch}/protection"
    if response.status == NOT_FOUND and response.message == NOT_PROTECTED_MESSAGE:
        return BranchProtection()
    if response.status != 200 or not is_object(response.body):
        raise unusable(endpoint, response)
    body = mapping(response.body)
    reviews = body.get("required_pull_request_reviews")
    checks = mapping(body.get("required_status_checks"))
    contexts = {str(each) for each in items(checks.get("contexts"))}
    contexts |= {
        str(mapping(each).get("context")) for each in items(checks.get("checks"))
    }
    return BranchProtection(
        pull_request_required=isinstance(reviews, dict),
        approving_review_count=int(
            mapping(reviews).get("required_approving_review_count", 0)
        ),
        status_checks=frozenset(contexts),
        force_pushes_blocked=not is_enabled(body.get("allow_force_pushes")),
        deletions_blocked=not is_enabled(body.get("allow_deletions")),
    )


def ruleset_protection(branch: str, response: Response) -> BranchProtection:
    """The active ruleset rules GitHub applies to the branch."""

    if response.status != 200 or not is_array(response.body):
        raise unusable(f"rules/branches/{branch}", response)
    rules = [mapping(each) for each in items(response.body)]
    types = {str(rule.get("type")) for rule in rules}

    def parameters_of(rule_type: str) -> list[dict[str, Any]]:
        return [
            mapping(rule.get("parameters"))
            for rule in rules
            if rule.get("type") == rule_type
        ]

    approvals = [
        int(each.get("required_approving_review_count", 0))
        for each in parameters_of("pull_request")
    ]
    checks = {
        str(mapping(check).get("context"))
        for each in parameters_of("required_status_checks")
        for check in items(each.get("required_status_checks"))
    }
    return BranchProtection(
        pull_request_required="pull_request" in types,
        approving_review_count=max(approvals, default=0),
        status_checks=frozenset(checks),
        force_pushes_blocked="non_fast_forward" in types,
        deletions_blocked="deletion" in types,
    )


def combined(first: BranchProtection, second: BranchProtection) -> BranchProtection:
    return BranchProtection(
        pull_request_required=first.pull_request_required
        or second.pull_request_required,
        approving_review_count=max(
            first.approving_review_count, second.approving_review_count
        ),
        status_checks=first.status_checks | second.status_checks,
        force_pushes_blocked=first.force_pushes_blocked or second.force_pushes_blocked,
        deletions_blocked=first.deletions_blocked or second.deletions_blocked,
    )


def branch_problems(
    expected: BranchExpectation, protection: BranchProtection
) -> list[str]:
    branch = expected.branch
    if protection == BranchProtection():
        return [f"{branch}: not protected (no branch protection rule, no ruleset)"]
    problems: list[str] = []
    if expected.pull_request_required and not protection.pull_request_required:
        problems.append(f"{branch}: commits can be pushed without a pull request")
    if protection.approving_review_count < expected.required_approving_review_count:
        problems.append(
            f"{branch}: {protection.approving_review_count} approving review(s)"
            f" required, {expected.required_approving_review_count} expected"
        )
    missing = sorted(set(expected.required_status_checks) - protection.status_checks)
    if missing:
        problems.append(f"{branch}: required checks missing: {', '.join(missing)}")
    if expected.force_pushes_blocked and not protection.force_pushes_blocked:
        problems.append(f"{branch}: force pushes are allowed")
    if expected.deletions_blocked and not protection.deletions_blocked:
        problems.append(f"{branch}: the branch can be deleted")
    return problems


def reporting_problems(expected: Expectations, response: Response) -> list[str]:
    if response.status != 200 or not is_object(response.body):
        raise unusable("private-vulnerability-reporting", response)
    if expected.private_vulnerability_reporting and not is_enabled(response.body):
        return ["private vulnerability reporting is off"]
    return []


def security_fixes_problems(expected: Expectations, response: Response) -> list[str]:
    # 404: Dependabot security updates are off (the other endpoints proved
    # that the token sees the repository).
    if response.status == NOT_FOUND:
        enabled, paused = False, False
    elif response.status == 200 and is_object(response.body):
        body = mapping(response.body)
        enabled, paused = body.get("enabled") is True, body.get("paused") is True
    else:
        raise unusable("automated-security-fixes", response)
    if not expected.dependabot_security_updates:
        return []
    if not enabled:
        return ["Dependabot security updates are off"]
    return ["Dependabot security updates are paused"] if paused else []


def flag(fields: dict[str, Any], key: str) -> bool:
    value = fields[key]
    if not isinstance(value, bool):
        raise SettingsError(f"{key} must be true or false")
    return value


def branch_expectation(branch: str, value: object) -> BranchExpectation:
    fields = mapping(value)
    count = fields["required_approving_review_count"]
    checks = fields["required_status_checks"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise SettingsError(f"{branch}: required_approving_review_count is a count")
    if not items(checks):
        raise SettingsError(f"{branch}: required_status_checks lists the checks")
    return BranchExpectation(
        branch=branch,
        pull_request_required=flag(fields, "pull_request_required"),
        required_approving_review_count=count,
        required_status_checks=tuple(str(each) for each in items(checks)),
        force_pushes_blocked=flag(fields, "force_pushes_blocked"),
        deletions_blocked=flag(fields, "deletions_blocked"),
    )


def parse_expectations(text: str) -> Expectations:
    try:
        document = mapping(json.loads(text))
        branches = mapping(document["branches"])
        if not branches:
            raise SettingsError("no branch is expected to be protected")
        return Expectations(
            branches=tuple(
                branch_expectation(name, value) for name, value in branches.items()
            ),
            private_vulnerability_reporting=flag(
                document, "private_vulnerability_reporting"
            ),
            dependabot_security_updates=flag(document, "dependabot_security_updates"),
        )
    except SettingsError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise SettingsError(f"expectations: missing or invalid {error}") from error
