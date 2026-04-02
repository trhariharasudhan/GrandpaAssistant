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
    offline_mode: false,
    developer_mode: false,
    emergency_mode: false,
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
