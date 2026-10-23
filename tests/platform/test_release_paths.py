"""
Every way a commit reaches main carries the same guards, and branch
protection cannot be passed by a skipped job:

- a run of CI on main that automerge.yml (or a person) dispatched publishes
  signed images like a push does, so deploy smoke can verify the commit;
- automerge.yml starts every workflow a push to main starts, since its
  merge pushes no event (ZAP, CodeQL and Lighthouse included);
- the required checks of ci.yml cannot be skipped into passing: a required
  job that needs other jobs runs always and fails unless they succeeded;
- automerge waits for every workflow that owns a required check.
"""

import ast
import json
import re
from pathlib import Path
from typing import Any, cast

import yaml

from tests.platform.environment_sources import ROOT

WORKFLOWS: Path = ROOT / ".github" / "workflows"
SETTINGS: Path = ROOT / ".github" / "repository-settings.json"
MAIN: str = "refs/heads/main"


def workflow(name: str) -> dict[Any, Any]:
    return cast(
        dict[Any, Any],
        yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8")),
    )


def triggers(document: dict[Any, Any]) -> dict[str, Any]:
    # YAML 1.1 reads the key `on` as True.
    return cast(dict[str, Any], document.get("on", document.get(True)))


def jobs(document: dict[Any, Any]) -> dict[str, dict[str, Any]]:
    return cast(dict[str, dict[str, Any]], document["jobs"])


def needs(job: dict[str, Any]) -> list[str]:
    value = job.get("needs", [])
    return [value] if isinstance(value, str) else list(cast(list[str], value))


def evaluate(node: ast.expr) -> object:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BoolOp):
        values = [evaluate(each) for each in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        left, right = evaluate(node.left), evaluate(node.comparators[0])
        if isinstance(node.ops[0], ast.Eq):
            return left == right
        if isinstance(node.ops[0], ast.NotEq):
            return left != right
    raise AssertionError(f"unsupported condition: {ast.dump(node)}")


def runs(condition: str, event: str, ref: str) -> bool:
    """A GitHub `if:` of event names, refs, `==`, `&&`, `||` for one run."""

    expression = condition.removeprefix("${{").removesuffix("}}").strip()
    expression = expression.replace("github.event_name", repr(event))
    expression = expression.replace("github.ref", repr(ref))
    expression = expression.replace("&&", " and ").replace("||", " or ")
    return bool(evaluate(ast.parse(expression, mode="eval").body))


def publishing_conditions() -> list[str]:
    ci = jobs(workflow("ci.yml"))
    saving = [
        str(step["if"])
        for step in ci["images"]["steps"]
        if "scanned" in str(step.get("name", "")) and "if" in step
    ]
    assert len(saving) == 2
    return [str(ci["publish-images"]["if"]), *saving]


def test_a_dispatched_run_of_main_publishes_signed_images_like_a_push() -> None:
    for condition in publishing_conditions():
        assert runs(condition, "push", MAIN), condition
        assert runs(condition, "workflow_dispatch", MAIN), condition
        assert not runs(condition, "pull_request", "refs/pull/7/merge"), condition
        assert not runs(condition, "workflow_dispatch", "refs/heads/other"), condition


def automerge_script() -> str:
    merge = jobs(workflow("automerge.yml"))["merge"]
    return "\n".join(str(step.get("run", "")) for step in merge["steps"])


def push_workflows_of_main() -> set[str]:
    """Workflows every push to main starts (no path filter)."""

    names: set[str] = set()
    for path in sorted(WORKFLOWS.glob("*.yml")):
        push = triggers(workflow(path.name)).get("push")
        if isinstance(push, dict):
            push_filter = cast(dict[str, Any], push)
            if "main" in push_filter.get("branches", []) and not {
                "paths",
                "paths-ignore",
            } & set(push_filter):
                names.add(path.name)
    return names


def test_automerge_starts_every_workflow_a_push_to_main_starts() -> None:
    run = automerge_script()
    loop = re.search(r"for name in ([\w. -]+); do", run)
    assert loop is not None
    dispatched = set(loop.group(1).split())
    expected = push_workflows_of_main()

    assert {"ci.yml", "zap.yml"} <= expected
    assert dispatched == expected
    assert 'gh workflow run "$name" --ref "$base"' in run
    for name in dispatched:
        assert "workflow_dispatch" in triggers(workflow(name)), name


def required_checks() -> set[str]:
    expected = json.loads(SETTINGS.read_text(encoding="utf-8"))
    return set(expected["branches"]["main"]["required_status_checks"])


def is_required(job_id: str, job: dict[str, Any]) -> bool:
    """Whether a job's check name (any matrix value) is a required check."""

    name = str(job.get("name", job_id))
    pattern = ".+".join(re.escape(part) for part in re.split(r"\$\{\{.*?\}\}", name))
    return any(re.fullmatch(pattern, check) for check in required_checks())


def test_no_required_check_of_ci_passes_by_being_skipped() -> None:
    ci = jobs(workflow("ci.yml"))
    required = {job_id for job_id, job in ci.items() if is_required(job_id, job)}

    for job_id in sorted(required):
        if needs(ci[job_id]):
            # Skipped when a needed job failed, and skipped counts as passed.
            assert ci[job_id].get("if") == "${{ always() }}", job_id
    assert required == {"ci-passed"}


def test_the_ci_verdict_needs_every_gate_and_succeeds_only_when_they_did() -> None:
    ci = jobs(workflow("ci.yml"))
    verdict = ci["ci-passed"]
    gates = set(ci) - {"ci-passed", "durations", "publish-images"}
    script = "\n".join(str(step.get("run", "")) for step in verdict["steps"])

    assert set(needs(verdict)) == gates
    assert verdict["steps"][0]["env"]["NEEDS"] == "${{ toJSON(needs) }}"
    assert 'all(.[]; .result == "success")' in script
    assert "exit 1" in script


def test_automerge_waits_for_every_workflow_of_a_required_check() -> None:
    owners: set[str] = set()
    for path in sorted(WORKFLOWS.glob("*.yml")):
        document = workflow(path.name)
        if any(is_required(job_id, job) for job_id, job in jobs(document).items()):
            owners.add(str(document["name"]))
    run = automerge_script()

    assert owners == {"CI", "CodeQL", "API contract"}
    assert set(triggers(workflow("automerge.yml"))["workflow_run"]["workflows"]) == (
        owners
    )
    # A merge while one of them still runs would be refused: wait for it.
    assert run.index('gh pr checks "$pr" --required') < run.index("gh pr merge")
    assert 'select(.bucket == "pending")' in run
