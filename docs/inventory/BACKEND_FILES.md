# Backend Files Inventory

Scanned `backend/app`.

- Python files: 273
- Large files over 500 lines: 29
- Files with TODO/FIXME/deprecated markers: 0

## All Python Files

| File | Module | Lines | Markers |
| --- | --- | --- | --- |
| backend/app/__init__.py | __init__ | 19 | 0 |
| backend/app/agents/__init__.py | agents.__init__ | 3 | 0 |
| backend/app/agents/base.py | agents.base | 39 | 0 |
| backend/app/agents/catalog.py | agents.catalog | 213 | 0 |
| backend/app/agents/message_bus.py | agents.message_bus | 63 | 0 |
| backend/app/agents/runtime.py | agents.runtime | 168 | 0 |
| backend/app/agents/state_store.py | agents.state_store | 198 | 0 |
| backend/app/api/__init__.py | api.__init__ | 1 | 0 |
| backend/app/api/chat_api.py | api.chat_api | 2000 | 0 |
| backend/app/api/web_api.py | api.web_api | 3607 | 0 |
| backend/app/cli/__init__.py | cli.__init__ | 1 | 0 |
| backend/app/cli/chat.py | cli.chat | 115 | 0 |
| backend/app/config/grandpa_config.py | config.grandpa_config | 100 | 0 |
| backend/app/core/__init__.py | core.__init__ | 0 | 0 |
| backend/app/core/assistant.py | core.assistant | 991 | 0 |
| backend/app/core/chat_service.py | core.chat_service | 377 | 0 |
| backend/app/core/chatbot/__init__.py | core.chatbot.__init__ | 3 | 0 |
| backend/app/core/chatbot/engine.py | core.chatbot.engine | 151 | 0 |
| backend/app/core/chatbot/intent_router.py | core.chatbot.intent_router | 109 | 0 |
| backend/app/core/chatbot/language.py | core.chatbot.language | 49 | 0 |
| backend/app/core/chatbot/memory.py | core.chatbot.memory | 176 | 0 |
| backend/app/core/chatbot/prompt_builder.py | core.chatbot.prompt_builder | 12 | 0 |
| backend/app/core/chatbot/providers/__init__.py | core.chatbot.providers.__init__ | 6 | 0 |
| backend/app/core/chatbot/providers/base.py | core.chatbot.providers.base | 21 | 0 |
| backend/app/core/chatbot/providers/fallback_provider.py | core.chatbot.providers.fallback_provider | 14 | 0 |
| backend/app/core/chatbot/providers/gemini_provider.py | core.chatbot.providers.gemini_provider | 18 | 0 |
| backend/app/core/chatbot/providers/ollama_provider.py | core.chatbot.providers.ollama_provider | 17 | 0 |
| backend/app/core/chatbot/providers/openai_provider.py | core.chatbot.providers.openai_provider | 18 | 0 |
| backend/app/core/command_router.py | core.command_router | 6441 | 0 |
| backend/app/core/commands/__init__.py | core.commands.__init__ | 7 | 0 |
| backend/app/core/commands/context.py | core.commands.context | 98 | 0 |
| backend/app/core/commands/handlers/__init__.py | core.commands.handlers.__init__ | 1 | 0 |
| backend/app/core/commands/handlers/audio_status.py | core.commands.handlers.audio_status | 75 | 0 |
| backend/app/core/commands/handlers/awareness.py | core.commands.handlers.awareness | 61 | 0 |
| backend/app/core/commands/handlers/config_status.py | core.commands.handlers.config_status | 77 | 0 |
| backend/app/core/commands/handlers/contacts.py | core.commands.handlers.contacts | 80 | 0 |
| backend/app/core/commands/handlers/debug.py | core.commands.handlers.debug | 141 | 0 |
| backend/app/core/commands/handlers/developer_status.py | core.commands.handlers.developer_status | 97 | 0 |
| backend/app/core/commands/handlers/device_status.py | core.commands.handlers.device_status | 56 | 0 |
| backend/app/core/commands/handlers/diagnostics.py | core.commands.handlers.diagnostics | 88 | 0 |
| backend/app/core/commands/handlers/emergency_status.py | core.commands.handlers.emergency_status | 63 | 0 |
| backend/app/core/commands/handlers/interface_status.py | core.commands.handlers.interface_status | 78 | 0 |
| backend/app/core/commands/handlers/iot_status.py | core.commands.handlers.iot_status | 77 | 0 |
| backend/app/core/commands/handlers/knowledge.py | core.commands.handlers.knowledge | 81 | 0 |
| backend/app/core/commands/handlers/knowledge_services.py | core.commands.handlers.knowledge_services | 71 | 0 |
| backend/app/core/commands/handlers/memory.py | core.commands.handlers.memory | 83 | 0 |
| backend/app/core/commands/handlers/notification_status.py | core.commands.handlers.notification_status | 77 | 0 |
| backend/app/core/commands/handlers/overlay_status.py | core.commands.handlers.overlay_status | 74 | 0 |
| backend/app/core/commands/handlers/planning.py | core.commands.handlers.planning | 88 | 0 |
| backend/app/core/commands/handlers/productivity.py | core.commands.handlers.productivity | 91 | 0 |
| backend/app/core/commands/handlers/profile_status.py | core.commands.handlers.profile_status | 60 | 0 |
| backend/app/core/commands/handlers/project_knowledge.py | core.commands.handlers.project_knowledge | 86 | 0 |
| backend/app/core/commands/handlers/security_status.py | core.commands.handlers.security_status | 90 | 0 |
| backend/app/core/commands/handlers/status.py | core.commands.handlers.status | 107 | 0 |
| backend/app/core/commands/handlers/system_health.py | core.commands.handlers.system_health | 113 | 0 |
| backend/app/core/commands/registry.py | core.commands.registry | 142 | 0 |
| backend/app/core/commands/result.py | core.commands.result | 16 | 0 |
| backend/app/core/commands/summaries/__init__.py | core.commands.summaries.__init__ | 1 | 0 |
| backend/app/core/commands/summaries/audio.py | core.commands.summaries.audio | 68 | 0 |
| backend/app/core/commands/summaries/config.py | core.commands.summaries.config | 66 | 0 |
| backend/app/core/commands/summaries/interface.py | core.commands.summaries.interface | 35 | 0 |
| backend/app/core/commands/summaries/notification.py | core.commands.summaries.notification | 82 | 0 |
| backend/app/core/commands/summaries/overlay.py | core.commands.summaries.overlay | 54 | 0 |
| backend/app/core/followup_memory.py | core.followup_memory | 42 | 0 |
| backend/app/core/intent_router.py | core.intent_router | 2136 | 0 |
| backend/app/core/llm/__init__.py | core.llm.__init__ | 23 | 0 |
| backend/app/core/llm/base.py | core.llm.base | 41 | 0 |
| backend/app/core/llm/provider_manager.py | core.llm.provider_manager | 98 | 0 |
| backend/app/core/llm/providers/__init__.py | core.llm.providers.__init__ | 11 | 0 |
| backend/app/core/llm/providers/fallback_provider.py | core.llm.providers.fallback_provider | 32 | 0 |
| backend/app/core/llm/providers/gemini_provider.py | core.llm.providers.gemini_provider | 87 | 0 |
| backend/app/core/llm/providers/ollama_provider.py | core.llm.providers.ollama_provider | 146 | 0 |
| backend/app/core/llm/providers/openai_provider.py | core.llm.providers.openai_provider | 107 | 0 |
| backend/app/core/llm/registry.py | core.llm.registry | 46 | 0 |
| backend/app/core/llm/status.py | core.llm.status | 159 | 0 |
| backend/app/core/module_contracts.py | core.module_contracts | 42 | 0 |
| backend/app/core/personal_assistant/__init__.py | core.personal_assistant.__init__ | 6 | 0 |
| backend/app/core/personal_assistant/context.py | core.personal_assistant.context | 85 | 0 |
| backend/app/core/personal_assistant/executor.py | core.personal_assistant.executor | 203 | 0 |
| backend/app/core/personal_assistant/intent_engine.py | core.personal_assistant.intent_engine | 188 | 0 |
| backend/app/core/personal_assistant/planner.py | core.personal_assistant.planner | 154 | 0 |
| backend/app/core/personal_assistant/service.py | core.personal_assistant.service | 88 | 0 |
| backend/app/core/planner_payload_verifier.py | core.planner_payload_verifier | 130 | 0 |
| backend/app/core/planner_prompt_payload.py | core.planner_prompt_payload | 148 | 0 |
| backend/app/core/prompt_builder.py | core.prompt_builder | 71 | 0 |
| backend/app/core/prompt_loader.py | core.prompt_loader | 52 | 0 |
| backend/app/core/prompt_memory_context.py | core.prompt_memory_context | 79 | 0 |
| backend/app/core/prompt_mode_resolver.py | core.prompt_mode_resolver | 109 | 0 |
| backend/app/core/prompt_modes.py | core.prompt_modes | 45 | 0 |
| backend/app/core/prompt_runtime_observability.py | core.prompt_runtime_observability | 61 | 0 |
| backend/app/core/prompt_runtime_status.py | core.prompt_runtime_status | 59 | 0 |
| backend/app/core/prompts/__init__.py | core.prompts.__init__ | 21 | 0 |
| backend/app/core/prompts/base.py | core.prompts.base | 24 | 0 |
| backend/app/core/prompts/builder.py | core.prompts.builder | 52 | 0 |
| backend/app/core/prompts/context_blocks.py | core.prompts.context_blocks | 37 | 0 |
| backend/app/core/prompts/language_style.py | core.prompts.language_style | 55 | 0 |
| backend/app/core/prompts/policies.py | core.prompts.policies | 27 | 0 |
| backend/app/core/prompts/route_adapters.py | core.prompts.route_adapters | 151 | 0 |
| backend/app/core/runtime_prompt_adapter.py | core.runtime_prompt_adapter | 126 | 0 |
| backend/app/core/unified_command_router.py | core.unified_command_router | 413 | 0 |
| backend/app/features/__init__.py | features.__init__ | 1 | 0 |
| backend/app/features/automation/__init__.py | features.automation.__init__ | 1 | 0 |
| backend/app/features/automation/dictation_module.py | features.automation.dictation_module | 71 | 0 |
| backend/app/features/automation/messaging_automation_module.py | features.automation.messaging_automation_module | 1427 | 0 |
| backend/app/features/automation/notification_module.py | features.automation.notification_module | 791 | 0 |
| backend/app/features/automation/startup_module.py | features.automation.startup_module | 93 | 0 |
| backend/app/features/integrations/__init__.py | features.integrations.__init__ | 1 | 0 |
| backend/app/features/integrations/google_calendar_module.py | features.integrations.google_calendar_module | 541 | 0 |
| backend/app/features/integrations/google_contacts_module.py | features.integrations.google_contacts_module | 837 | 0 |
| backend/app/features/integrations/iot_module.py | features.integrations.iot_module | 18 | 0 |
| backend/app/features/integrations/weather_module.py | features.integrations.weather_module | 178 | 0 |
| backend/app/features/integrations/web_module.py | features.integrations.web_module | 292 | 0 |
| backend/app/features/intelligence/__init__.py | features.intelligence.__init__ | 1 | 0 |
| backend/app/features/intelligence/browser_automation_module.py | features.intelligence.browser_automation_module | 721 | 0 |
| backend/app/features/intelligence/file_intelligence_module.py | features.intelligence.file_intelligence_module | 328 | 0 |
| backend/app/features/modules/__init__.py | features.modules.__init__ | 2 | 0 |
| backend/app/features/modules/app_scan_module.py | features.modules.app_scan_module | 7 | 0 |
| backend/app/features/modules/briefing_module.py | features.modules.briefing_module | 7 | 0 |
| backend/app/features/modules/browser_automation_module.py | features.modules.browser_automation_module | 7 | 0 |
| backend/app/features/modules/calendar_module.py | features.modules.calendar_module | 7 | 0 |
| backend/app/features/modules/dashboard_module.py | features.modules.dashboard_module | 7 | 0 |
| backend/app/features/modules/desktop_launch_module.py | features.modules.desktop_launch_module | 27 | 0 |
| backend/app/features/modules/dictation_module.py | features.modules.dictation_module | 7 | 0 |
| backend/app/features/modules/event_module.py | features.modules.event_module | 7 | 0 |
| backend/app/features/modules/export_module.py | features.modules.export_module | 7 | 0 |
| backend/app/features/modules/file_intelligence_module.py | features.modules.file_intelligence_module | 7 | 0 |
| backend/app/features/modules/google_calendar_module.py | features.modules.google_calendar_module | 7 | 0 |
| backend/app/features/modules/google_contacts_module.py | features.modules.google_contacts_module | 7 | 0 |
| backend/app/features/modules/health_module.py | features.modules.health_module | 7 | 0 |
| backend/app/features/modules/media_module.py | features.modules.media_module | 7 | 0 |
| backend/app/features/modules/messaging_automation_module.py | features.modules.messaging_automation_module | 7 | 0 |
| backend/app/features/modules/nextgen_module.py | features.modules.nextgen_module | 7 | 0 |
| backend/app/features/modules/notes_module.py | features.modules.notes_module | 7 | 0 |
| backend/app/features/modules/notification_module.py | features.modules.notification_module | 7 | 0 |
| backend/app/features/modules/profile_module.py | features.modules.profile_module | 7 | 0 |
| backend/app/features/modules/routine_module.py | features.modules.routine_module | 7 | 0 |
| backend/app/features/modules/startup_module.py | features.modules.startup_module | 7 | 0 |
| backend/app/features/modules/system_module.py | features.modules.system_module | 7 | 0 |
| backend/app/features/modules/task_module.py | features.modules.task_module | 7 | 0 |
| backend/app/features/modules/weather_module.py | features.modules.weather_module | 7 | 0 |
| backend/app/features/modules/web_module.py | features.modules.web_module | 7 | 0 |
| backend/app/features/modules/window_context_module.py | features.modules.window_context_module | 7 | 0 |
| backend/app/features/modules/windows_voice_control_module.py | features.modules.windows_voice_control_module | 7 | 0 |
| backend/app/features/productivity/__init__.py | features.productivity.__init__ | 1 | 0 |
| backend/app/features/productivity/briefing_module.py | features.productivity.briefing_module | 157 | 0 |
| backend/app/features/productivity/calendar_module.py | features.productivity.calendar_module | 238 | 0 |
| backend/app/features/productivity/dashboard_module.py | features.productivity.dashboard_module | 239 | 0 |
| backend/app/features/productivity/event_module.py | features.productivity.event_module | 631 | 0 |
| backend/app/features/productivity/export_module.py | features.productivity.export_module | 185 | 0 |
| backend/app/features/productivity/nextgen_module.py | features.productivity.nextgen_module | 1035 | 0 |
| backend/app/features/productivity/notes_module.py | features.productivity.notes_module | 167 | 0 |
| backend/app/features/productivity/proactive_suggestion_engine.py | features.productivity.proactive_suggestion_engine | 440 | 0 |
| backend/app/features/productivity/profile_module.py | features.productivity.profile_module | 462 | 0 |
| backend/app/features/productivity/routine_module.py | features.productivity.routine_module | 171 | 0 |
| backend/app/features/productivity/task_module.py | features.productivity.task_module | 1182 | 0 |
| backend/app/features/security/emergency_dispatch.py | features.security.emergency_dispatch | 102 | 0 |
| backend/app/features/security/face_verification.py | features.security.face_verification | 110 | 0 |
| backend/app/features/system/__init__.py | features.system.__init__ | 1 | 0 |
| backend/app/features/system/app_scan_module.py | features.system.app_scan_module | 282 | 0 |
| backend/app/features/system/health_module.py | features.system.health_module | 61 | 0 |
| backend/app/features/system/media_module.py | features.system.media_module | 35 | 0 |
| backend/app/features/system/system_module.py | features.system.system_module | 1208 | 0 |
| backend/app/features/system/window_context_module.py | features.system.window_context_module | 785 | 0 |
| backend/app/features/system/windows_voice_control_module.py | features.system.windows_voice_control_module | 592 | 0 |
| backend/app/features/ui_analysis/__init__.py | features.ui_analysis.__init__ | 1 | 0 |
| backend/app/features/ui_analysis/action_planner.py | features.ui_analysis.action_planner | 95 | 0 |
| backend/app/features/ui_analysis/screen_capture.py | features.ui_analysis.screen_capture | 81 | 0 |
| backend/app/features/ui_analysis/ui_action_executor.py | features.ui_analysis.ui_action_executor | 79 | 0 |
| backend/app/features/ui_analysis/ui_element_detector.py | features.ui_analysis.ui_element_detector | 141 | 0 |
| backend/app/features/ui_analysis/ui_models.py | features.ui_analysis.ui_models | 34 | 0 |
| backend/app/features/vision/__init__.py | features.vision.__init__ | 0 | 0 |
| backend/app/features/vision/hand_mouse_control.py | features.vision.hand_mouse_control | 382 | 0 |
| backend/app/features/vision/object_detection.py | features.vision.object_detection | 665 | 0 |
| backend/app/features/vision/screen_reader.py | features.vision.screen_reader | 694 | 0 |
| backend/app/features/vision/vision_models.py | features.vision.vision_models | 374 | 0 |
| backend/app/features/voice/__init__.py | features.voice.__init__ | 0 | 0 |
| backend/app/features/voice/listen.py | features.voice.listen | 976 | 0 |
| backend/app/features/voice/speak.py | features.voice.speak | 1277 | 0 |
| backend/app/integrations/__init__.py | integrations.__init__ | 1 | 0 |
| backend/app/integrations/n8n_client.py | integrations.n8n_client | 80 | 0 |
| backend/app/project_knowledge/__init__.py | project_knowledge.__init__ | 5 | 0 |
| backend/app/project_knowledge/cache.py | project_knowledge.cache | 213 | 0 |
| backend/app/project_knowledge/cached_search.py | project_knowledge.cached_search | 96 | 0 |
| backend/app/project_knowledge/chunker.py | project_knowledge.chunker | 90 | 0 |
| backend/app/project_knowledge/config.py | project_knowledge.config | 96 | 0 |
| backend/app/project_knowledge/content_reader.py | project_knowledge.content_reader | 122 | 0 |
| backend/app/project_knowledge/file_discovery.py | project_knowledge.file_discovery | 63 | 0 |
| backend/app/project_knowledge/file_filters.py | project_knowledge.file_filters | 51 | 0 |
| backend/app/project_knowledge/file_metadata.py | project_knowledge.file_metadata | 56 | 0 |
| backend/app/project_knowledge/lexical_index.py | project_knowledge.lexical_index | 129 | 0 |
| backend/app/project_knowledge/project_chunks.py | project_knowledge.project_chunks | 57 | 0 |
| backend/app/project_knowledge/project_context_adapter.py | project_knowledge.project_context_adapter | 61 | 0 |
| backend/app/project_knowledge/project_context_status.py | project_knowledge.project_context_status | 61 | 0 |
| backend/app/project_knowledge/project_search.py | project_knowledge.project_search | 31 | 0 |
| backend/app/project_knowledge/project_snapshot.py | project_knowledge.project_snapshot | 28 | 0 |
| backend/app/project_knowledge/retrieval_context.py | project_knowledge.retrieval_context | 143 | 0 |
| backend/app/project_knowledge/tokenizer.py | project_knowledge.tokenizer | 53 | 0 |
| backend/app/security/__init__.py | security.__init__ | 2 | 0 |
| backend/app/security/auth_manager.py | security.auth_manager | 416 | 0 |
| backend/app/security/device_monitor.py | security.device_monitor | 143 | 0 |
| backend/app/security/encryption_utils.py | security.encryption_utils | 185 | 0 |
| backend/app/security/hub.py | security.hub | 101 | 0 |
| backend/app/security/permission_engine.py | security.permission_engine | 109 | 0 |
| backend/app/security/state.py | security.state | 181 | 0 |
| backend/app/security/threat_detector.py | security.threat_detector | 157 | 0 |
| backend/app/services/__init__.py | services.__init__ | 1 | 0 |
| backend/app/services/local_action_executor.py | services.local_action_executor | 219 | 0 |
| backend/app/shared/__init__.py | shared.__init__ | 1 | 0 |
| backend/app/shared/ai_router.py | shared.ai_router | 142 | 0 |
| backend/app/shared/api_cors.py | shared.api_cors | 36 | 0 |
| backend/app/shared/api_logging.py | shared.api_logging | 50 | 0 |
| backend/app/shared/app_auth.py | shared.app_auth | 295 | 0 |
| backend/app/shared/app_data_store.py | shared.app_data_store | 484 | 0 |
| backend/app/shared/backend_stability.py | shared.backend_stability | 171 | 0 |
| backend/app/shared/brain/__init__.py | shared.brain.__init__ | 0 | 0 |
| backend/app/shared/brain/ai_engine.py | shared.brain.ai_engine | 673 | 0 |
| backend/app/shared/brain/database.py | shared.brain.database | 258 | 0 |
| backend/app/shared/brain/memory_engine.py | shared.brain.memory_engine | 909 | 0 |
| backend/app/shared/brain/question_analyzer.py | shared.brain.question_analyzer | 47 | 0 |
| backend/app/shared/brain/semantic_memory.py | shared.brain.semantic_memory | 488 | 0 |
| backend/app/shared/call_control.py | shared.call_control | 204 | 0 |
| backend/app/shared/claude_client.py | shared.claude_client | 106 | 0 |
| backend/app/shared/cognition/__init__.py | shared.cognition.__init__ | 15 | 0 |
| backend/app/shared/cognition/context_engine.py | shared.cognition.context_engine | 61 | 0 |
| backend/app/shared/cognition/decision_engine.py | shared.cognition.decision_engine | 124 | 0 |
| backend/app/shared/cognition/graph_engine.py | shared.cognition.graph_engine | 174 | 0 |
| backend/app/shared/cognition/hub.py | shared.cognition.hub | 115 | 0 |
| backend/app/shared/cognition/insight_engine.py | shared.cognition.insight_engine | 133 | 0 |
| backend/app/shared/cognition/learning_engine.py | shared.cognition.learning_engine | 652 | 0 |
| backend/app/shared/cognition/personality_engine.py | shared.cognition.personality_engine | 40 | 0 |
| backend/app/shared/cognition/proactive_engine.py | shared.cognition.proactive_engine | 91 | 0 |
| backend/app/shared/cognition/recovery_engine.py | shared.cognition.recovery_engine | 93 | 0 |
| backend/app/shared/cognition/state.py | shared.cognition.state | 195 | 0 |
| backend/app/shared/cognition/sync_engine.py | shared.cognition.sync_engine | 107 | 0 |
| backend/app/shared/cognition/workflow_engine.py | shared.cognition.workflow_engine | 143 | 0 |
| backend/app/shared/contact_manager.py | shared.contact_manager | 146 | 0 |
| backend/app/shared/context_action_executor.py | shared.context_action_executor | 197 | 0 |
| backend/app/shared/context_suggestions.py | shared.context_suggestions | 164 | 0 |
| backend/app/shared/controls/__init__.py | shared.controls.__init__ | 0 | 0 |
| backend/app/shared/controls/brightness_control.py | shared.controls.brightness_control | 75 | 0 |
| backend/app/shared/controls/volume_control.py | shared.controls.volume_control | 178 | 0 |
| backend/app/shared/debug_assistant.py | shared.debug_assistant | 240 | 0 |
| backend/app/shared/debug_health_dashboard.py | shared.debug_health_dashboard | 196 | 0 |
| backend/app/shared/debug_knowledge_reuse.py | shared.debug_knowledge_reuse | 142 | 0 |
| backend/app/shared/debug_learning_summary.py | shared.debug_learning_summary | 162 | 0 |
| backend/app/shared/debug_preflight_checklist.py | shared.debug_preflight_checklist | 186 | 0 |
| backend/app/shared/debug_session.py | shared.debug_session | 192 | 0 |
| backend/app/shared/debug_session_export.py | shared.debug_session_export | 211 | 0 |
| backend/app/shared/debug_session_search.py | shared.debug_session_search | 148 | 0 |
| backend/app/shared/debug_timeline.py | shared.debug_timeline | 172 | 0 |
| backend/app/shared/device_manager.py | shared.device_manager | 1030 | 0 |
| backend/app/shared/fix_approval_flow.py | shared.fix_approval_flow | 253 | 0 |
| backend/app/shared/fix_audit_log.py | shared.fix_audit_log | 142 | 0 |
| backend/app/shared/fix_plan_generator.py | shared.fix_plan_generator | 193 | 0 |
| backend/app/shared/iot_control.py | shared.iot_control | 515 | 0 |
| backend/app/shared/iot_registry.py | shared.iot_registry | 694 | 0 |
| backend/app/shared/llm_client.py | shared.llm_client | 534 | 0 |
| backend/app/shared/local_knowledge.py | shared.local_knowledge | 344 | 0 |
| backend/app/shared/mobile_companion.py | shared.mobile_companion | 494 | 0 |
| backend/app/shared/offline_multi_model.py | shared.offline_multi_model | 237 | 0 |
| backend/app/shared/phone_link_readiness.py | shared.phone_link_readiness | 67 | 0 |
| backend/app/shared/plugin_system.py | shared.plugin_system | 190 | 0 |
| backend/app/shared/productivity_store.py | shared.productivity_store | 222 | 0 |
| backend/app/shared/screen_awareness.py | shared.screen_awareness | 197 | 0 |
| backend/app/shared/startup_diagnostics.py | shared.startup_diagnostics | 555 | 0 |
| backend/app/shared/utils/__init__.py | shared.utils.__init__ | 0 | 0 |
| backend/app/shared/utils/config.py | shared.utils.config | 587 | 0 |
| backend/app/shared/utils/emotion.py | shared.utils.emotion | 123 | 0 |
| backend/app/shared/utils/mood_memory.py | shared.utils.mood_memory | 199 | 0 |
| backend/app/shared/utils/paths.py | shared.utils.paths | 123 | 0 |
| backend/app/shared/utils/sound.py | shared.utils.sound | 49 | 0 |
| backend/app/shared/window_awareness.py | shared.window_awareness | 196 | 0 |
| backend/app/shared/windows_control_audit.py | shared.windows_control_audit | 116 | 0 |

