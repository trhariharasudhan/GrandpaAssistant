# API Routes Inventory

- Route declarations: 167
- Exact duplicate method/path candidates: 5
- Duplicate path candidates across methods/modules: 14

## Ownership Recommendation Counts

| Recommendation | Route Count |
| --- | --- |
| DEPRECATED_KEEP_COMPAT | 15 |
| KEEP_IN_WEB_API | 9 |
| MOVE_TO_CHAT_API_LATER | 91 |
| MOVE_TO_DEDICATED_ROUTER_LATER | 52 |

## All Routes

| Method | Path | Function | Module | File | Line | Ownership |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /agents | get_agent_statuses | api.chat_api | backend/app/api/chat_api.py | 1309 | MOVE_TO_CHAT_API_LATER |
| GET | /agents/bus | get_agent_bus_events | api.chat_api | backend/app/api/chat_api.py | 1318 | MOVE_TO_CHAT_API_LATER |
| GET | /api/auth/audit | api_auth_audit | api.web_api | backend/app/api/web_api.py | 2628 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/auth/bootstrap-status | api_auth_bootstrap_status | api.web_api | backend/app/api/web_api.py | 2512 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/auth/chat-archive | api_auth_chat_archive | api.web_api | backend/app/api/web_api.py | 2640 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/auth/login | api_auth_login | api.web_api | backend/app/api/web_api.py | 2547 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/auth/logout | api_auth_logout | api.web_api | backend/app/api/web_api.py | 2561 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/auth/me | api_auth_me | api.web_api | backend/app/api/web_api.py | 2570 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/auth/profile | api_auth_profile | api.web_api | backend/app/api/web_api.py | 2576 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/auth/profile | api_auth_update_profile | api.web_api | backend/app/api/web_api.py | 2582 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/auth/register | api_auth_register | api.web_api | backend/app/api/web_api.py | 2527 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/auth/status | api_auth_status | api.web_api | backend/app/api/web_api.py | 2517 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/auth/users | api_auth_users | api.web_api | backend/app/api/web_api.py | 2618 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/automation/n8n/test | n8n_test | api.chat_api | backend/app/api/chat_api.py | 804 | MOVE_TO_CHAT_API_LATER |
| POST | /api/automation/n8n/test | api_n8n_test | api.web_api | backend/app/api/web_api.py | 2462 | KEEP_IN_WEB_API |
| GET | /api/backend/stability | api_backend_stability | api.web_api | backend/app/api/web_api.py | 2155 | KEEP_IN_WEB_API |
| POST | /api/command | api_command | api.web_api | backend/app/api/web_api.py | 2745 | KEEP_IN_WEB_API |
| GET | /api/contacts | api_contacts | api.web_api | backend/app/api/web_api.py | 2411 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/contacts | api_add_contact | api.web_api | backend/app/api/web_api.py | 2419 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/contacts/search | api_search_contacts | api.web_api | backend/app/api/web_api.py | 2430 | MOVE_TO_DEDICATED_ROUTER_LATER |
| DELETE | /api/contacts/{name} | api_delete_contact | api.web_api | backend/app/api/web_api.py | 2443 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/context/execute-suggestion | api_context_execute_suggestion | api.web_api | backend/app/api/web_api.py | 2206 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/context/suggestions | api_context_suggestions | api.web_api | backend/app/api/web_api.py | 2198 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/dashboard | api_debug_dashboard | api.web_api | backend/app/api/web_api.py | 2367 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/docs-summary | api_debug_docs_summary | api.web_api | backend/app/api/web_api.py | 2375 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/fix-approvals | api_fix_approvals | api.web_api | backend/app/api/web_api.py | 2232 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/debug/fix-approvals | api_create_fix_approval | api.web_api | backend/app/api/web_api.py | 2240 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/debug/fix-approvals/{approval_id}/allow | api_allow_fix_approval | api.web_api | backend/app/api/web_api.py | 2248 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/debug/fix-approvals/{approval_id}/dismiss | api_dismiss_fix_approval | api.web_api | backend/app/api/web_api.py | 2256 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/fix-audit | api_fix_audit | api.web_api | backend/app/api/web_api.py | 2264 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/fix-plan | api_debug_fix_plan | api.web_api | backend/app/api/web_api.py | 2224 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/learning-summary | api_debug_learning_summary | api.web_api | backend/app/api/web_api.py | 2351 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/preflight-checklist | api_debug_preflight_checklist | api.web_api | backend/app/api/web_api.py | 2359 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/report | api_debug_report | api.web_api | backend/app/api/web_api.py | 2216 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/reuse-suggestions | api_debug_reuse_suggestions | api.web_api | backend/app/api/web_api.py | 2343 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/debug/session/close | api_debug_session_close | api.web_api | backend/app/api/web_api.py | 2300 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/session/current | api_debug_session_current | api.web_api | backend/app/api/web_api.py | 2272 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/debug/session/export | api_debug_session_export | api.web_api | backend/app/api/web_api.py | 2311 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/session/exports | api_debug_session_exports | api.web_api | backend/app/api/web_api.py | 2319 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/debug/session/start | api_debug_session_start | api.web_api | backend/app/api/web_api.py | 2288 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/sessions | api_debug_sessions | api.web_api | backend/app/api/web_api.py | 2280 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/sessions/search | api_debug_session_search | api.web_api | backend/app/api/web_api.py | 2335 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/debug/timeline | api_debug_timeline | api.web_api | backend/app/api/web_api.py | 2327 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/doctor | api_doctor | api.web_api | backend/app/api/web_api.py | 2147 | KEEP_IN_WEB_API |
| GET | /api/health | api_health | api.web_api | backend/app/api/web_api.py | 2134 | KEEP_IN_WEB_API |
| GET | /api/knowledge/review-queue | api_knowledge_review_queue | api.web_api | backend/app/api/web_api.py | 2171 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/local-actions/execute | api_execute_local_action | api.web_api | backend/app/api/web_api.py | 2473 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/memory/search | api_memory_search | api.web_api | backend/app/api/web_api.py | 2659 | KEEP_IN_WEB_API |
| GET | /api/memory/status | api_memory_status | api.web_api | backend/app/api/web_api.py | 2651 | KEEP_IN_WEB_API |
| POST | /api/mobile/devices/revoke | api_mobile_revoke_device | api.web_api | backend/app/api/web_api.py | 2799 | DEPRECATED_KEEP_COMPAT |
| POST | /api/mobile/pairing/start | api_mobile_pairing_start | api.web_api | backend/app/api/web_api.py | 2792 | DEPRECATED_KEEP_COMPAT |
| GET | /api/mobile/status | api_mobile_status | api.web_api | backend/app/api/web_api.py | 2786 | DEPRECATED_KEEP_COMPAT |
| GET | /api/phone-link/status | api_phone_link_status | api.web_api | backend/app/api/web_api.py | 2454 | KEEP_IN_WEB_API |
| POST | /api/proactive/refresh | api_refresh_proactive | api.web_api | backend/app/api/web_api.py | 2722 | KEEP_IN_WEB_API |
| GET | /api/screen/summary | api_screen_summary | api.web_api | backend/app/api/web_api.py | 2182 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/settings/focus_mode | api_update_focus_mode | api.web_api | backend/app/api/web_api.py | 2711 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/settings/portable-setup | api_portable_setup | api.web_api | backend/app/api/web_api.py | 2736 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/settings/startup | api_startup_status | api.web_api | backend/app/api/web_api.py | 2677 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/settings/startup | api_update_startup | api.web_api | backend/app/api/web_api.py | 2692 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/ui/analyze | api_ui_analyze | api.web_api | backend/app/api/web_api.py | 2489 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/ui/plan | api_ui_plan | api.web_api | backend/app/api/web_api.py | 2498 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/ui/screenshot | api_ui_screenshot | api.web_api | backend/app/api/web_api.py | 2481 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/voice/start | api_voice_start | api.web_api | backend/app/api/web_api.py | 2682 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/voice/status | api_voice_status | api.web_api | backend/app/api/web_api.py | 2672 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /api/voice/stop | api_voice_stop | api.web_api | backend/app/api/web_api.py | 2687 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/window/context | api_window_context | api.web_api | backend/app/api/web_api.py | 2190 | MOVE_TO_DEDICATED_ROUTER_LATER |
| GET | /api/windows/controls/audit | api_windows_controls_audit | api.web_api | backend/app/api/web_api.py | 2403 | MOVE_TO_DEDICATED_ROUTER_LATER |
| POST | /ask | ask | api.chat_api | backend/app/api/chat_api.py | 1577 | MOVE_TO_CHAT_API_LATER |
| GET | /auth/audit | auth_audit | api.chat_api | backend/app/api/chat_api.py | 935 | MOVE_TO_CHAT_API_LATER |
| GET | /auth/bootstrap-status | auth_bootstrap | api.chat_api | backend/app/api/chat_api.py | 821 | MOVE_TO_CHAT_API_LATER |
| GET | /auth/chat-archive | auth_chat_archive | api.chat_api | backend/app/api/chat_api.py | 947 | MOVE_TO_CHAT_API_LATER |
| POST | /auth/login | auth_login | api.chat_api | backend/app/api/chat_api.py | 855 | MOVE_TO_CHAT_API_LATER |
| POST | /auth/logout | auth_logout | api.chat_api | backend/app/api/chat_api.py | 869 | MOVE_TO_CHAT_API_LATER |
| GET | /auth/me | auth_me | api.chat_api | backend/app/api/chat_api.py | 878 | MOVE_TO_CHAT_API_LATER |
| GET | /auth/profile | auth_profile | api.chat_api | backend/app/api/chat_api.py | 883 | MOVE_TO_CHAT_API_LATER |
| POST | /auth/profile | auth_update_profile | api.chat_api | backend/app/api/chat_api.py | 889 | MOVE_TO_CHAT_API_LATER |
| POST | /auth/register | auth_register | api.chat_api | backend/app/api/chat_api.py | 835 | MOVE_TO_CHAT_API_LATER |
| GET | /auth/status | auth_status | api.chat_api | backend/app/api/chat_api.py | 826 | MOVE_TO_CHAT_API_LATER |
| GET | /auth/users | auth_users | api.chat_api | backend/app/api/chat_api.py | 925 | MOVE_TO_CHAT_API_LATER |
| POST | /chat | chat | api.chat_api | backend/app/api/chat_api.py | 1785 | MOVE_TO_CHAT_API_LATER |
| POST | /chat | chat_reply | api.web_api | backend/app/api/web_api.py | 3189 | MOVE_TO_CHAT_API_LATER |
| POST | /chat/cancel | chat_cancel | api.web_api | backend/app/api/web_api.py | 3182 | MOVE_TO_CHAT_API_LATER |
| GET | /chat/export | export_chat | api.web_api | backend/app/api/web_api.py | 3148 | MOVE_TO_CHAT_API_LATER |
| GET | /chat/history | get_chat_history | api.chat_api | backend/app/api/chat_api.py | 1773 | MOVE_TO_CHAT_API_LATER |
| GET | /chat/history | chat_history | api.web_api | backend/app/api/web_api.py | 3084 | MOVE_TO_CHAT_API_LATER |
| POST | /chat/regenerate | regenerate_reply | api.web_api | backend/app/api/web_api.py | 3299 | MOVE_TO_CHAT_API_LATER |
| POST | /chat/reset | reset_chat | api.chat_api | backend/app/api/chat_api.py | 1778 | MOVE_TO_CHAT_API_LATER |
| POST | /chat/reset | chat_reset | api.web_api | backend/app/api/web_api.py | 3171 | MOVE_TO_CHAT_API_LATER |
| GET | /chat/sessions | get_sessions | api.web_api | backend/app/api/web_api.py | 3048 | MOVE_TO_CHAT_API_LATER |
| POST | /chat/sessions | create_session | api.web_api | backend/app/api/web_api.py | 3054 | MOVE_TO_CHAT_API_LATER |
| POST | /chat/sessions/delete | delete_session | api.web_api | backend/app/api/web_api.py | 3074 | MOVE_TO_CHAT_API_LATER |
| POST | /chat/sessions/rename | rename_session | api.web_api | backend/app/api/web_api.py | 3062 | MOVE_TO_CHAT_API_LATER |
| GET | /chat/settings | get_chat_settings | api.web_api | backend/app/api/web_api.py | 3019 | MOVE_TO_CHAT_API_LATER |
| POST | /chat/settings | update_chat_settings | api.web_api | backend/app/api/web_api.py | 3025 | MOVE_TO_CHAT_API_LATER |
| POST | /chat/stream | chat_stream | api.chat_api | backend/app/api/chat_api.py | 1911 | MOVE_TO_CHAT_API_LATER |
| POST | /chat/stream | chat_stream | api.web_api | backend/app/api/web_api.py | 3355 | MOVE_TO_CHAT_API_LATER |
| POST | /chat/upload | chat_upload | api.web_api | backend/app/api/web_api.py | 3091 | MOVE_TO_CHAT_API_LATER |
| POST | /chat/upload/remove | chat_remove_upload | api.web_api | backend/app/api/web_api.py | 3123 | MOVE_TO_CHAT_API_LATER |
| POST | /decision | make_decision | api.chat_api | backend/app/api/chat_api.py | 1440 | MOVE_TO_CHAT_API_LATER |
| GET | /devices | get_devices | api.chat_api | backend/app/api/chat_api.py | 980 | MOVE_TO_CHAT_API_LATER |
| POST | /devices/rescan | rescan_devices | api.chat_api | backend/app/api/chat_api.py | 989 | MOVE_TO_CHAT_API_LATER |
| GET | /doctor | doctor | api.chat_api | backend/app/api/chat_api.py | 796 | MOVE_TO_CHAT_API_LATER |
| POST | /feedback | submit_feedback_api | api.chat_api | backend/app/api/chat_api.py | 1417 | MOVE_TO_CHAT_API_LATER |
| GET | /goals | get_runtime_goals | api.chat_api | backend/app/api/chat_api.py | 1328 | MOVE_TO_CHAT_API_LATER |
| POST | /goals | create_runtime_goal | api.chat_api | backend/app/api/chat_api.py | 1337 | MOVE_TO_CHAT_API_LATER |
| GET | /health | health | api.chat_api | backend/app/api/chat_api.py | 757 | MOVE_TO_CHAT_API_LATER |
| GET | /insights | get_user_insights | api.chat_api | backend/app/api/chat_api.py | 1409 | MOVE_TO_CHAT_API_LATER |
| GET | /intelligence/status | get_intelligence_status | api.chat_api | backend/app/api/chat_api.py | 1392 | MOVE_TO_CHAT_API_LATER |
| POST | /iot/control | iot_control | api.chat_api | backend/app/api/chat_api.py | 1112 | MOVE_TO_CHAT_API_LATER |
| GET | /iot/devices | get_iot_devices | api.chat_api | backend/app/api/chat_api.py | 1047 | MOVE_TO_CHAT_API_LATER |
| GET | /iot/history | get_iot_history | api.chat_api | backend/app/api/chat_api.py | 1074 | MOVE_TO_CHAT_API_LATER |
| POST | /iot/knowledge | iot_knowledge | api.chat_api | backend/app/api/chat_api.py | 1082 | MOVE_TO_CHAT_API_LATER |
| GET | /iot/mock/status | iot_mock_status | api.chat_api | backend/app/api/chat_api.py | 1152 | MOVE_TO_CHAT_API_LATER |
| POST | /iot/mock/{device_name}/{action} | iot_mock_action | api.chat_api | backend/app/api/chat_api.py | 1130 | MOVE_TO_CHAT_API_LATER |
| GET | /iot/status | get_iot_status | api.chat_api | backend/app/api/chat_api.py | 1058 | MOVE_TO_CHAT_API_LATER |
| GET | /iot/validate | get_iot_validation | api.chat_api | backend/app/api/chat_api.py | 1066 | MOVE_TO_CHAT_API_LATER |
| GET | /knowledge-graph | get_knowledge_graph | api.chat_api | backend/app/api/chat_api.py | 1451 | MOVE_TO_CHAT_API_LATER |
| GET | /learning/status | get_learning_status | api.chat_api | backend/app/api/chat_api.py | 1401 | MOVE_TO_CHAT_API_LATER |
| GET | /memory/contextual-recall | get_contextual_recall | api.chat_api | backend/app/api/chat_api.py | 1429 | MOVE_TO_CHAT_API_LATER |
| POST | /memory/search | search_memory_endpoint | api.chat_api | backend/app/api/chat_api.py | 1563 | MOVE_TO_CHAT_API_LATER |
| GET | /memory/status | get_memory_status | api.chat_api | backend/app/api/chat_api.py | 1555 | MOVE_TO_CHAT_API_LATER |
| POST | /mobile/auth/token | mobile_auth_token | api.web_api | backend/app/api/web_api.py | 2822 | DEPRECATED_KEEP_COMPAT |
| POST | /mobile/chat | mobile_chat | api.web_api | backend/app/api/web_api.py | 2867 | DEPRECATED_KEEP_COMPAT |
| GET | /mobile/chat/sessions | mobile_chat_sessions | api.web_api | backend/app/api/web_api.py | 2861 | DEPRECATED_KEEP_COMPAT |
| POST | /mobile/command | mobile_command | api.web_api | backend/app/api/web_api.py | 2876 | DEPRECATED_KEEP_COMPAT |
| GET | /mobile/dashboard | mobile_dashboard | api.web_api | backend/app/api/web_api.py | 2845 | DEPRECATED_KEEP_COMPAT |
| GET | /mobile/me | mobile_me | api.web_api | backend/app/api/web_api.py | 2828 | DEPRECATED_KEEP_COMPAT |
| GET | /mobile/notifications | mobile_notifications | api.web_api | backend/app/api/web_api.py | 2851 | DEPRECATED_KEEP_COMPAT |
| POST | /mobile/pairing/complete | mobile_pairing_complete | api.web_api | backend/app/api/web_api.py | 2808 | DEPRECATED_KEEP_COMPAT |
| GET | /mobile/status | mobile_status | api.web_api | backend/app/api/web_api.py | 2834 | DEPRECATED_KEEP_COMPAT |
| POST | /mobile/voice/chat | mobile_voice_chat | api.web_api | backend/app/api/web_api.py | 2914 | DEPRECATED_KEEP_COMPAT |
| POST | /mobile/voice/transcribe | mobile_voice_transcribe | api.web_api | backend/app/api/web_api.py | 2893 | DEPRECATED_KEEP_COMPAT |
| WEBSOCKET | /mobile/ws | mobile_websocket | api.web_api | backend/app/api/web_api.py | 2947 | DEPRECATED_KEEP_COMPAT |
| GET | /models | get_models | api.chat_api | backend/app/api/chat_api.py | 969 | MOVE_TO_CHAT_API_LATER |
| GET | /mood | get_mood_status | api.chat_api | backend/app/api/chat_api.py | 1539 | MOVE_TO_CHAT_API_LATER |
| POST | /mood/reset | reset_mood_status | api.chat_api | backend/app/api/chat_api.py | 1547 | MOVE_TO_CHAT_API_LATER |
| GET | /plugins | get_plugins_status | api.chat_api | backend/app/api/chat_api.py | 1351 | MOVE_TO_CHAT_API_LATER |
| POST | /plugins/reload | reload_plugin_registry | api.chat_api | backend/app/api/chat_api.py | 1362 | MOVE_TO_CHAT_API_LATER |
| POST | /plugins/toggle | toggle_plugin | api.chat_api | backend/app/api/chat_api.py | 1376 | MOVE_TO_CHAT_API_LATER |
| GET | /proactive/conversation | get_proactive_conversation | api.chat_api | backend/app/api/chat_api.py | 1530 | MOVE_TO_CHAT_API_LATER |
| GET | /recovery | get_recovery_status | api.chat_api | backend/app/api/chat_api.py | 1490 | MOVE_TO_CHAT_API_LATER |
| GET | /runtime | get_runtime_status | api.chat_api | backend/app/api/chat_api.py | 1282 | MOVE_TO_CHAT_API_LATER |
| POST | /runtime/autonomous-mode | set_runtime_autonomous_mode | api.chat_api | backend/app/api/chat_api.py | 1300 | MOVE_TO_CHAT_API_LATER |
| POST | /runtime/thinking-mode | set_runtime_thinking_mode | api.chat_api | backend/app/api/chat_api.py | 1291 | MOVE_TO_CHAT_API_LATER |
| POST | /security/admin-mode | set_security_admin_mode | api.chat_api | backend/app/api/chat_api.py | 1243 | MOVE_TO_CHAT_API_LATER |
| POST | /security/auth/face | authenticate_with_face | api.chat_api | backend/app/api/chat_api.py | 1222 | MOVE_TO_CHAT_API_LATER |
| POST | /security/auth/pin | authenticate_with_pin | api.chat_api | backend/app/api/chat_api.py | 1212 | MOVE_TO_CHAT_API_LATER |
| POST | /security/auth/voice | authenticate_with_voice | api.chat_api | backend/app/api/chat_api.py | 1232 | MOVE_TO_CHAT_API_LATER |
| GET | /security/devices | get_security_devices | api.chat_api | backend/app/api/chat_api.py | 1263 | MOVE_TO_CHAT_API_LATER |
| POST | /security/devices/trust | post_trust_device | api.chat_api | backend/app/api/chat_api.py | 1272 | MOVE_TO_CHAT_API_LATER |
| POST | /security/lockdown | set_security_lockdown | api.chat_api | backend/app/api/chat_api.py | 1253 | MOVE_TO_CHAT_API_LATER |
| GET | /security/logs | get_security_logs | api.chat_api | backend/app/api/chat_api.py | 1194 | MOVE_TO_CHAT_API_LATER |
| POST | /security/pin | configure_security_pin | api.chat_api | backend/app/api/chat_api.py | 1202 | MOVE_TO_CHAT_API_LATER |
| GET | /security/status | get_security_status | api.chat_api | backend/app/api/chat_api.py | 1186 | MOVE_TO_CHAT_API_LATER |
| GET | /settings/validation | get_settings_validation | api.chat_api | backend/app/api/chat_api.py | 1000 | MOVE_TO_CHAT_API_LATER |
| GET | /status | get_status | api.chat_api | backend/app/api/chat_api.py | 1163 | MOVE_TO_CHAT_API_LATER |
| POST | /sync/config | configure_sync_api | api.chat_api | backend/app/api/chat_api.py | 1506 | MOVE_TO_CHAT_API_LATER |
| GET | /sync/export | export_sync_state | api.chat_api | backend/app/api/chat_api.py | 1514 | MOVE_TO_CHAT_API_LATER |
| POST | /sync/import | import_sync_state | api.chat_api | backend/app/api/chat_api.py | 1522 | MOVE_TO_CHAT_API_LATER |
| GET | /sync/status | get_sync_status | api.chat_api | backend/app/api/chat_api.py | 1498 | MOVE_TO_CHAT_API_LATER |
| POST | /voice/custom/autoconfigure | autoconfigure_custom_voice | api.chat_api | backend/app/api/chat_api.py | 1037 | MOVE_TO_CHAT_API_LATER |
| GET | /voice/custom/status | get_custom_voice_status | api.chat_api | backend/app/api/chat_api.py | 1028 | MOVE_TO_CHAT_API_LATER |
| POST | /voice/piper/autoconfigure | autoconfigure_piper | api.chat_api | backend/app/api/chat_api.py | 1018 | MOVE_TO_CHAT_API_LATER |
| GET | /voice/piper/status | get_piper_status | api.chat_api | backend/app/api/chat_api.py | 1009 | MOVE_TO_CHAT_API_LATER |
| GET | /workflows | get_workflows | api.chat_api | backend/app/api/chat_api.py | 1459 | MOVE_TO_CHAT_API_LATER |
| POST | /workflows | create_workflow_api | api.chat_api | backend/app/api/chat_api.py | 1467 | MOVE_TO_CHAT_API_LATER |
| POST | /workflows/run | run_workflow_api | api.chat_api | backend/app/api/chat_api.py | 1479 | MOVE_TO_CHAT_API_LATER |

