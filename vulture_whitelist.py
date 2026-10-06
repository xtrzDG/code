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
_.PRINTED_QR  # app/schemas/constants/setup.py
_.DOWNLOADED_QR  # app/schemas/constants/setup.py
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
_.changed_by  # app/schemas/domain/bookings.py (BookingStatusChange)
_.resolved_by  # app/schemas/domain/handoffs.py
_.identity_digest  # app/schemas/domain/suppression.py (the id is derived from it)

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
_.guard  # app/schemas/dto/conversation_feed/conversation_views.py
_.item_kind  # app/schemas/dto/setup/pending_changes.py
_.live_version_number  # app/schemas/dto/setup/pending_changes.py
_.dialog_usage_percent  # app/schemas/dto/billing_cabinet.py
_.issued_at  # app/schemas/dto/billing_cabinet.py
_.is_receipt_available  # app/schemas/dto/billing_cabinet.py
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
_.anonymized_feedback_requests  # app/schemas/dto/compliance.py
_.anonymized_handoffs  # app/schemas/dto/compliance.py
_.anonymized_leads  # app/schemas/dto/compliance.py
_.current_document_version  # app/schemas/dto/compliance.py
_.deleted_messages  # app/schemas/dto/compliance.py
_.deleted_notes  # app/schemas/dto/compliance.py
_.document_url  # app/schemas/dto/compliance.py
_.entities  # app/schemas/dto/compliance.py
_.erased_calls  # app/schemas/dto/compliance.py
_.erased_missed_calls  # app/schemas/dto/compliance.py
_.exported_at  # app/schemas/dto/compliance.py
_.is_current_version_accepted  # app/schemas/dto/compliance.py
_.is_on_suppression_list  # app/schemas/dto/compliance.py
_.opt_out  # app/schemas/dto/compliance.py
_.redacted_inbound_events  # app/schemas/dto/compliance.py
_.redacted_outbound_messages  # app/schemas/dto/compliance.py
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
_.booked_value  # app/schemas/dto/operations/dashboard.py
_.after_hours_booked_value  # app/schemas/dto/operations/dashboard.py
_.valued_booking_count  # app/schemas/dto/value/value_model.py, domain/value_reports.py
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
# The folded name of a contact: stored for its lookup column, which the
# trigger of migration 1122 fills and the exact-name search queries.
_.display_name_folded  # app/schemas/domain/contacts.py
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
_.steps_after_launch  # app/schemas/dto/setup/setup_guide.py
_.is_phone_check_listening  # app/schemas/dto/setup/setup_guide.py
_.phone_check_until  # app/schemas/dto/setup/setup_guide.py
_.onboarding_requested_at  # app/schemas/dto/billing_cabinet.py
_.onboarding_request  # app/schemas/dto/admin.py
_.setup_options  # app/schemas/dto/catalog/plan_quotes.py
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

# Growth analytics (GET /v1/admin/metrics, POST /v1/telemetry/events): the
# values the cabinet sends (tunnel screens, device classes), the facts kept
# on product events and sign-up attribution for the founder's own queries,
# and the response fields the admin Metrics page reads.
_.PLACE  # app/schemas/constants/analytics.py (TunnelStepKey)
_.PEOPLE  # app/schemas/constants/analytics.py (TunnelStepKey)
_.TABLET  # app/schemas/constants/analytics.py (DeviceClass)
_.DESKTOP  # app/schemas/constants/analytics.py (DeviceClass)
_.attention_codes  # app/schemas/domain/product_events.py
_.utm_medium  # app/schemas/domain/signup_attribution.py
_.utm_campaign  # app/schemas/domain/signup_attribution.py
_.utm_term  # app/schemas/domain/signup_attribution.py
_.utm_content  # app/schemas/domain/signup_attribution.py
_.growth  # app/schemas/dto/analytics/admin_metrics_view.py
_.web_vitals  # app/schemas/dto/analytics/admin_metrics_view.py, telemetry.py
_.share_of_sign_ups  # app/schemas/dto/analytics/growth_views.py
_.share_of_previous  # app/schemas/dto/analytics/growth_views.py
_.stopped_here  # app/schemas/dto/analytics/growth_views.py
_.funnel  # app/schemas/dto/analytics/growth_views.py
_.median_time_to_live_seconds  # app/schemas/dto/analytics/growth_views.py
_.trials  # app/schemas/dto/analytics/growth_views.py
_.net_change  # app/schemas/dto/analytics/revenue_views.py
_.paying_accounts  # app/schemas/dto/analytics/revenue_views.py
_.arpa  # app/schemas/dto/analytics/revenue_views.py
_.unconverted_currencies  # app/schemas/dto/analytics/revenue_views.py
_.gross_margin_percent  # app/schemas/dto/analytics/revenue_views.py
_.accounts_without_rate  # app/schemas/dto/analytics/revenue_views.py
_.mrr  # app/schemas/dto/analytics/revenue_views.py
_.tunnel_steps  # app/schemas/dto/analytics/telemetry.py

