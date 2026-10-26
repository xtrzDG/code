"""
The vendored files read from the types of installed SDKs: the vendors
generate the SDKs from their own specifications (`sdk_types`).
"""

from scripts.vendor_specs.spec_model import (
    AddProperty,
    DocumentFormat,
    DropProperty,
    SchemaRoot,
    VendorSpec,
)

ANTHROPIC_SPEC = VendorSpec(
    file_name="anthropic_messages_api.json",
    provider="anthropic",
    title="Anthropic Messages API (beta surface of the Python SDK)",
    source_url="https://github.com/anthropics/anthropic-sdk-python",
    document_format=DocumentFormat.PYTHON_SDK,
    roots=(
        SchemaRoot(
            "request:messages.create",
            "python:anthropic.types.beta.message_create_params:"
            "MessageCreateParamsNonStreaming",
        ),
        SchemaRoot(
            "response:messages.create", "python:anthropic.types.beta:BetaMessage"
        ),
    ),
    patches=(
        DropProperty(
            definition="request:messages.create",
            property_name="betas",
            reason="the SDK sends the beta names in the anthropic-beta header",
        ),
    ),
)

ELEVENLABS_TYPES: str = "python:elevenlabs.types"
ELEVENLABS_AGENTS: str = "python-body:elevenlabs.conversational_ai.agents.raw_client"
ELEVENLABS_SPEC = VendorSpec(
    file_name="elevenlabs_agents_api.json",
    provider="elevenlabs",
    title="ElevenLabs Agents Platform (types of the Fern-generated Python SDK)",
    source_url="https://github.com/elevenlabs/elevenlabs-python",
    document_format=DocumentFormat.PYTHON_SDK,
    roots=(
        SchemaRoot(
            "request:agents.create", f"{ELEVENLABS_AGENTS}:RawAgentsClient.create"
        ),
        SchemaRoot(
            "request:agents.update", f"{ELEVENLABS_AGENTS}:RawAgentsClient.update"
        ),
        SchemaRoot(
            "response:agents.create",
            f"{ELEVENLABS_TYPES}.create_agent_response_model:CreateAgentResponseModel",
        ),
        SchemaRoot(
            "request:tools.create",
            f"{ELEVENLABS_TYPES}.tool_request_model:ToolRequestModel",
        ),
        SchemaRoot(
            "response:tools.create",
            f"{ELEVENLABS_TYPES}.tool_response_model:ToolResponseModel",
        ),
        # The answer of the conversation-initiation webhook.
        SchemaRoot(
            "ConversationInitiationClientData",
            f"{ELEVENLABS_TYPES}.conversation_initiation_client_data_request_input:"
            "ConversationInitiationClientDataRequestInput",
        ),
        # `data` of a post-call transcription webhook: the conversation as
        # GET /v1/convai/conversations/{id} answers it.
        SchemaRoot(
            "Conversation",
            f"{ELEVENLABS_TYPES}.get_conversation_response_model:"
            "GetConversationResponseModel",
        ),
        # The voice checks of autotests: a simulated call (an agent test),
        # its run against the agent with the version's configuration, and
        # the run as GET /v1/convai/test-invocations/{id} answers it.
        SchemaRoot(
            "request:agent_testing.create",
            "python:elevenlabs.conversational_ai.tests.types."
            "tests_create_request_body:TestsCreateRequestBody",
        ),
        SchemaRoot(
            "response:agent_testing.create",
            f"{ELEVENLABS_TYPES}.create_agent_test_response_model:"
            "CreateAgentTestResponseModel",
        ),
        SchemaRoot(
            "request:agents.run_tests", f"{ELEVENLABS_AGENTS}:RawAgentsClient.run_tests"
        ),
        SchemaRoot(
            "TestInvocation",
            f"{ELEVENLABS_TYPES}.get_test_suite_invocation_response_model:"
            "GetTestSuiteInvocationResponseModel",
        ),
    ),
    patches=(
        AddProperty(
            definition="ConversationInitiationClientData",
            property_name="type",
            schema={"const": "conversation_initiation_client_data"},
            reason=(
                "the webhook's answer names its type (ElevenLabs' example); the "
                "SDK type is the WebSocket message, which carries it elsewhere"
            ),
        ),
    ),
)
