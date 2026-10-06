"""
The vendored files generated from machine-readable vendor documents.

Providers without one (Messenger and Instagram, ElevenLabs, Flitt,
Cloudflare Turnstile, the National Bank of Georgia) have hand-written
files in tests/contracts/specs, marked `"kind": "documented"` with the
documentation pages they follow; the refresh leaves them alone.
"""

from scripts.vendor_specs.spec_model import (
    AddProperty,
    DocumentFormat,
    DropProperty,
    DropPropertyKeyword,
    DropRequired,
    RepairSectionReferences,
    SchemaRoot,
    VendorSpec,
)

TELEGRAM_SPEC = VendorSpec(
    file_name="telegram_bot_api.json",
    provider="telegram",
    title="Telegram Bot API",
    source_url="https://raw.githubusercontent.com/ark0f/tg-bot-api/gh-pages/openapi.json",
    document_format=DocumentFormat.OPENAPI,
    roots=(
        SchemaRoot("Update", "schema:Update"),
        SchemaRoot("Message", "schema:Message"),
        SchemaRoot("User", "schema:User"),
        SchemaRoot("File", "schema:File"),
        SchemaRoot("UserProfilePhotos", "schema:UserProfilePhotos"),
        SchemaRoot("request:sendMessage", "request:post /sendMessage"),
        SchemaRoot("request:sendChatAction", "request:post /sendChatAction"),
        SchemaRoot("request:setWebhook", "request:post /setWebhook"),
        SchemaRoot("request:deleteWebhook", "request:post /deleteWebhook"),
        SchemaRoot("request:getFile", "request:post /getFile"),
        SchemaRoot(
            "request:getUserProfilePhotos", "request:post /getUserProfilePhotos"
        ),
    ),
)

META_SPEC = VendorSpec(
    file_name="meta_whatsapp_cloud_api.json",
    provider="meta",
    title="WhatsApp Cloud API (Meta)",
    source_url=(
        "https://raw.githubusercontent.com/facebook/openapi/main/"
        "business-messaging-api_v23.0.yaml"
    ),
    document_format=DocumentFormat.OPENAPI,
    roots=(
        SchemaRoot("WebhookPayload", "schema:WebhookPayload"),
        SchemaRoot("MarkMessageRequestPayload", "schema:MarkMessageRequestPayload"),
        SchemaRoot("MessageResponsePayload", "schema:MessageResponsePayload"),
        SchemaRoot(
            "request:messages.send",
            "request:post /{Version}/{Phone-Number-ID}/messages",
        ),
        SchemaRoot("response:media.get", "response:get /{Version}/{Media-ID} 200"),
    ),
    patches=(
        RepairSectionReferences(
            first_schema="WebhookPayload",
            reason=(
                "the merged document renamed the webhook's message schemas "
                "(TextMessage_2, AudioMessage_1, ...) but kept references to "
                "the send API's schemas of the same name"
            ),
        ),
        DropRequired(
            definition="LanguageObject",
            property_name="policy",
            reason=(
                "templates are sent with the language code only; 'deterministic' "
                "is the only policy and the Cloud API applies it by default"
            ),
        ),
        DropPropertyKeyword(
            definition="TemplateComponent",
            property_name="index",
            keyword="pattern",
            reason=(
                "the published pattern '^[2-6, 11-14]$' is a one-character "
                "class; buttons are numbered from 0 (an authentication "
                "template's copy-code button is index 0)"
            ),
        ),
        AddProperty(
            definition="MarkMessageRequestPayload",
            property_name="typing_indicator",
            schema={
                "type": "object",
                "properties": {"type": {"type": "string", "enum": ["text"]}},
                "required": ["type"],
            },
            reason=(
                "typing indicators ride on the read receipt "
                "(developers.facebook.com/docs/whatsapp/cloud-api/typing-indicators)"
            ),
        ),
    ),
)

OPENAI_SPEC = VendorSpec(
    file_name="openai_responses_api.json",
    provider="openai",
    title="OpenAI Responses API",
    source_url=(
        "https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml"
    ),
    document_format=DocumentFormat.OPENAPI,
    roots=(
        SchemaRoot("Response", "schema:Response"),
        SchemaRoot("request:responses.create", "request:post /responses"),
    ),
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

GOOGLE_SPEC = VendorSpec(
    file_name="google_calendar_api.json",
    provider="google",
    title="Google Calendar API v3",
    source_url="https://www.googleapis.com/discovery/v1/apis/calendar/v3/rest",
    document_format=DocumentFormat.GOOGLE_DISCOVERY,
    roots=(
        SchemaRoot("Event", "schema:Event"),
        SchemaRoot("Events", "schema:Events"),
        SchemaRoot("FreeBusyRequest", "schema:FreeBusyRequest"),
        SchemaRoot("FreeBusyResponse", "schema:FreeBusyResponse"),
        SchemaRoot("CalendarList", "schema:CalendarList"),
        SchemaRoot("Calendar", "schema:Calendar"),
    ),
)

TWILIO_SPEC = VendorSpec(
    file_name="twilio_messaging_api.json",
    provider="twilio",
    title="Twilio Programmable Messaging (API 2010-04-01)",
    source_url=(
        "https://raw.githubusercontent.com/twilio/twilio-oai/main/spec/json/"
        "twilio_api_v2010.json"
    ),
    document_format=DocumentFormat.OPENAPI,
    roots=(
        SchemaRoot(
            "request:messages.create",
            "request:post /2010-04-01/Accounts/{AccountSid}/Messages.json",
        ),
        SchemaRoot(
            "response:messages.create",
            "response:post /2010-04-01/Accounts/{AccountSid}/Messages.json 201",
        ),
    ),
)

LANGFUSE_SPEC = VendorSpec(
    file_name="langfuse_public_api.json",
    provider="langfuse",
    title="Langfuse public API",
    source_url=(
        "https://raw.githubusercontent.com/langfuse/langfuse/main/web/public/"
        "generated/api/openapi.yml"
    ),
    document_format=DocumentFormat.OPENAPI,
    roots=(
        SchemaRoot("request:ingestion", "request:post /api/public/ingestion"),
        SchemaRoot("response:ingestion", "response:post /api/public/ingestion 207"),
        SchemaRoot("request:traces.delete", "request:delete /api/public/traces"),
        SchemaRoot("response:traces.list", "response:get /api/public/traces 200"),
    ),
)

CAL_COM_SPEC = VendorSpec(
    file_name="cal_com_api_v2.json",
    provider="cal_com",
    title="Cal.com API v2",
    source_url=(
        "https://raw.githubusercontent.com/calcom/cal.com/main/docs/"
        "api-reference/v2/openapi.json"
    ),
    document_format=DocumentFormat.OPENAPI,
    roots=(
        SchemaRoot("request:bookings.create", "request:post /v2/bookings"),
        SchemaRoot(
            "request:bookings.cancel", "request:post /v2/bookings/{bookingUid}/cancel"
        ),
        SchemaRoot("response:bookings.create", "response:post /v2/bookings 201"),
        SchemaRoot(
            "response:event-types.get", "response:get /v2/event-types/{eventTypeId} 200"
        ),
    ),
)

GENERATED_SPECS: tuple[VendorSpec, ...] = (
    TELEGRAM_SPEC,
    META_SPEC,
    OPENAI_SPEC,
    ANTHROPIC_SPEC,
    ELEVENLABS_SPEC,
    GOOGLE_SPEC,
    TWILIO_SPEC,
    LANGFUSE_SPEC,
    CAL_COM_SPEC,
)
