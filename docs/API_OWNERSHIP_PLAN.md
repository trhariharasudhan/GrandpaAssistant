# API Ownership Plan

This is a read-only classification generated from route inventory heuristics. It is a planning document, not a code movement instruction.

## Recommendation Meanings

| Status | Meaning |
| --- | --- |
| KEEP_IN_WEB_API | Keep in `backend/app/api/web_api.py` for the active desktop backend runtime. |
| MOVE_TO_CHAT_API_LATER | Candidate to move or consolidate into the chat API after contracts and tests are explicit. |
| MOVE_TO_DEDICATED_ROUTER_LATER | Candidate for a future domain router such as auth, debug, voice, contacts, UI analysis, or context. |
| DEPRECATED_KEEP_COMPAT | Keep for compatibility. Do not remove without replacement clients and migration notes. |
| UNKNOWN_NEEDS_REVIEW | Route could not be classified safely by this inventory script. |

## Current Recommendation

Keep `backend/app/api/web_api.py` as the active desktop backend API owner for now. Treat `backend/app/api/chat_api.py` as a candidate chat-focused surface that needs explicit ownership before any consolidation.

## Phase 1 Duplicate Route Decisions

The active desktop backend entrypoint imports `backend/app/api/web_api.py`. The duplicate declarations in `backend/app/api/chat_api.py` are registered only on the alternate `chat_api.app`, not on the active desktop app object.

| Route | Active Owner | Secondary Declaration | Decision | Future Action |
| --- | --- | --- | --- | --- |
| POST /api/automation/n8n/test | backend/app/api/web_api.py::api_n8n_test | backend/app/api/chat_api.py::n8n_test | KEEP_IN_WEB_API | Keep chat_api copy until alternate chat API ownership is decided. |
| POST /chat | backend/app/api/web_api.py::chat_reply | backend/app/api/chat_api.py::chat | KEEP_IN_WEB_API_NOW_MOVE_TO_CHAT_API_LATER | Move or consolidate only after the chat API contract and desktop API compatibility are explicit. |
| GET /chat/history | backend/app/api/web_api.py::chat_history | backend/app/api/chat_api.py::get_chat_history | KEEP_IN_WEB_API_NOW_MOVE_TO_CHAT_API_LATER | Preserve web_api behavior; later compare response schemas before consolidation. |
| POST /chat/reset | backend/app/api/web_api.py::chat_reset | backend/app/api/chat_api.py::reset_chat | KEEP_IN_WEB_API_NOW_MOVE_TO_CHAT_API_LATER | Preserve web_api behavior; later compare session reset semantics before consolidation. |
| POST /chat/stream | backend/app/api/web_api.py::chat_stream | backend/app/api/chat_api.py::chat_stream | KEEP_IN_WEB_API_NOW_MOVE_TO_CHAT_API_LATER | Preserve web_api streaming behavior; later align stream event format if chat_api becomes owner. |

## KEEP_IN_WEB_API

| Method | Path | Function | File | Line |
| --- | --- | --- | --- | --- |
| POST | /api/automation/n8n/test | api_n8n_test | backend/app/api/web_api.py | 2462 |
| GET | /api/backend/stability | api_backend_stability | backend/app/api/web_api.py | 2155 |
| POST | /api/command | api_command | backend/app/api/web_api.py | 2745 |
| GET | /api/doctor | api_doctor | backend/app/api/web_api.py | 2147 |
| GET | /api/health | api_health | backend/app/api/web_api.py | 2134 |
| POST | /api/memory/search | api_memory_search | backend/app/api/web_api.py | 2659 |
| GET | /api/memory/status | api_memory_status | backend/app/api/web_api.py | 2651 |
| GET | /api/phone-link/status | api_phone_link_status | backend/app/api/web_api.py | 2454 |
| POST | /api/proactive/refresh | api_refresh_proactive | backend/app/api/web_api.py | 2722 |

## MOVE_TO_CHAT_API_LATER

