"""Knowledge tools of the assistant: search, prices and links."""

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolOutcome,
    GetPriceToolInput,
    SearchKnowledgeToolInput,
    SendLinkToolInput,
)
from app.schemas.dto.conversations import LlmToolCall
from app.schemas.dto.knowledge import (
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    PriceLookupQuery,
    PriceLookupResult,
    SendLinkQuery,
    SendLinkResult,
)
from app.use_cases.conversations.tools.tool_outcomes import success_outcome
from app.utilities.conversations.tool_payloads import (
    render_knowledge_search,
    render_link,
    render_price_lookup,
)


def run_search_knowledge(
    search_knowledge: UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult],
    call: LlmToolCall,
    context: AssistantToolContext,
) -> AssistantToolOutcome:
    tool_input = SearchKnowledgeToolInput.model_validate_json(call.input_json)
    result: KnowledgeSearchResult = search_knowledge.run(
        KnowledgeSearchRequest(
            business_id=context.business_id,
            query=tool_input.query,
            language=(
                tool_input.language
                if tool_input.language is not None
                else context.language
            ),
        )
    )
    return success_outcome(call, render_knowledge_search(result))


def run_get_price(
    get_price: UseCaseContract[PriceLookupQuery, PriceLookupResult],
    call: LlmToolCall,
    context: AssistantToolContext,
) -> AssistantToolOutcome:
    tool_input = GetPriceToolInput.model_validate_json(call.input_json)
    result: PriceLookupResult = get_price.run(
        PriceLookupQuery(
            business_id=context.business_id,
            item_name=tool_input.item_name,
            language=context.language,
        )
    )
    return success_outcome(call, render_price_lookup(result))


def run_send_link(
    send_link: UseCaseContract[SendLinkQuery, SendLinkResult],
    call: LlmToolCall,
    context: AssistantToolContext,
) -> AssistantToolOutcome:
    tool_input = SendLinkToolInput.model_validate_json(call.input_json)
    result: SendLinkResult = send_link.run(
        SendLinkQuery(business_id=context.business_id, kind=tool_input.kind)
    )
    return success_outcome(call, render_link(result))