# Customer media (voice notes, photos, places): fields the cabinet's
# transcript and inbox preview read.
_.last_message_attachment  # app/schemas/dto/inbox/inbox_views.py, conversation_views.py
_.map_url  # app/schemas/dto/media.py (MessageAttachmentView)
_.is_media_deleted  # app/schemas/dto/media.py (MessageAttachmentView)

# Two-factor sign-in (Account → Security, the sign-in's second step, the
# step-up dialog, Settings → Team): response fields the cabinet reads.
_.provisioning_uri  # app/schemas/dto/mfa.py (TotpEnrollmentView)
_.totp_status  # app/schemas/dto/mfa.py (AccountSecurityView)
_.totp_confirmed_at  # app/schemas/dto/mfa.py (AccountSecurityView)
_.totp_last_used_at  # app/schemas/dto/mfa.py (AccountSecurityView)
_.recovery_codes_left  # app/schemas/dto/mfa.py (AccountSecurityView)
_.is_mfa_required  # app/schemas/dto/mfa.py (AccountSecurityView)
_.step_up_valid_until  # app/schemas/dto/mfa.py (SessionAssuranceView)
_.members_without_two_factor  # app/schemas/dto/mfa.py (BusinessSecurityView)
_.viewer_auth_level  # app/schemas/dto/mfa.py (BusinessSecurityView)

# Pydantic configuration, read by pydantic's metaclass (the evaluation
# dataset models refuse unknown keys).
_.model_config  # scripts/eval_harness/dataset_models.py

# Reply speed: a reply's measured wait is read by the database (the latency
# buckets of migration 1090), the medians by the admin's client page.
_.reply_latency_ms  # app/schemas/domain/conversations.py (MessageDocument)
_.p50_ms  # app/schemas/dto/reply_speed.py (ClientReplySpeed, ChannelReplySpeed)

# The platform's own operations (GET /v1/admin/system, /v1/admin/incidents,
# docs/operations): response fields the admin pages read, the incident
# kinds an admin picks, and when an alert was last checked (stored for the
# postmortem); no Python code reads them.
_.OUTAGE  # app/schemas/constants/incidents.py
_.DEGRADATION  # app/schemas/constants/incidents.py
_.checked_at  # app/schemas/domain/platform_alerts.py, app/schemas/dto/admin_system.py
_.failing_jobs  # app/schemas/dto/admin_system.py (WorkerPulseView)
_.scheduled  # app/schemas/dto/admin_system.py (LaneView)
_.dead  # app/schemas/dto/admin_system.py (LaneView)
_.oldest_wait_seconds  # app/schemas/dto/admin_system.py (LaneView)
_.row_estimate  # app/schemas/dto/admin_system.py (TableSizeView)
_.dead_jobs  # app/schemas/dto/admin_system.py (AdminSystemView)
_.channels_in_error  # app/schemas/dto/admin_system.py (AdminSystemView)
_.channels_in_error_count  # app/schemas/dto/admin_system.py (AdminSystemView)
_.expiring_credentials  # app/schemas/dto/admin_system.py (AdminSystemView)
_.database_bytes  # app/schemas/dto/admin_system.py (AdminSystemView)
_.last_restore_drill  # app/schemas/dto/admin_system.py (AdminSystemView)
_.alerts  # app/schemas/dto/admin_system.py (AdminSystemView)
_.notice_languages  # app/schemas/dto/incidents.py (IncidentView)

# Where customers came from and the owner's summary channels: response
# fields the cabinet's Reports page reads; no Python code reads them.
_.estimated_value_minor  # app/schemas/dto/value/customer_sources.py (CustomerSourceRow)
_.suggested_whatsapp_number  # app/schemas/dto/value/value_views.py

