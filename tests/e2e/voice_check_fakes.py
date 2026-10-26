"""
ElevenLabs agent testing as the end-to-end workshop plays it: each run's
calls are answered by an agent that opens with the greeting the run's
configuration gives it, books for two people and is judged a pass.
"""

import itertools
import json
from dataclasses import dataclass, field
from typing import cast

import httpx

from tests.e2e.edge_fakes import answer_elevenlabs
from tests.e2e.harness_settings import JsonObject

CONFIRMATIONS: dict[str, str] = {
    "ka": "ჯავშანი მზადაა: ხვალ, 19:00, ორი ადამიანი.",
    "ru": "Бронь готова: завтра в 19:00, двое гостей.",
    "en": "Your table is booked for two tomorrow at 7 pm.",
}


@dataclass
class SimulatedCalls:
    """The agent-testing endpoints, remembering the tests of each run."""

    tests: dict[str, JsonObject] = field(default_factory=dict[str, JsonObject])
    runs: dict[str, tuple[str, str, list[str]]] = field(
        default_factory=dict[str, tuple[str, str, list[str]]]
    )
    numbers: itertools.count[int] = field(default_factory=itertools.count)

    def __call__(self, request: httpx.Request) -> JsonObject:
        path: str = request.url.path
        if request.method == "POST" and path == "/v1/convai/agent-testing/create":
            test_id: str = f"test_{next(self.numbers)}"
            self.tests[test_id] = cast(JsonObject, json.loads(request.content))
            return {"id": test_id}

        if request.method == "POST" and path.endswith("/run-tests"):
            return self._start(cast(JsonObject, json.loads(request.content)))

        if request.method == "GET" and path.startswith("/v1/convai/test-invocations/"):
            return self._finished(path.rsplit("/", 1)[-1])

        return answer_elevenlabs(request)

    def _start(self, body: JsonObject) -> JsonObject:
        override = cast(JsonObject, body["agent_config_override"])
        agent = cast(
            JsonObject, cast(JsonObject, override["conversation_config"])["agent"]
        )
        run_id: str = f"suite_{next(self.numbers)}"
        self.runs[run_id] = (
            str(agent["first_message"]),
            str(agent["language"]),
            [
                str(cast(JsonObject, test)["test_id"])
                for test in cast(list[object], body["tests"])
            ],
        )
        return {"id": run_id, "test_runs": []}

    def _finished(self, run_id: str) -> JsonObject:
        greeting, language, test_ids = self.runs[run_id]
        return {
            "id": run_id,
            "test_runs": [
                {
                    "test_run_id": f"{test_id}_run",
                    "test_invocation_id": run_id,
                    "agent_id": "agent_e2e",
                    "status": "passed",
                    "test_id": test_id,
                    "agent_responses": [
                        {"role": "agent", "message": greeting, "time_in_call_secs": 0},
                        {"role": "user", "message": "…", "time_in_call_secs": 3},
                        {
                            "role": "agent",
                            "message": CONFIRMATIONS.get(language, "Booked."),
                            "time_in_call_secs": 9,
                            "tool_calls": [
                                {
                                    "request_id": "req_1",
                                    "tool_name": "create_booking",
                                    "params_as_json": json.dumps(
                                        {"arguments": {"party_size": 2}}
                                    ),
                                    "tool_has_been_called": True,
                                }
                            ],
                        },
                    ],
                    "condition_result": {"result": "success"},
                }
                for test_id in test_ids
            ],
        }
