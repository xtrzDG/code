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
_.run_queued_jobs  # app/gateways/worker/background_worker.py
_.worker_id  # app/gateways/worker/heartbeat_recorder.py
_.wait_until_listening  # app/adapters/events/postgres_live_event_listener.py
_.open_stream_count  # app/facilitators/events/live_event_stream_facilitator.py
# The current schema version of every collection, read by the document
# evolution policy (tests/architecture_policy/test_document_evolution.py).
_.CURRENT_SCHEMA_VERSION  # app/adapters/storage/document_upgrades.py
# A bumped `schema_version` default is read by the storage codec through the
# model's fields, never by name (app/adapters/storage/document_upgrades.py).
_.schema_version  # app/schemas/domain/assistants.py, conversations.py

# Container providers kept for the template example and for tests that
# build the synchronous autotest run and bulk knowledge upserts.
_.example_config  # app/containers/config.py
_.run_autotests_orchestrator  # app/containers/orchestrators/assistant_orchestrators.py
_.upsert_knowledge_items_use_case  # app/containers/use_cases/knowledge_use_cases.py
_.example_use_case  # app/containers/use_cases/use_cases_container.py

# Set for a library that reads it: AnyIO's thread limiter (app/main.py).
_.total_tokens  # app/main.py

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
# The booking rule rows a pending change names, found by their fact key.
_.BOOKING_UNIT  # app/schemas/constants/setup.py
_.BOOKING_LENGTH  # app/schemas/constants/setup.py
_.BOOKING_MAX_PARTY_SIZE  # app/schemas/constants/setup.py
_.BOOKING_MIN_NOTICE  # app/schemas/constants/setup.py
_.BOOKING_DEPOSIT  # app/schemas/constants/setup.py
_.BOOKING_CANCELLATION  # app/schemas/constants/setup.py
# What the website widget's error beacon sends (widget.js, errors.js).
_.SCRIPT_ERROR  # app/schemas/constants/observability.py
_.CONFIG_FAILED  # app/schemas/constants/observability.py
_.BOOT  # app/schemas/constants/observability.py
_.MOUNT  # app/schemas/constants/observability.py
_.SEND  # app/schemas/constants/observability.py
_.POLL  # app/schemas/constants/observability.py
_.RENDER  # app/schemas/constants/observability.py

# Stored document fields: written for people and exports, never read back
# by code.
_.rated_at  # app/registries/demo/demo_conversation_recorder.py
_.connected_by  # app/schemas/domain/calendar.py
_.linked_chat_id  # app/schemas/domain/manager_links.py
_.last_payment_reference  # app/schemas/domain/payments.py
_.processed_at  # app/schemas/domain/inbound_events.py
_.delivered_at  # app/schemas/domain/outbound_messages.py
_.source_message_id  # app/schemas/domain/outbound_messages.py

# Response fields: serialized to JSON for the cabinet and the widget; the
# code fills them by keyword, so nothing in Python reads them.
_.latency_ms  # app/schemas/dto/health.py (GET /readyz)
_.heartbeat_age_seconds  # app/schemas/dto/health.py (GET /readyz)
_.error_name  # app/schemas/dto/widget_errors.py (read as a tag by model_dump)
_.attention_count  # app/schemas/dto/admin.py
_.failed_tests  # app/schemas/dto/admin.py
_.low_criteria  # app/schemas/dto/admin.py
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
_.item_kind  # app/schemas/dto/setup/pending_changes.py
_.live_version_number  # app/schemas/dto/setup/pending_changes.py
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
_.answered  # app/schemas/dto/channels/channel_webhooks.py
_.failed  # app/schemas/dto/channels/channel_webhooks.py
_.received  # app/schemas/dto/channels/channel_webhooks.py
_.silenced  # app/schemas/dto/channels/channel_webhooks.py
_.display_phone_number  # app/schemas/dto/channels/provider_profiles.py
_.deep_link  # app/schemas/dto/channels/staff_links.py
_.actor_ids  # app/schemas/dto/compliance.py
_.anonymized_bookings  # app/schemas/dto/compliance.py
_.anonymized_conversations  # app/schemas/dto/compliance.py
_.anonymized_handoffs  # app/schemas/dto/compliance.py
_.anonymized_leads  # app/schemas/dto/compliance.py
_.current_document_version  # app/schemas/dto/compliance.py
_.deleted_messages  # app/schemas/dto/compliance.py
_.deleted_notes  # app/schemas/dto/compliance.py
_.document_url  # app/schemas/dto/compliance.py
_.entities  # app/schemas/dto/compliance.py
_.erased_calls  # app/schemas/dto/compliance.py
_.exported_at  # app/schemas/dto/compliance.py
_.is_current_version_accepted  # app/schemas/dto/compliance.py
_.scanned_businesses  # app/schemas/dto/compliance.py
_.conversation_count  # app/schemas/dto/contacts.py
_.first_seen_at  # app/schemas/dto/contacts.py
_.customer_message_count  # app/schemas/dto/conversation_feed/conversation_views.py
_.earlier_messages_cursor  # app/schemas/dto/conversation_feed/conversation_views.py
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
_.open_count  # app/schemas/dto/operations/handoffs.py
_.resolved_count  # app/schemas/dto/operations/handoffs.py
_.channel_errors  # app/schemas/dto/inbox/inbox_attention.py
_.channel_error_count  # app/schemas/dto/inbox/inbox_attention.py (deprecated name)
_.new_lead_count  # app/schemas/dto/inbox/inbox_attention.py (deprecated name)
_.open_handoff_count  # app/schemas/dto/inbox/inbox_attention.py (deprecated name)
_.unconfirmed_bookings  # app/schemas/dto/inbox/inbox_attention.py
_.unconfirmed_booking_count  # app/schemas/dto/inbox/inbox_attention.py (deprecated)
# A channel's link state, read by the cabinet's Channels card.
_.link_state  # app/schemas/dto/channels/channel_settings.py
# Dated exchange rates: the stored day number is a lookup column (the newest
# rate of a pair, migration 1071); staleness is shown by the cabinet.
_.rate_day  # app/schemas/domain/exchange_rates.py
_.is_stale  # app/schemas/dto/catalog/plan_quotes.py
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