# Device sessions, the admin team and support access (1103): response
# fields the cabinet reads (Account → Security, Admin → Team, the support
# banner), and what a grant stores for the audit trail (who granted it,
# from where, why it ended); no Python code reads them.
_.revoked_count  # app/schemas/dto/sessions.py (RevokedSessionsView)
_.added_by_name  # app/schemas/dto/platform_admins.py (PlatformAdminView)
_.is_you  # app/schemas/dto/platform_admins.py (PlatformAdminView)
_.is_yours  # app/schemas/dto/support_access.py (SupportSessionView)
_.write_access  # app/schemas/dto/support_access.py (SupportAccessView)
_.is_support_viewer  # app/schemas/dto/support_access.py (SupportAccessView)
_.viewer_can_write  # app/schemas/dto/support_access.py (SupportAccessView)
_.support_access_grant_id  # app/schemas/dto/admin.py (ClientCabinetAccess)
_.can_write  # app/schemas/dto/admin.py (ClientCabinetAccess)
_.platform_admin_role  # app/schemas/dto/users.py (CurrentUserView)
_.platform_admin_permissions  # app/schemas/dto/users.py (CurrentUserView)
_.granted_by  # app/schemas/domain/support_access_grants.py
_.opened_from_ip  # app/schemas/domain/support_access_grants.py
_.end_reason  # app/schemas/domain/support_access_grants.py

# Guided channels (R9-CONNECT): response fields the cabinet reads (the
# Channels page's per-language staff templates and the checked bot's photo).
_.staff_reply_templates  # app/schemas/dto/channels/channel_settings.py
_.avatar_data_url  # app/schemas/dto/channels/telegram_token_checks.py

# Help, support contacts and the status page (1111): help topics named by the
# articles' front matter (docs/help), and response fields the cabinet's help
# drawer, account panel and the public /status page read; no Python code does.
_.GETTING_STARTED  # app/schemas/constants/help.py
_.DAILY_WORK  # app/schemas/constants/help.py
_.ACCOUNT  # app/schemas/constants/help.py
_.whatsapp_url  # app/schemas/dto/help.py (SupportContactsView)
_.telegram_url  # app/schemas/dto/help.py (SupportContactsView)
_.email_url  # app/schemas/dto/help.py (SupportContactsView)
_.is_scheduled  # app/schemas/dto/platform_status.py (AnnouncementView)
_.past_announcements  # app/schemas/dto/platform_status.py (PlatformStatusView)

# Teaching from conversations (1112): where a saved check came from and the
# reasons of a bad rating arrive from the cabinet; the correction draft,
# the last result of a check and the counts of "Answers worth improving"
# are response fields only the cabinet reads.
_.CORRECTION  # app/schemas/constants/assistants.py (AutotestCaseSource)
_.SHOULD_HAND_OFF  # app/schemas/constants/conversations.py (ConversationRatingReason)
_.last_result  # app/schemas/dto/assistants/autotest_cases.py (AutotestCaseView)
_.suggested_scope  # app/schemas/dto/conversation_feed/answer_corrections.py
_.current_fact  # app/schemas/dto/conversation_feed/answer_corrections.py
_.is_corrected  # app/schemas/dto/conversation_feed/answer_corrections.py
_.bad_rating_count  # app/schemas/dto/conversation_feed/answers_to_improve.py

# Trustworthy checks and production quality (R11): the comparison of a run
# with the live version's run, a client's quality trend and a
# conversation's score are response fields only the cabinet reads.
_.baseline_outcome  # app/schemas/dto/assistants/autotest_comparison_views.py
_.baseline_average_score  # app/schemas/dto/assistants/autotest_comparison_views.py
_.baseline_run_id  # app/schemas/dto/assistants/autotest_comparison_views.py
_.baseline_version_id  # app/schemas/dto/assistants/autotest_comparison_views.py
_.baseline_version_number  # app/schemas/dto/assistants/autotest_comparison_views.py
_.average_score_change  # app/schemas/dto/assistants/autotest_comparison_views.py
_.shared_scenario_count  # app/schemas/dto/assistants/autotest_comparison_views.py
_.new_failures  # app/schemas/dto/assistants/autotest_comparison_views.py
_.fixed  # app/schemas/dto/assistants/autotest_comparison_views.py
_.score_changes  # app/schemas/dto/assistants/autotest_comparison_views.py
_.criterion_changes  # app/schemas/dto/assistants/autotest_comparison_views.py
_.last_week_average  # app/schemas/dto/quality.py (ClientQualityView)
_.previous_week_average  # app/schemas/dto/quality.py (ClientQualityView)
_.is_dropping  # app/schemas/dto/quality.py (ClientQualityView)

# Retention (1123): what the latest purge removed, when it ran and the jobs
# queued at the sub-processors after an erasure are response fields only
# the cabinet reads.
_.deleted_media  # app/schemas/domain/retention_purges.py (RetentionPurgeCounts)
_.deleted_missed_calls  # app/schemas/domain/retention_purges.py
_.queued_processor_erasures  # app/schemas/dto/compliance.py (ContactErasureResult)
_.ran_at  # app/schemas/dto/retention.py (RetentionPurgeView)
_.last_purge  # app/schemas/dto/retention.py (PrivacySettingsView)

