"""
The workshop (tests/e2e/harness.py) with the model of LLM_PROVIDER=scripted
instead of the journey's script: what development, staging and the
cabinet's end-to-end suite run on.
"""

from typing import Any

from app.adapters.llm.offline_llm_adapter import OfflineLlmAdapter
from app.containers.app import AppContainer
from tests.e2e.harness import Workshop, start_workshop
from tests.e2e.workshop_container import replace_provider
from tests.setup.launch_steps import NewAssistant

type JsonObject = dict[str, Any]


def use_rehearsal_model(container: AppContainer) -> None:
    replace_provider(container.adapters.routing_llm_adapter, OfflineLlmAdapter())


def start_rehearsal_workshop() -> Workshop:
    return start_workshop(prepare=use_rehearsal_model)


def read_pending(
    workshop: Workshop, assistant: NewAssistant, language: str | None = None
) -> JsonObject:
    read = workshop.client.get(
        f"{assistant.base}/assistant/pending-changes",
        params={} if language is None else {"language": language},
        headers=assistant.headers,
    )
    assert read.status_code == 200, read.text
    return dict(read.json())


def add_item(
    workshop: Workshop, assistant: NewAssistant, body: JsonObject
) -> JsonObject:
    created = workshop.client.post(
        f"{assistant.base}/knowledge", json=body, headers=assistant.headers
    )
    assert created.status_code == 201, created.text
    return dict(created.json())


def edit_item(
    workshop: Workshop, assistant: NewAssistant, item_id: str, body: JsonObject
) -> JsonObject:
    edited = workshop.client.patch(
        f"{assistant.base}/knowledge/{item_id}", json=body, headers=assistant.headers
    )
    assert edited.status_code == 200, edited.text
    return dict(edited.json())
