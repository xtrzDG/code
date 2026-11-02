"""
The GitHub environments a person or a branch rule stands in front of
(.github/repository-settings.json, "environments"): `production-release`,
whose required reviewers approve every promotion to production
(deploy-smoke.yml, job "promote"), and `backup-drill`, whose secrets open
production's backups (restore-drill.yml). GitHub creates an environment a
job names but nobody set up, without any protection, so the daily check
reads each one as well (.github/workflows/repo-settings.yml):

    environment-<name>.http      GET repos/{repo}/environments/{name}
    branch-policies-<name>.http  GET .../environments/{name}/deployment-branch-policies

An expectation names the reviewers (user logins or team slugs) of whom one
must approve, exactly those: anyone added could approve a release too; none
means the environment needs no approval. It names the branches that may
use it, exactly those: any other branch's workflow could read its secrets.
"""

from dataclasses import dataclass
from typing import Any

from scripts.repository_settings import (
    NOT_FOUND,
    Response,
    SettingsError,
    is_array,
    is_object,
    items,
    mapping,
    unusable,
)

# The fine-grained token's permission these endpoints need.
ENVIRONMENT_PERMISSION: str = "Actions: read"
REVIEWERS_RULE: str = "required_reviewers"
BRANCH_POLICY: str = "branch"


@dataclass(frozen=True)
class EnvironmentExpectation:
    name: str
    required_reviewers: frozenset[str]
    deployment_branches: frozenset[str]


def names(field: str, environment: str, value: object) -> frozenset[str]:
    if not is_array(value) or not all(
        isinstance(each, str) and each for each in items(value)
    ):
        raise SettingsError(f"{environment}: {field} lists names")
    return frozenset(str(each) for each in items(value))


def parse_environment_expectations(
    document: dict[str, Any],
) -> tuple[EnvironmentExpectation, ...]:
    """The "environments" object of the expectations (it may be empty)."""

    if "environments" not in document or not is_object(document["environments"]):
        raise SettingsError("expectations: environments must be an object")
    expectations: list[EnvironmentExpectation] = []
    for name, value in mapping(document["environments"]).items():
        fields = mapping(value)
        expectations.append(
            EnvironmentExpectation(
                name=name,
                required_reviewers=names(
                    "required_reviewers", name, fields.get("required_reviewers")
                ),
                deployment_branches=names(
                    "deployment_branches", name, fields.get("deployment_branches")
                ),
            )
        )
    return tuple(expectations)


def reviewer_name(entry: object) -> str:
    reviewer = mapping(mapping(entry).get("reviewer"))
    return str(reviewer.get("login") or reviewer.get("slug") or "")


def reviewers_of(body: dict[str, Any]) -> frozenset[str] | None:
    """The required reviewers, or None when the environment has no such rule."""

    rules = [
        mapping(rule)
        for rule in items(body.get("protection_rules"))
        if mapping(rule).get("type") == REVIEWERS_RULE
    ]
    if not rules:
        return None
    return frozenset(
        reviewer_name(entry) for rule in rules for entry in items(rule.get("reviewers"))
    )


def reviewer_problems(
    expected: EnvironmentExpectation, body: dict[str, Any]
) -> list[str]:
    if not expected.required_reviewers:
        return []
    actual = reviewers_of(body)
    name = expected.name
    if not actual:
        return [f"{name}: no required reviewers (its jobs run without approval)"]
    if actual != expected.required_reviewers:
        return [
            f"{name}: required reviewers are {', '.join(sorted(actual))},"
            f" expected {', '.join(sorted(expected.required_reviewers))}"
        ]
    return []


def allowed_refs(policies: Response, name: str) -> tuple[set[str], set[str]]:
    """The branch and the tag patterns of the custom deployment policy."""

    endpoint = f"environments/{name}/deployment-branch-policies"
    if policies.status != 200 or not is_object(policies.body):
        raise unusable(endpoint, policies, ENVIRONMENT_PERMISSION)
    branches: set[str] = set()
    tags: set[str] = set()
    for policy in items(mapping(policies.body).get("branch_policies")):
        fields = mapping(policy)
        kind = str(fields.get("type") or BRANCH_POLICY)
        (branches if kind == BRANCH_POLICY else tags).add(str(fields.get("name")))
    return branches, tags


def branch_problems(
    expected: EnvironmentExpectation, body: dict[str, Any], policies: Response
) -> list[str]:
    if not expected.deployment_branches:
        return []
    name = expected.name
    wanted = ", ".join(sorted(expected.deployment_branches))
    policy = mapping(body.get("deployment_branch_policy"))
    if not policy:
        return [f"{name}: every branch may use it, expected only {wanted}"]
    if policy.get("custom_branch_policies") is not True:
        return [f"{name}: every protected branch may use it, expected only {wanted}"]
    branches, tags = allowed_refs(policies, name)
    problems: list[str] = []
    if extra := sorted(branches - expected.deployment_branches):
        problems.append(f"{name}: other branches may use it: {', '.join(extra)}")
    if tags:
        problems.append(f"{name}: tags may use it: {', '.join(sorted(tags))}")
    if missing := sorted(expected.deployment_branches - branches):
        problems.append(f"{name}: {', '.join(missing)} may not use it")
    return problems


def environment_problems(
    expected: EnvironmentExpectation, environment: Response, policies: Response
) -> list[str]:
    name = expected.name
    if environment.status == NOT_FOUND:
        return [
            f"{name}: the environment does not exist"
            " (a job that names it would create it without protection)"
        ]
    if environment.status != 200 or not is_object(environment.body):
        raise unusable(f"environments/{name}", environment, ENVIRONMENT_PERMISSION)
    body = mapping(environment.body)
    return reviewer_problems(expected, body) + branch_problems(expected, body, policies)