# Legal texts and the sub-processor list (1124): the cookie statement is
# chosen by the request path (/v1/legal/cookies); the time of the terms
# acceptance is stored for the record; the `app/clients` packages of an
# entry are read by tests/legal (every client package has an entry); the
# rest are response fields the public pages and the sign-in page read.
_.COOKIES  # app/schemas/constants/legal.py (LegalDocumentKind)
_.terms_accepted_at  # app/schemas/domain/users.py
_.client_modules  # app/schemas/dto/legal.py (SubprocessorEntry)
_.notice_from  # app/schemas/dto/legal.py (SubprocessorChangeView)
_.as_of  # app/schemas/dto/legal.py (SubprocessorListView)
_.subprocessors  # app/schemas/dto/legal.py (SubprocessorListView)
_.upcoming_changes  # app/schemas/dto/legal.py (SubprocessorListView)
_.has_placeholders  # app/schemas/dto/legal.py (LegalDocumentView)
_.upcoming_version  # app/schemas/dto/legal.py (LegalDocumentView)
_.terms_version  # app/schemas/dto/login_options.py (LoginOptionsView)
_.privacy_version  # app/schemas/dto/login_options.py (LoginOptionsView)

# Day 0 of a business (W13): the monthly price after the free trial is a
# response field the Overview reads ("trial, then N a month").
_.plan_cost_after_trial_minor  # app/schemas/dto/value/value_model.py (ValueModel)

# The public site (landing-page demos, legal pages, country picker): the
# security overview is chosen by the request path (/v1/legal/security); the
# rest are response fields the landing page and the legal pages read.
_.SECURITY  # app/schemas/constants/legal.py (LegalDocumentKind)
_.has_price_book  # app/schemas/dto/catalog/countries.py (CountryListItem)
_.is_draft  # app/schemas/dto/legal.py (LegalDocumentView, LegalOverviewView)
_.niche_name  # app/schemas/dto/public_demo.py (PublicDemoCard)
_.messages_per_hour  # app/schemas/dto/public_demo.py (PublicDemoList)
_.is_booking_made  # app/schemas/dto/public_demo.py (PublicDemoReply)
_.is_request_made  # app/schemas/dto/public_demo.py (PublicDemoReply)
_.is_handoff_made  # app/schemas/dto/public_demo.py (PublicDemoReply)
_.messages_left  # app/schemas/dto/public_demo.py (PublicDemoReply)

# The DPA status the cabinet's banner and Settings → Privacy read (the
# accepted version, when to accept again); the code that implements a DPA
# security measure, read by tests/legal (every path exists).
_.latest_acceptance  # app/schemas/dto/compliance.py (DpaStatusView)
_.implemented_by  # app/schemas/dto/security_measures.py (SecurityMeasure)

# Customers (R11): who added a tag and when, and who blocked a customer, are
# kept for the audit trail; the masked phone, the segment's member count and
# the timeline's statuses are response fields the Customers pages read.
_.added_at  # app/schemas/domain/contacts.py (ContactTagMark)
_.blocked_by  # app/schemas/domain/contacts.py (ContactBlock)
_.masked_phone_number  # app/schemas/dto/contacts.py (ContactSummaryView)
_.is_phone_masked  # app/schemas/dto/contacts.py (ContactSummaryView)
_.member_count  # app/schemas/dto/customers/customer_segments.py (SegmentPreview)
_.is_count_exact  # app/schemas/dto/customers/customer_segments.py (SegmentPreview)
_.conversation_status  # app/schemas/dto/customers/customer_timeline.py
_.call_outcome  # app/schemas/dto/customers/customer_timeline.py

# What a guest's booking page (/r/{token}) and the hosted chat page read
# from the API: the ways to write, what may still change, the stay's
# availability and the owner's own booking page.
_.chat_links  # app/schemas/dto/booking_manage.py (ManagedBookingView)
_.can_cancel  # app/schemas/dto/booking_manage.py (ManagedBookingView)
_.can_reschedule  # app/schemas/dto/booking_manage.py (ManagedBookingView)
_.is_over  # app/schemas/dto/booking_manage.py (ManagedBookingView)
_.is_stay_available  # app/schemas/dto/booking_manage.py (ManagedBookingSlots)
_.booking_url  # app/schemas/dto/sharing.py (HostedChatView)

# The spend guard (R12): the admin overview's spend tile reads how much of
# the daily budget is used and the clients that passed a limit today.
_.budget_used_percent  # app/schemas/dto/spend_guard.py (PlatformSpendView)
_.braked_businesses  # app/schemas/dto/spend_guard.py (PlatformSpendView)