| Method | Path | Function | File | Line |
| --- | --- | --- | --- | --- |
| GET | /agents | get_agent_statuses | backend/app/api/chat_api.py | 1309 |
| GET | /agents/bus | get_agent_bus_events | backend/app/api/chat_api.py | 1318 |
| POST | /api/automation/n8n/test | n8n_test | backend/app/api/chat_api.py | 804 |
| POST | /ask | ask | backend/app/api/chat_api.py | 1577 |
| GET | /auth/audit | auth_audit | backend/app/api/chat_api.py | 935 |
| GET | /auth/bootstrap-status | auth_bootstrap | backend/app/api/chat_api.py | 821 |
| GET | /auth/chat-archive | auth_chat_archive | backend/app/api/chat_api.py | 947 |
| POST | /auth/login | auth_login | backend/app/api/chat_api.py | 855 |
| POST | /auth/logout | auth_logout | backend/app/api/chat_api.py | 869 |
| GET | /auth/me | auth_me | backend/app/api/chat_api.py | 878 |
| GET | /auth/profile | auth_profile | backend/app/api/chat_api.py | 883 |
| POST | /auth/profile | auth_update_profile | backend/app/api/chat_api.py | 889 |
| POST | /auth/register | auth_register | backend/app/api/chat_api.py | 835 |
| GET | /auth/status | auth_status | backend/app/api/chat_api.py | 826 |
| GET | /auth/users | auth_users | backend/app/api/chat_api.py | 925 |
| POST | /chat | chat | backend/app/api/chat_api.py | 1785 |
| POST | /chat | chat_reply | backend/app/api/web_api.py | 3189 |
| POST | /chat/cancel | chat_cancel | backend/app/api/web_api.py | 3182 |
| GET | /chat/export | export_chat | backend/app/api/web_api.py | 3148 |
| GET | /chat/history | get_chat_history | backend/app/api/chat_api.py | 1773 |
| GET | /chat/history | chat_history | backend/app/api/web_api.py | 3084 |
| POST | /chat/regenerate | regenerate_reply | backend/app/api/web_api.py | 3299 |
| POST | /chat/reset | reset_chat | backend/app/api/chat_api.py | 1778 |
| POST | /chat/reset | chat_reset | backend/app/api/web_api.py | 3171 |
| GET | /chat/sessions | get_sessions | backend/app/api/web_api.py | 3048 |
| POST | /chat/sessions | create_session | backend/app/api/web_api.py | 3054 |
| POST | /chat/sessions/delete | delete_session | backend/app/api/web_api.py | 3074 |
| POST | /chat/sessions/rename | rename_session | backend/app/api/web_api.py | 3062 |
| GET | /chat/settings | get_chat_settings | backend/app/api/web_api.py | 3019 |
| POST | /chat/settings | update_chat_settings | backend/app/api/web_api.py | 3025 |
| POST | /chat/stream | chat_stream | backend/app/api/chat_api.py | 1911 |
| POST | /chat/stream | chat_stream | backend/app/api/web_api.py | 3355 |
| POST | /chat/upload | chat_upload | backend/app/api/web_api.py | 3091 |
| POST | /chat/upload/remove | chat_remove_upload | backend/app/api/web_api.py | 3123 |
| POST | /decision | make_decision | backend/app/api/chat_api.py | 1440 |
| GET | /devices | get_devices | backend/app/api/chat_api.py | 980 |
| POST | /devices/rescan | rescan_devices | backend/app/api/chat_api.py | 989 |
| GET | /doctor | doctor | backend/app/api/chat_api.py | 796 |
| POST | /feedback | submit_feedback_api | backend/app/api/chat_api.py | 1417 |
| GET | /goals | get_runtime_goals | backend/app/api/chat_api.py | 1328 |
| POST | /goals | create_runtime_goal | backend/app/api/chat_api.py | 1337 |
| GET | /health | health | backend/app/api/chat_api.py | 757 |
| GET | /insights | get_user_insights | backend/app/api/chat_api.py | 1409 |
| GET | /intelligence/status | get_intelligence_status | backend/app/api/chat_api.py | 1392 |
| POST | /iot/control | iot_control | backend/app/api/chat_api.py | 1112 |
| GET | /iot/devices | get_iot_devices | backend/app/api/chat_api.py | 1047 |
| GET | /iot/history | get_iot_history | backend/app/api/chat_api.py | 1074 |
| POST | /iot/knowledge | iot_knowledge | backend/app/api/chat_api.py | 1082 |
| GET | /iot/mock/status | iot_mock_status | backend/app/api/chat_api.py | 1152 |
| POST | /iot/mock/{device_name}/{action} | iot_mock_action | backend/app/api/chat_api.py | 1130 |
| GET | /iot/status | get_iot_status | backend/app/api/chat_api.py | 1058 |
| GET | /iot/validate | get_iot_validation | backend/app/api/chat_api.py | 1066 |
| GET | /knowledge-graph | get_knowledge_graph | backend/app/api/chat_api.py | 1451 |
| GET | /learning/status | get_learning_status | backend/app/api/chat_api.py | 1401 |
| GET | /memory/contextual-recall | get_contextual_recall | backend/app/api/chat_api.py | 1429 |
| POST | /memory/search | search_memory_endpoint | backend/app/api/chat_api.py | 1563 |
| GET | /memory/status | get_memory_status | backend/app/api/chat_api.py | 1555 |
| GET | /models | get_models | backend/app/api/chat_api.py | 969 |
| GET | /mood | get_mood_status | backend/app/api/chat_api.py | 1539 |
| POST | /mood/reset | reset_mood_status | backend/app/api/chat_api.py | 1547 |
| GET | /plugins | get_plugins_status | backend/app/api/chat_api.py | 1351 |
| POST | /plugins/reload | reload_plugin_registry | backend/app/api/chat_api.py | 1362 |
| POST | /plugins/toggle | toggle_plugin | backend/app/api/chat_api.py | 1376 |
| GET | /proactive/conversation | get_proactive_conversation | backend/app/api/chat_api.py | 1530 |
| GET | /recovery | get_recovery_status | backend/app/api/chat_api.py | 1490 |
| GET | /runtime | get_runtime_status | backend/app/api/chat_api.py | 1282 |
| POST | /runtime/autonomous-mode | set_runtime_autonomous_mode | backend/app/api/chat_api.py | 1300 |
| POST | /runtime/thinking-mode | set_runtime_thinking_mode | backend/app/api/chat_api.py | 1291 |
| POST | /security/admin-mode | set_security_admin_mode | backend/app/api/chat_api.py | 1243 |
| POST | /security/auth/face | authenticate_with_face | backend/app/api/chat_api.py | 1222 |
| POST | /security/auth/pin | authenticate_with_pin | backend/app/api/chat_api.py | 1212 |
| POST | /security/auth/voice | authenticate_with_voice | backend/app/api/chat_api.py | 1232 |
| GET | /security/devices | get_security_devices | backend/app/api/chat_api.py | 1263 |
| POST | /security/devices/trust | post_trust_device | backend/app/api/chat_api.py | 1272 |
| POST | /security/lockdown | set_security_lockdown | backend/app/api/chat_api.py | 1253 |
| GET | /security/logs | get_security_logs | backend/app/api/chat_api.py | 1194 |
| POST | /security/pin | configure_security_pin | backend/app/api/chat_api.py | 1202 |
| GET | /security/status | get_security_status | backend/app/api/chat_api.py | 1186 |
| GET | /settings/validation | get_settings_validation | backend/app/api/chat_api.py | 1000 |
| GET | /status | get_status | backend/app/api/chat_api.py | 1163 |
| POST | /sync/config | configure_sync_api | backend/app/api/chat_api.py | 1506 |
| GET | /sync/export | export_sync_state | backend/app/api/chat_api.py | 1514 |
| POST | /sync/import | import_sync_state | backend/app/api/chat_api.py | 1522 |
| GET | /sync/status | get_sync_status | backend/app/api/chat_api.py | 1498 |
| POST | /voice/custom/autoconfigure | autoconfigure_custom_voice | backend/app/api/chat_api.py | 1037 |
| GET | /voice/custom/status | get_custom_voice_status | backend/app/api/chat_api.py | 1028 |
| POST | /voice/piper/autoconfigure | autoconfigure_piper | backend/app/api/chat_api.py | 1018 |
| GET | /voice/piper/status | get_piper_status | backend/app/api/chat_api.py | 1009 |
| GET | /workflows | get_workflows | backend/app/api/chat_api.py | 1459 |
| POST | /workflows | create_workflow_api | backend/app/api/chat_api.py | 1467 |
| POST | /workflows/run | run_workflow_api | backend/app/api/chat_api.py | 1479 |

