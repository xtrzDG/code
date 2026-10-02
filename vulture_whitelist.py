"""
Names vulture reports as unused although they are used (see [tool.vulture]
in pyproject.toml). Each section says why. Add a name here only with such a
reason; delete code that is really unused instead.

Run: uv run vulture
"""


class _Whitelist:
    def __getattr__(self, name: str) -> _Whitelist:
        return self


_ = _Whitelist()

# Test and operations seams: called by tests or by an operator in a shell,
# not by the running service.
_.from_turns  # app/adapters/llm/scripted_llm_adapter.py
_.idle_connection_count  # app/clients/postgres/postgres_connection_pool_client.py
_.open_connection_count  # app/clients/postgres/postgres_connection_pool_client.py
_.buffered_event_count  # app/facilitators/observability/langfuse_trace_facilitator.py
_.collection_name_for  # app/utilities/storage/document_collection_catalog.py
_.run_once  # app/gateways/worker/background_worker.py
# The current schema version of every collection, read by the document
# evolution policy (tests/architecture_policy/test_document_evolution.py).
_.CURRENT_SCHEMA_VERSION  # app/adapters/storage/document_upgrades.py

# Container providers kept for the template example and for tests that
# build the synchronous autotest run and bulk knowledge upserts.
_.example_config  # app/containers/config.py
_.run_autotests_orchestrator  # app/containers/orchestrators/assistant_orchestrators.py
_.upsert_knowledge_items_use_case  # app/containers/use_cases/knowledge_use_cases.py
_.example_use_case  # app/containers/use_cases/use_cases_container.py

# Template examples, kept on purpose
# (tests/architecture_policy/test_example_schemas_are_kept.py).
_.ExampleDocument  # app/schemas/domain/example_document.py
_.ExampleMicrosecondTimestampedDocument  # app/schemas/domain/example_document.py
_.ExampleMillisecondTimestampedDocument  # app/schemas/domain/example_document.py
_.ExampleNanosecondTimestampedDocument  # app/schemas/domain/example_document.py
_.ExamplePersistentDocument  # app/schemas/domain/example_document.py
_.ExampleArbitraryImmutableDTO  # app/schemas/dto/example_dto.py
_.ExampleArbitraryMutableDTO  # app/schemas/dto/example_dto.py
_.immutable_output  # app/schemas/dto/example_dto.py
_.mutable_input  # app/schemas/dto/example_dto.py
_.output_buffer  # app/schemas/dto/example_dto.py
_.publish_output  # app/schemas/dto/example_dto.py
_.ExampleConstrainedFloat  # app/schemas/typings/constrained_floats.py
_.ExampleConstrainedInt  # app/schemas/typings/constrained_integers.py
_.ExampleConstrainedString  # app/schemas/typings/constrained_strings.py

# Settings reserved for planned work: ZADARMA_* for the telephony
# integration (R5) and META_APP_ID for Meta app review (R15).
_.meta_app_id  # app/schemas/configurations/app_settings.py
_.zadarma_api_key  # app/schemas/configurations/app_settings.py
_.zadarma_api_secret  # app/schemas/configurations/app_settings.py

# Enum members that are valid on the wire (requests, stored documents,
# the cabinet) although no Python branch names them.
_.LOST  # app/schemas/constants/bookings.py
_.LEFT  # app/schemas/constants/channels.py
_.RIGHT  # app/schemas/constants/channels.py
_.BILLING  # app/schemas/constants/client_health.py
_.BOOKINGS  # app/schemas/constants/client_health.py
_.CONVERSATIONS  # app/schemas/constants/client_health.py
_.DASHBOARD  # app/schemas/constants/client_health.py
_.HANDOFFS  # app/schemas/constants/client_health.py
_.KNOWLEDGE  # app/schemas/constants/client_health.py
_.LEADS  # app/schemas/constants/client_health.py
_.SETTINGS  # app/schemas/constants/client_health.py
_.TEST  # app/schemas/constants/environment.py
_.UNSUPPORTED  # app/schemas/constants/localization.py
_.US  # app/schemas/constants/localization.py

# Stored document fields: written for people and exports, never read back
# by code.
_.rated_at  # app/registries/demo/demo_conversation_recorder.py
_.connected_by  # app/schemas/domain/calendar.py
_.linked_chat_id  # app/schemas/domain/manager_links.py
_.last_payment_reference  # app/schemas/domain/payments.py