## Large Files Over 500 Lines

| File | Lines |
| --- | --- |
| backend/app/core/command_router.py | 6441 |
| backend/app/api/web_api.py | 3607 |
| backend/app/core/intent_router.py | 2136 |
| backend/app/api/chat_api.py | 2000 |
| backend/app/features/automation/messaging_automation_module.py | 1427 |
| backend/app/features/voice/speak.py | 1277 |
| backend/app/features/system/system_module.py | 1208 |
| backend/app/features/productivity/task_module.py | 1182 |
| backend/app/features/productivity/nextgen_module.py | 1035 |
| backend/app/shared/device_manager.py | 1030 |
| backend/app/core/assistant.py | 991 |
| backend/app/features/voice/listen.py | 976 |
| backend/app/shared/brain/memory_engine.py | 909 |
| backend/app/features/integrations/google_contacts_module.py | 837 |
| backend/app/features/automation/notification_module.py | 791 |
| backend/app/features/system/window_context_module.py | 785 |
| backend/app/features/intelligence/browser_automation_module.py | 721 |
| backend/app/features/vision/screen_reader.py | 694 |
| backend/app/shared/iot_registry.py | 694 |
| backend/app/shared/brain/ai_engine.py | 673 |
| backend/app/features/vision/object_detection.py | 665 |
| backend/app/shared/cognition/learning_engine.py | 652 |
| backend/app/features/productivity/event_module.py | 631 |
| backend/app/features/system/windows_voice_control_module.py | 592 |
| backend/app/shared/utils/config.py | 587 |
| backend/app/shared/startup_diagnostics.py | 555 |
| backend/app/features/integrations/google_calendar_module.py | 541 |
| backend/app/shared/llm_client.py | 534 |
| backend/app/shared/iot_control.py | 515 |

## Marker Files

| File | Marker Count | Preview |
| --- | --- | --- |