## MOVE_TO_DEDICATED_ROUTER_LATER

| Method | Path | Function | File | Line |
| --- | --- | --- | --- | --- |
| GET | /api/auth/audit | api_auth_audit | backend/app/api/web_api.py | 2628 |
| GET | /api/auth/bootstrap-status | api_auth_bootstrap_status | backend/app/api/web_api.py | 2512 |
| GET | /api/auth/chat-archive | api_auth_chat_archive | backend/app/api/web_api.py | 2640 |
| POST | /api/auth/login | api_auth_login | backend/app/api/web_api.py | 2547 |
| POST | /api/auth/logout | api_auth_logout | backend/app/api/web_api.py | 2561 |
| GET | /api/auth/me | api_auth_me | backend/app/api/web_api.py | 2570 |
| GET | /api/auth/profile | api_auth_profile | backend/app/api/web_api.py | 2576 |
| POST | /api/auth/profile | api_auth_update_profile | backend/app/api/web_api.py | 2582 |
| POST | /api/auth/register | api_auth_register | backend/app/api/web_api.py | 2527 |
| GET | /api/auth/status | api_auth_status | backend/app/api/web_api.py | 2517 |
| GET | /api/auth/users | api_auth_users | backend/app/api/web_api.py | 2618 |
| GET | /api/contacts | api_contacts | backend/app/api/web_api.py | 2411 |
| POST | /api/contacts | api_add_contact | backend/app/api/web_api.py | 2419 |
| GET | /api/contacts/search | api_search_contacts | backend/app/api/web_api.py | 2430 |
| DELETE | /api/contacts/{name} | api_delete_contact | backend/app/api/web_api.py | 2443 |
| POST | /api/context/execute-suggestion | api_context_execute_suggestion | backend/app/api/web_api.py | 2206 |
| GET | /api/context/suggestions | api_context_suggestions | backend/app/api/web_api.py | 2198 |
| GET | /api/debug/dashboard | api_debug_dashboard | backend/app/api/web_api.py | 2367 |
| GET | /api/debug/docs-summary | api_debug_docs_summary | backend/app/api/web_api.py | 2375 |
| GET | /api/debug/fix-approvals | api_fix_approvals | backend/app/api/web_api.py | 2232 |
| POST | /api/debug/fix-approvals | api_create_fix_approval | backend/app/api/web_api.py | 2240 |
| POST | /api/debug/fix-approvals/{approval_id}/allow | api_allow_fix_approval | backend/app/api/web_api.py | 2248 |
| POST | /api/debug/fix-approvals/{approval_id}/dismiss | api_dismiss_fix_approval | backend/app/api/web_api.py | 2256 |
| GET | /api/debug/fix-audit | api_fix_audit | backend/app/api/web_api.py | 2264 |
| GET | /api/debug/fix-plan | api_debug_fix_plan | backend/app/api/web_api.py | 2224 |
| GET | /api/debug/learning-summary | api_debug_learning_summary | backend/app/api/web_api.py | 2351 |
| GET | /api/debug/preflight-checklist | api_debug_preflight_checklist | backend/app/api/web_api.py | 2359 |
| GET | /api/debug/report | api_debug_report | backend/app/api/web_api.py | 2216 |
| GET | /api/debug/reuse-suggestions | api_debug_reuse_suggestions | backend/app/api/web_api.py | 2343 |
| POST | /api/debug/session/close | api_debug_session_close | backend/app/api/web_api.py | 2300 |
| GET | /api/debug/session/current | api_debug_session_current | backend/app/api/web_api.py | 2272 |
| POST | /api/debug/session/export | api_debug_session_export | backend/app/api/web_api.py | 2311 |
| GET | /api/debug/session/exports | api_debug_session_exports | backend/app/api/web_api.py | 2319 |
| POST | /api/debug/session/start | api_debug_session_start | backend/app/api/web_api.py | 2288 |
| GET | /api/debug/sessions | api_debug_sessions | backend/app/api/web_api.py | 2280 |
| GET | /api/debug/sessions/search | api_debug_session_search | backend/app/api/web_api.py | 2335 |
| GET | /api/debug/timeline | api_debug_timeline | backend/app/api/web_api.py | 2327 |
| GET | /api/knowledge/review-queue | api_knowledge_review_queue | backend/app/api/web_api.py | 2171 |
| POST | /api/local-actions/execute | api_execute_local_action | backend/app/api/web_api.py | 2473 |
| GET | /api/screen/summary | api_screen_summary | backend/app/api/web_api.py | 2182 |
| POST | /api/settings/focus_mode | api_update_focus_mode | backend/app/api/web_api.py | 2711 |
| POST | /api/settings/portable-setup | api_portable_setup | backend/app/api/web_api.py | 2736 |
| GET | /api/settings/startup | api_startup_status | backend/app/api/web_api.py | 2677 |
| POST | /api/settings/startup | api_update_startup | backend/app/api/web_api.py | 2692 |
| POST | /api/ui/analyze | api_ui_analyze | backend/app/api/web_api.py | 2489 |
| POST | /api/ui/plan | api_ui_plan | backend/app/api/web_api.py | 2498 |
| GET | /api/ui/screenshot | api_ui_screenshot | backend/app/api/web_api.py | 2481 |
| POST | /api/voice/start | api_voice_start | backend/app/api/web_api.py | 2682 |
| GET | /api/voice/status | api_voice_status | backend/app/api/web_api.py | 2672 |
| POST | /api/voice/stop | api_voice_stop | backend/app/api/web_api.py | 2687 |
| GET | /api/window/context | api_window_context | backend/app/api/web_api.py | 2190 |
| GET | /api/windows/controls/audit | api_windows_controls_audit | backend/app/api/web_api.py | 2403 |