## Exact Duplicate Method/Path Candidates

| Method | Path | Locations |
| --- | --- | --- |
| POST | /api/automation/n8n/test | backend/app/api/chat_api.py:804 `n8n_test`<br>backend/app/api/web_api.py:2462 `api_n8n_test` |
| POST | /chat | backend/app/api/chat_api.py:1785 `chat`<br>backend/app/api/web_api.py:3189 `chat_reply` |
| GET | /chat/history | backend/app/api/chat_api.py:1773 `get_chat_history`<br>backend/app/api/web_api.py:3084 `chat_history` |
| POST | /chat/reset | backend/app/api/chat_api.py:1778 `reset_chat`<br>backend/app/api/web_api.py:3171 `chat_reset` |
| POST | /chat/stream | backend/app/api/chat_api.py:1911 `chat_stream`<br>backend/app/api/web_api.py:3355 `chat_stream` |

## Duplicate Path Candidates

| Path | Methods | Locations |
| --- | --- | --- |
| /api/auth/profile | GET, POST | GET backend/app/api/web_api.py:2576 `api_auth_profile`<br>POST backend/app/api/web_api.py:2582 `api_auth_update_profile` |
| /api/automation/n8n/test | POST | POST backend/app/api/chat_api.py:804 `n8n_test`<br>POST backend/app/api/web_api.py:2462 `api_n8n_test` |
| /api/contacts | GET, POST | GET backend/app/api/web_api.py:2411 `api_contacts`<br>POST backend/app/api/web_api.py:2419 `api_add_contact` |
| /api/debug/fix-approvals | GET, POST | GET backend/app/api/web_api.py:2232 `api_fix_approvals`<br>POST backend/app/api/web_api.py:2240 `api_create_fix_approval` |
| /api/settings/startup | GET, POST | GET backend/app/api/web_api.py:2677 `api_startup_status`<br>POST backend/app/api/web_api.py:2692 `api_update_startup` |
| /auth/profile | GET, POST | GET backend/app/api/chat_api.py:883 `auth_profile`<br>POST backend/app/api/chat_api.py:889 `auth_update_profile` |
| /chat | POST | POST backend/app/api/chat_api.py:1785 `chat`<br>POST backend/app/api/web_api.py:3189 `chat_reply` |
| /chat/history | GET | GET backend/app/api/chat_api.py:1773 `get_chat_history`<br>GET backend/app/api/web_api.py:3084 `chat_history` |
| /chat/reset | POST | POST backend/app/api/chat_api.py:1778 `reset_chat`<br>POST backend/app/api/web_api.py:3171 `chat_reset` |
| /chat/sessions | GET, POST | GET backend/app/api/web_api.py:3048 `get_sessions`<br>POST backend/app/api/web_api.py:3054 `create_session` |
| /chat/settings | GET, POST | GET backend/app/api/web_api.py:3019 `get_chat_settings`<br>POST backend/app/api/web_api.py:3025 `update_chat_settings` |
| /chat/stream | POST | POST backend/app/api/chat_api.py:1911 `chat_stream`<br>POST backend/app/api/web_api.py:3355 `chat_stream` |
| /goals | GET, POST | GET backend/app/api/chat_api.py:1328 `get_runtime_goals`<br>POST backend/app/api/chat_api.py:1337 `create_runtime_goal` |
| /workflows | GET, POST | GET backend/app/api/chat_api.py:1459 `get_workflows`<br>POST backend/app/api/chat_api.py:1467 `create_workflow_api` |