# The load-test manifest (`workshop seed-load`): written as JSON for the k6
# scenarios (perf/k6), which read these fields; no Python code does.
_.latest_message_id  # app/schemas/dto/load_data.py
_.telegram_channel_id  # app/schemas/dto/load_data.py
_.telegram_webhook_secret  # app/schemas/dto/load_data.py
_.provider_ready  # app/schemas/dto/notifications/notification_settings.py
_.booking_date  # app/schemas/dto/notifications/staff_links.py
_.does_trial_start_at_go_live  # app/schemas/dto/billing_cabinet.py
_.checks_done  # app/schemas/dto/setup/apply_changes.py
_.checks_total  # app/schemas/dto/setup/apply_changes.py
_.starter_answers  # app/schemas/dto/setup/assistant_creation.py
_.is_answering  # app/schemas/dto/setup/setup_progress.py
_.milestones  # app/schemas/dto/setup/setup_progress.py
_.minutes_left  # app/schemas/dto/setup/setup_progress.py
_.next_action  # app/schemas/dto/setup/setup_progress.py
_.applied_sections  # app/schemas/dto/setup/starter_answers.py
_.kept_sections  # app/schemas/dto/setup/starter_answers.py
_.offer_examples  # app/schemas/dto/setup/starter_answers.py

# Settings → Calls and the telephony webhook: response fields the cabinet
# (and Zadarma's retries log) read; no Python code does.
_.is_whatsapp_connected  # app/schemas/dto/calls/call_settings.py
_.template_previews  # app/schemas/dto/calls/call_settings.py
_.notified_count  # app/schemas/dto/calls/call_summaries.py
_.text_back_status  # app/schemas/dto/calls/missed_calls.py

# Settings → Reviews: response fields the cabinet reads; no Python code does.
_.is_link_tracked  # app/schemas/dto/feedback/review_settings.py
_.period_days  # app/schemas/dto/feedback/review_stats.py
_.asked_count  # app/schemas/dto/feedback/review_stats.py
_.answered_count  # app/schemas/dto/feedback/review_stats.py
_.review_opened_count  # app/schemas/dto/feedback/review_stats.py
_.skipped_count  # app/schemas/dto/feedback/review_stats.py
_.failed_count  # app/schemas/dto/feedback/review_stats.py

# The team inbox's views: fields the cabinet reads (R6 inbox UI).
_.is_assigned_automatically  # app/schemas/dto/inbox/assignment.py, inbox_views.py
_.assignment  # app/schemas/dto/inbox/assignment.py
_.author_name  # app/schemas/dto/inbox/conversation_notes.py
_.awaiting_count  # app/schemas/dto/inbox/inbox_views.py
_.variables  # app/schemas/dto/inbox/quick_replies.py
_.missing_variables  # app/schemas/dto/inbox/quick_replies.py

# The platform admin's key ring view (GET /v1/admin/security/encryption-keys):
# response fields read by the admin and the runbook, never by Python code.
_.latest_rotation  # app/schemas/dto/key_rotation.py
_.requested_at  # app/schemas/dto/key_rotation.py

# Read by the website chat widget (widget.js) and the hosted chat page
# (web/src/app/c), never by Python code.
_.starter_questions  # app/schemas/dto/channels/widget.py
_.contact_links  # app/schemas/dto/channels/widget.py
_.widget_script_url  # app/schemas/dto/sharing.py

_.source_page_url  # app/schemas/dto/menu_import.py

# Hooks a library calls: httpcore asks a network backend for Unix sockets,
# HTMLParser calls handle_startendtag for "<br/>"-style tags.
_.connect_unix_socket  # app/clients/http/vetting_network_backend.py
_.handle_startendtag  # app/utilities/knowledge/website/html_to_text.py
# The value of a business, its digests and reports: totals and settings the
# cabinet shows (dashboard hero, Reports page, digest choices).
_.assistant_reply_count  # app/schemas/dto/value/value_model.py, domain/value_reports.py
_.call_count  # app/schemas/dto/value/value_model.py, domain/value_reports.py
_.typical_check_minor  # app/schemas/dto/value/value_model.py, value_views.py
_.is_email_ready  # app/schemas/dto/value/value_views.py
_.device_count  # app/schemas/dto/value/value_views.py
_.upcoming_booking_count  # app/schemas/dto/value/value_views.py
