export const API_BASE = "http://127.0.0.1:8765";
export const CHAT_API_BASE = API_BASE;

export const initialMessages = [];

export const initialChatSettings = {
  llm_provider: "ollama",
  model: "gpt-4.1-mini",
  ollama_model: "llama3:8b",
  system_prompt: "You are Grandpa Assistant, a warm, practical AI desktop assistant.",
  tone: "friendly",
  response_style: "balanced",
  tool_mode: true,
  llm_status: {
    provider: "openai-compatible",
    model: "gpt-4.1-mini",
    base_url: "https://api.openai.com/v1",
    api_key_configured: false,
    ready: false,
  },
};

export const initialChatSessions = [];

export const initialUiState = {
  overview: {
    tasks: "Loading...",
    reminders: "Loading...",
    weather: "Loading...",
    health: "Loading...",
    object_detection: "Loading...",
  },
  today: "Loading...",
  next_event: "Loading...",
  latest_note: "Loading...",
  recent_commands: [],
  notifications: [],
  dashboard: {
    tasks: [],
    reminders: [],
    events: [],
    vision: [],
  },
  settings: {
    wake_word: "Loading...",
    voice_profile: "Loading...",
    voice_popup_enabled: true,
    voice_chime_enabled: true,
    offline_mode: false,
    developer_mode: false,
    emergency_mode: false,
    focus_mode: false,
  },
  proactive: {
    focus_mode: false,
    summary: "Loading...",
    suggestions: [],
  },
  contacts: {
    favorite_contact: "Loading...",
    preview: [],
    aliases_summary: "Loading...",
    favorites_summary: "Loading...",
    recent_changes: "Loading...",
  },
  emergency: {
    location: "Loading...",
    contact: "Loading...",
    mode_enabled: false,
    protocol_summary: "Loading...",
  },
  memory: {
    preferred_language: "Loading...",
    favorite_contact: "Loading...",
  },
  integrations: {
    smart_home: {
      configured: false,
      enabled: false,
      device_count: 0,
      sample_commands: [],
      placeholder_count: 0,
      summary: "Loading...",
    },
    face_security: {
      enrolled: false,
      camera_ready: false,
      embedding_ready: false,
      updated_at: "",
      summary: "Loading...",
    },
  },
  object_watch: {
    active: false,
    target: "",
    summary: "Loading...",
  },
  object_detection: {
    model_name: "yolov8n.pt",
    small_object_mode: false,
    presets: [],
  },
  object_history: [],
  object_watch_history: [],
};

export const initialVoiceStatus = {
  enabled: false,
  activity: "Ready",
  state_label: "ready",
  wake_word: "hey grandpa",
  voice_profile: "normal",
  follow_up_active: false,
  follow_up_remaining: 0,
  transcript: "",
  error: "",
  messages: [],
  last_reply: "",
  settings: {
    mode: "normal",
    post_wake_pause_seconds: 0.35,
    wake_listen_timeout: 5,
    wake_phrase_time_limit: 4,
    wake_match_threshold: 0.68,
    wake_retry_window_seconds: 6,
    follow_up_timeout_seconds: 12,
    wake_direct_fallback_enabled: true,
    desktop_popup_enabled: true,
    desktop_chime_enabled: true,
  },
  diagnostics: {
    wake_detection_count: 0,
    wake_only_count: 0,
    command_count: 0,
    follow_up_command_count: 0,
    retry_window_command_count: 0,
    direct_fallback_count: 0,
    interrupt_count: 0,
    error_count: 0,
    last_heard_phrase: "",
    last_processed_command: "",
    last_wake_at: "",
    last_command_at: "",
    last_interrupt_at: "",
    last_error_at: "",
    last_error_message: "",
    wake_retry_window_active: false,
    wake_retry_remaining: 0,
  },
};

export const initialStartupState = {
  auto_launch_enabled: false,
  tray_mode: false,
  summary: "Loading...",
  portable_setup_ready: false,
  react_ui_on_tray_enabled: false,
  react_ui_on_tray_mode: "browser",
  react_frontend_ready: false,
  react_desktop_ready: false,
};