## DEPRECATED_KEEP_COMPAT

| Method | Path | Function | File | Line |
| --- | --- | --- | --- | --- |
| POST | /api/mobile/devices/revoke | api_mobile_revoke_device | backend/app/api/web_api.py | 2799 |
| POST | /api/mobile/pairing/start | api_mobile_pairing_start | backend/app/api/web_api.py | 2792 |
| GET | /api/mobile/status | api_mobile_status | backend/app/api/web_api.py | 2786 |
| POST | /mobile/auth/token | mobile_auth_token | backend/app/api/web_api.py | 2822 |
| POST | /mobile/chat | mobile_chat | backend/app/api/web_api.py | 2867 |
| GET | /mobile/chat/sessions | mobile_chat_sessions | backend/app/api/web_api.py | 2861 |
| POST | /mobile/command | mobile_command | backend/app/api/web_api.py | 2876 |
| GET | /mobile/dashboard | mobile_dashboard | backend/app/api/web_api.py | 2845 |
| GET | /mobile/me | mobile_me | backend/app/api/web_api.py | 2828 |
| GET | /mobile/notifications | mobile_notifications | backend/app/api/web_api.py | 2851 |
| POST | /mobile/pairing/complete | mobile_pairing_complete | backend/app/api/web_api.py | 2808 |
| GET | /mobile/status | mobile_status | backend/app/api/web_api.py | 2834 |
| POST | /mobile/voice/chat | mobile_voice_chat | backend/app/api/web_api.py | 2914 |
| POST | /mobile/voice/transcribe | mobile_voice_transcribe | backend/app/api/web_api.py | 2893 |
| WEBSOCKET | /mobile/ws | mobile_websocket | backend/app/api/web_api.py | 2947 |

## UNKNOWN_NEEDS_REVIEW

| Method | Path | Function | File | Line |
| --- | --- | --- | --- | --- |