# Response fields: serialized to JSON for the cabinet and the widget; the
# code fills them by keyword, so nothing in Python reads them.
_.attention_count  # app/schemas/dto/admin.py
_.audit_log_entry_id  # app/schemas/dto/admin.py
_.client_count  # app/schemas/dto/admin.py
_.critical_count  # app/schemas/dto/admin.py
_.failed_autotests  # app/schemas/dto/admin.py
_.generated_at  # app/schemas/dto/admin.py
_.has_auto_debit  # app/schemas/dto/admin.py
_.healthy_count  # app/schemas/dto/admin.py
_.last_test_score  # app/schemas/dto/admin.py
_.losing_money_count  # app/schemas/dto/admin.py
_.matching_count  # app/schemas/dto/admin.py
_.niches  # app/schemas/dto/admin.py
_.opened_at  # app/schemas/dto/admin.py
_.payments  # app/schemas/dto/admin.py
_.subscription_status  # app/schemas/dto/admin.py
_.version_status  # app/schemas/dto/assistants/assistant_views.py
_.dialog_usage_percent  # app/schemas/dto/billing_cabinet.py
_.issued_at  # app/schemas/dto/billing_cabinet.py
_.overage_cost  # app/schemas/dto/billing_cabinet.py
_.plan_name  # app/schemas/dto/billing_cabinet.py
_.voice_usage_percent  # app/schemas/dto/billing_cabinet.py
_.llm_cost_micro_usd  # app/schemas/dto/billing_ledger.py
_.planned_monthly_provider_cost  # app/schemas/dto/billing_ledger.py
_.connected_at  # app/schemas/dto/calendar.py
_.is_connected  # app/schemas/dto/calendar.py
_.assistant_phone_number  # app/schemas/dto/catalog/call_forwarding.py
_.assistant_phone_number_display  # app/schemas/dto/catalog/call_forwarding.py
_.currency_display_name  # app/schemas/dto/catalog/countries.py
_.annual_price  # app/schemas/dto/catalog/plan_quotes.py
_.local_annual_price  # app/schemas/dto/catalog/plan_quotes.py
_.local_overage_price_per_minute  # app/schemas/dto/catalog/plan_quotes.py
_.rate_date  # app/schemas/dto/catalog/plan_quotes.py
_.has_credential  # app/schemas/dto/channels/channel_settings.py
_.staff_reply_template  # app/schemas/dto/channels/channel_settings.py
_.received  # app/schemas/dto/channels/channel_webhooks.py
_.display_phone_number  # app/schemas/dto/channels/provider_profiles.py
_.deep_link  # app/schemas/dto/channels/staff_links.py
_.actor_ids  # app/schemas/dto/compliance.py
_.anonymized_bookings  # app/schemas/dto/compliance.py
_.anonymized_conversations  # app/schemas/dto/compliance.py
_.anonymized_handoffs  # app/schemas/dto/compliance.py
_.anonymized_leads  # app/schemas/dto/compliance.py
_.current_document_version  # app/schemas/dto/compliance.py
_.deleted_messages  # app/schemas/dto/compliance.py
_.document_url  # app/schemas/dto/compliance.py
_.entities  # app/schemas/dto/compliance.py
_.erased_calls  # app/schemas/dto/compliance.py
_.exported_at  # app/schemas/dto/compliance.py
_.is_current_version_accepted  # app/schemas/dto/compliance.py
_.scanned_businesses  # app/schemas/dto/compliance.py
_.conversation_count  # app/schemas/dto/contacts.py
_.first_seen_at  # app/schemas/dto/contacts.py
_.customer_message_count  # app/schemas/dto/conversation_feed/conversation_views.py
_.last_message_author  # app/schemas/dto/conversation_feed/conversation_views.py
_.last_message_text  # app/schemas/dto/conversation_feed/conversation_views.py
_.message_count  # app/schemas/dto/conversation_feed/conversation_views.py
_.window_closes_at  # app/schemas/dto/conversation_feed/conversation_views.py
_.assistant_version_number  # app/schemas/dto/conversations.py
_.completed_count  # app/schemas/dto/go_live.py
_.is_ready  # app/schemas/dto/go_live.py
_.scheduled_at  # app/schemas/dto/jobs.py
_.is_mobile  # app/schemas/dto/localization.py
_.local_number_provisioning  # app/schemas/dto/localization.py
_.national_format  # app/schemas/dto/localization.py
_.recording_consent_rule  # app/schemas/dto/localization.py
_.is_email_login_available  # app/schemas/dto/login_options.py
_.is_phone_login_available  # app/schemas/dto/login_options.py
_.activated_items  # app/schemas/dto/menu_import.py
_.discarded_item_ids  # app/schemas/dto/menu_import.py
_.printed_currency_code  # app/schemas/dto/menu_import.py
_.was_connected  # app/schemas/dto/operations/calendar_connection.py
_.after_hours_conversation_count  # app/schemas/dto/operations/dashboard.py
_.after_hours_share_percent  # app/schemas/dto/operations/dashboard.py
_.bookings_by_status  # app/schemas/dto/operations/dashboard.py
_.daily  # app/schemas/dto/operations/dashboard.py
_.handoff_count  # app/schemas/dto/operations/dashboard.py
_.handoffs_by_reason  # app/schemas/dto/operations/dashboard.py
_.handoffs_by_urgency  # app/schemas/dto/operations/dashboard.py
_.open_unanswered_question_count  # app/schemas/dto/operations/dashboard.py
_.package  # app/schemas/dto/operations/dashboard.py
_.resolved_count  # app/schemas/dto/operations/handoffs.py
_.status_counts  # app/schemas/dto/operations/leads.py
_.knowledge_item_id  # app/schemas/dto/operations/unanswered_questions.py
_.requires_reassembly  # app/schemas/dto/operations/unanswered_questions.py
_.is_ready_for_assembly  # app/schemas/dto/profiles/profile_gaps.py
_.unanswered_question  # app/schemas/dto/profiles/profile_gaps.py
_.unanswered_question_id  # app/schemas/dto/profiles/profile_gaps.py
_.saved_knowledge_items  # app/schemas/dto/profiles/profile_steps.py
_.is_complete  # app/schemas/dto/profiles/profile_wizard.py
_.expires_in_seconds  # app/schemas/dto/users.py
_.international_phone_number  # app/schemas/dto/users.py