# Admin account actions and the client story (R13): cash is a manual
# payment method an admin picks in the cabinet; when a discount was given
# and when a manual payment was recorded are stored for the record; the
# rest are response fields the admin client page (invoices, timeline) and
# the Metrics page (business funnel and tunnel, the admins line) read.
_.CASH  # app/schemas/constants/billing.py (ManualPaymentMethod)
_.granted_at  # app/schemas/domain/billing.py (SubscriptionDiscount)
_.recorded_at  # app/schemas/domain/billing.py (ManualPayment)
_.manual_payment_method  # app/schemas/dto/admin.py (AdminInvoiceView)
_.share_of_created  # app/schemas/dto/analytics/growth_views.py (BusinessFunnelStepView)
_.by_returning_owners  # app/schemas/dto/analytics/growth_views.py (BusinessGrowthView)
_.are_platform_admins_included  # app/schemas/dto/analytics/growth_views.py (GrowthView)
_.excluded_platform_admins  # app/schemas/dto/analytics/growth_views.py (GrowthView)
_.excluded_admin_businesses  # app/schemas/dto/analytics/growth_views.py (GrowthView)
_.actor_name  # app/schemas/dto/client_story.py (ClientTimelineEntry)
_.audit_action  # app/schemas/dto/client_story.py (ClientTimelineEntry)
_.audit_entity  # app/schemas/dto/client_story.py (ClientTimelineEntry)
_.invoice_number  # app/schemas/dto/client_story.py (ClientTimelineEntry)
_.payment_method  # app/schemas/dto/client_story.py (ClientTimelineEntry)
_.health_from  # app/schemas/dto/client_story.py (ClientTimelineEntry)
_.health_to  # app/schemas/dto/client_story.py (ClientTimelineEntry)

# Referrals and partners (R15): who marked a partner's commission paid and
# the transfer's reference are stored for the record; the rest are response
# fields the cabinet reads (the invitation card and dialog, the "Powered by"
# switch on Channels → Share, the account menu's partner portal link).
_.paid_by  # app/schemas/domain/referrals.py (CommissionEntryDocument)
_.payout_reference  # app/schemas/domain/referrals.py (CommissionEntryDocument)
_.is_shown  # app/schemas/dto/referrals/program.py (PoweredByView)
_.is_removable  # app/schemas/dto/referrals/program.py (PoweredByView)
_.invite_link  # app/schemas/dto/referrals/program.py (ReferralProgramView)
_.rewarded  # app/schemas/dto/referrals/program.py (ReferralProgramView)
_.powered_by  # app/schemas/dto/referrals/program.py (ReferralProgramView)
_.is_partner  # app/schemas/dto/users.py (CurrentUserView)

# The waitlist and return visits (W17): the value model's and the stored
# reports' growth lines, the erasure result's count and the return-visit
# settings view are response fields the cabinet reads (Bookings → Return
# visits, the value hero, the reports).
_.waitlist_booking_count  # app/schemas/dto/value/value_model.py (ValueTotals)
_.waitlist_value_minor  # app/schemas/dto/value/value_model.py (ValueTotals)
_.campaign_booking_count  # app/schemas/dto/value/value_model.py (ValueTotals)
_.campaign_value_minor  # app/schemas/dto/value/value_model.py (ValueTotals)
_.anonymized_waitlist_entries  # app/schemas/dto/compliance.py (ContactErasureResult)
_.segment_name  # app/schemas/dto/growth/campaign_views.py (CampaignSettingsView)
_.niche_rule_kind  # app/schemas/dto/growth/campaign_views.py (CampaignSettingsView)
_.niche_delay_days  # app/schemas/dto/growth/campaign_views.py (CampaignSettingsView)
_.month_sent_count  # app/schemas/dto/growth/campaign_views.py (CampaignSettingsView)
_.recent_counts  # app/schemas/dto/growth/campaign_views.py (CampaignSettingsView)
_.previews  # app/schemas/dto/growth/campaign_views.py (CampaignSettingsView)

# Post-deploy data tasks (W16): the columns that need no backfill are read
# by the lookup-column policy test; the rest are response fields the
# cabinet reads (the system page's data-task card, the lists' hint).
_.LOOKUP_COLUMNS_WITHOUT_BACKFILL  # app/registries/maintenance/lookup_backfills.py
_.is_indexing  # app/schemas/dto/contacts.py, knowledge_admin.py (list pages)
_.settles_at  # app/schemas/dto/data_tasks.py (RolloutView)
_.is_gate_open  # app/utilities/storage/release_gates.py (writers of a gated enum value)
