import { useEffect, useMemo, useRef, useState } from "react";
import ChatSurface from "./components/ChatSurface";
import DashboardSurface from "./components/DashboardSurface";
import LogoMark from "./components/LogoMark";
import SidebarPanels from "./components/SidebarPanels";
import VoiceWave from "./components/VoiceWave";
import {
  API_BASE,
  CHAT_API_BASE,
  initialChatSessions,
  initialChatSettings,
  initialMessages,
  initialStartupState,
  initialUiState,
  initialVoiceStatus,
} from "./constants/appState";
import { cleanPlannerItem, matchesCommand, normalizeMessageText } from "./utils/text";

export default function App() {
  const messagesEndRef = useRef(null);
  const [mode, setMode] = useState("text");
  const [surfaceTab, setSurfaceTab] = useState("chat");
  const [workspaceTab, setWorkspaceTab] = useState("planner");
  const [now, setNow] = useState(new Date());
  const [input, setInput] = useState("");
  const [taskInput, setTaskInput] = useState("");
  const [reminderText, setReminderText] = useState("");
  const [reminderWhen, setReminderWhen] = useState("tomorrow at 8 pm");
  const [eventText, setEventText] = useState("");
  const [eventWhen, setEventWhen] = useState("tomorrow at 6 pm");
  const [noteInput, setNoteInput] = useState("");
  const [noteSearch, setNoteSearch] = useState("");
  const [taskTitleInput, setTaskTitleInput] = useState("");
  const [reminderTitleInput, setReminderTitleInput] = useState("");
  const [reminderRescheduleInput, setReminderRescheduleInput] = useState("tomorrow at 8 pm");
  const [eventTitleInput, setEventTitleInput] = useState("");
  const [eventRescheduleInput, setEventRescheduleInput] = useState("tomorrow at 6 pm");
  const [calendarTitle, setCalendarTitle] = useState("");
  const [calendarWhen, setCalendarWhen] = useState("tomorrow at 6 pm");
  const [wakeWordInput, setWakeWordInput] = useState("");
  const [wakeThresholdInput, setWakeThresholdInput] = useState("0.68");
  const [followUpTimeoutInput, setFollowUpTimeoutInput] = useState("12");
  const [wakeRetryInput, setWakeRetryInput] = useState("8");
  const [objectModelInput, setObjectModelInput] = useState("");
  const [objectPresetNameInput, setObjectPresetNameInput] = useState("");
  const [contactAlias, setContactAlias] = useState("");
  const [contactAliasTarget, setContactAliasTarget] = useState("");
  const [contactSearch, setContactSearch] = useState("");
  const [chatSearch, setChatSearch] = useState("");
  const [attachedDocuments, setAttachedDocuments] = useState([]);
  const [selectedContact, setSelectedContact] = useState("");
  const [selectedPlanner, setSelectedPlanner] = useState({
    type: "",
    text: "",
  });
  const [messages, setMessages] = useState(initialMessages);
  const [activity, setActivity] = useState("Ready");
  const [uiState, setUiState] = useState(initialUiState);
  const [apiError, setApiError] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [pendingConfirmation, setPendingConfirmation] = useState(null);
  const [chatSessions, setChatSessions] = useState(initialChatSessions);
  const [currentSessionId, setCurrentSessionId] = useState("");
  const [chatSettings, setChatSettings] = useState(initialChatSettings);
  const [chatSettingsDraft, setChatSettingsDraft] = useState(initialChatSettings);
  const [showChatSettings, setShowChatSettings] = useState(false);
  const [lastPrompt, setLastPrompt] = useState("");
  const [voiceStatus, setVoiceStatus] = useState(initialVoiceStatus);
  const [voiceToast, setVoiceToast] = useState(null);
  const [startupState, setStartupState] = useState(initialStartupState);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(0);
  const [pinnedCommands, setPinnedCommands] = useState([
    "plan my day",
    "weather",
    "latest note",
  ]);
  const previousVoiceStateRef = useRef(initialVoiceStatus.state_label);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  useEffect(() => {
    setActiveSuggestionIndex(0);
  }, [input]);

  useEffect(() => {
    setActivity(mode === "voice" ? voiceStatus.activity || "Ready" : "Ready");
  }, [mode, voiceStatus.activity]);

  useEffect(() => {
    if (!selectedContact && uiState.contacts.favorite_contact && uiState.contacts.favorite_contact !== "Loading...") {
      setSelectedContact(uiState.contacts.favorite_contact);
    }
  }, [selectedContact, uiState.contacts.favorite_contact]);

  useEffect(() => {
    const configured = voiceStatus.settings?.wake_match_threshold;
    if (typeof configured === "number" && Number.isFinite(configured)) {
      setWakeThresholdInput(String(configured));
    }
  }, [voiceStatus.settings?.wake_match_threshold]);

  useEffect(() => {
    if (voiceStatus.follow_up_remaining) {
      setFollowUpTimeoutInput(String(Math.max(voiceStatus.follow_up_remaining, 12)));
    }
  }, [voiceStatus.follow_up_remaining]);

  useEffect(() => {
    if (mode !== "voice") {
      previousVoiceStateRef.current = voiceStatus.state_label || "ready";
      return;
    }

    const currentState = voiceStatus.state_label || "ready";
    const previousState = previousVoiceStateRef.current;
    previousVoiceStateRef.current = currentState;
    const voicePopupEnabled = voiceStatus.settings?.desktop_popup_enabled ?? uiState.settings.voice_popup_enabled ?? true;
    const voiceChimeEnabled = voiceStatus.settings?.desktop_chime_enabled ?? uiState.settings.voice_chime_enabled ?? true;

    if (!voicePopupEnabled) {
      setVoiceToast(null);
      return;
    }

    if (!currentState || currentState === previousState) {
      return;
    }

    const toastMap = {
      sleeping: {
        title: "Back To Sleep",
        text: `Say ${voiceStatus.wake_word || "hey grandpa"} to wake me again.`,
        tone: 460,
      },
      awake: {
        title: "Wake Word Heard",
        text: "Assistant is awake and listening now.",
        tone: 720,
      },
      follow_up: {
        title: "Follow-up Active",
        text: `You can continue talking${voiceStatus.follow_up_remaining ? ` for ${voiceStatus.follow_up_remaining}s` : ""}.`,
        tone: 620,
      },
      speaking: {
        title: "Replying",
        text: "Assistant is speaking now.",
        tone: 560,
      },
      interrupted: {
        title: "Interrupted",
        text: "Speech stopped. Listening again.",
        tone: 390,
      },
      error: {
        title: "Voice Error",
        text: voiceStatus.error || "Voice mode hit an issue.",
        tone: 300,
      },
    };

    const toast = toastMap[currentState];
    if (!toast) {
      return;
    }

    const toastId = Date.now();
    setVoiceToast({ ...toast, id: toastId, state: currentState });

    if (voiceChimeEnabled) {
      try {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (AudioContextClass) {
          const audioContext = new AudioContextClass();
          const oscillator = audioContext.createOscillator();
          const gain = audioContext.createGain();
          oscillator.type = currentState === "error" ? "sawtooth" : "sine";
          oscillator.frequency.value = toast.tone;
          gain.gain.value = currentState === "error" ? 0.025 : 0.018;
          oscillator.connect(gain);
          gain.connect(audioContext.destination);
          oscillator.start();
          oscillator.stop(audioContext.currentTime + 0.12);
          oscillator.onended = () => {
            audioContext.close().catch(() => {});
          };
        }
      } catch (_error) {
        // Ignore browser audio errors and keep the toast visible.
      }
    }

    const timer = window.setTimeout(() => {
      setVoiceToast((current) => (current?.id === toastId ? null : current));
    }, 2200);

    return () => window.clearTimeout(timer);
  }, [
    mode,
    voiceStatus.state_label,
    voiceStatus.follow_up_remaining,
    voiceStatus.error,
    voiceStatus.wake_word,
    voiceStatus.settings?.desktop_popup_enabled,
    voiceStatus.settings?.desktop_chime_enabled,
    uiState.settings.voice_popup_enabled,
    uiState.settings.voice_chime_enabled,
  ]);

  useEffect(() => {
    setObjectModelInput(uiState.object_detection?.model_name || "");
  }, [uiState.object_detection?.model_name]);

  const mapHistoryMessages = (items = []) =>
    items.map((item, index) => ({
      id: item.id || `history-${index}`,
      side: item.role === "user" ? "user" : "assistant",
      text: item.content || "",
      createdAt: item.created_at ? Date.parse(item.created_at) : Date.now() + index,
      streaming: false,
    }));

  const mapSessionDocuments = (items = []) =>
    (items || []).map((item, index) => ({
      id: item.id || `doc-${index}`,
      name: item.name || "Document",
      kind: item.kind || "file",
      uploaded_at: item.uploaded_at || "",
      char_count: item.char_count || 0,
      chunk_count: item.chunk_count || 0,
      preview: item.preview || "",
    }));

  useEffect(() => {
    if (mode !== "voice") {
      return;
    }

    let cancelled = false;

    const loadVoiceStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/voice/status`);
        const payload = await response.json();
        if (!cancelled && payload?.ok && payload.voice) {
          setVoiceStatus(payload.voice);
          setApiError(payload.voice.error ? payload.voice.error : "");
          if (payload.voice.messages?.length) {
            setMessages((current) => {
              const existing = new Set(current.map((item) => `${item.side}:${item.text}`));
              const fresh = payload.voice.messages
                .map((line, index) => {
                  const isUser = line.startsWith("You : ");
                  const cleanedLine = isUser ? line.replace(/^You\s:\s*/, "") : line;
                  return {
                    id: `voice-${Date.now()}-${index}`,
                    side: isUser ? "user" : "assistant",
                    text: cleanedLine,
                    createdAt: Date.now() + index,
                  };
                })
                .filter((item) => !existing.has(`${item.side}:${item.text}`));
              return fresh.length ? [...current, ...fresh] : current;
            });
          }
        }
      } catch (_error) {
        if (!cancelled) {
          setApiError("Voice service is not reachable yet.");
        }
      }
    };

    loadVoiceStatus();
    const timer = window.setInterval(loadVoiceStatus, 400);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [mode]);

  useEffect(() => {
    let cancelled = false;

    const loadChatHistory = async () => {
      try {
        const [historyResponse, sessionsResponse, settingsResponse] = await Promise.all([
          fetch(`${CHAT_API_BASE}/chat/history`),
          fetch(`${CHAT_API_BASE}/chat/sessions`),
          fetch(`${CHAT_API_BASE}/chat/settings`),
        ]);
        const historyPayload = await historyResponse.json();
        const sessionsPayload = await sessionsResponse.json();
        const settingsPayload = await settingsResponse.json();
        if (!cancelled && historyPayload?.ok) {
          setMessages(mapHistoryMessages(historyPayload.messages));
          if (historyPayload.session?.id) {
            setCurrentSessionId(historyPayload.session.id);
          }
          setAttachedDocuments(mapSessionDocuments(historyPayload.session?.documents));
        }
        if (!cancelled && sessionsPayload?.ok) {
          setChatSessions(sessionsPayload.sessions || []);
        }
        if (!cancelled && settingsPayload?.ok && settingsPayload.settings) {
          setChatSettings(settingsPayload.settings);
          setChatSettingsDraft(settingsPayload.settings);
          if (!settingsPayload.settings?.llm_status?.ready) {
            setApiError("OpenAI key not configured. Create a .env file in the project root and set OPENAI_API_KEY.");
          }
        }
      } catch (_error) {
        if (!cancelled) {
          setApiError("Chat history could not be loaded.");
        }
      }
    };

    const loadState = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/ui-state`);
        const payload = await response.json();
        if (!cancelled && payload?.ok && payload.state) {
          setUiState(payload.state);
          if (payload.state.voice) {
            setVoiceStatus(payload.state.voice);
          }
          if (payload.state.startup) {
            setStartupState(payload.state.startup);
          }
          setApiError("");
        }
      } catch (_error) {
        if (!cancelled) {
          setApiError("Python assistant API is not reachable yet.");
        }
      }
    };

    loadChatHistory();
    loadState();
    const timer = window.setInterval(loadState, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const runCommand = async (rawCommand) => {
    const value = (rawCommand || "").trim();
    if (!value) return;
    const userMessage = { id: Date.now(), side: "user", text: value, createdAt: Date.now() };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setActivity("Thinking");

    try {
      const response = await fetch(`${API_BASE}/api/command`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ command: value }),
      });
      const payload = await response.json();

      if (!payload?.ok) {
        throw new Error(payload?.error || "Command failed.");
      }

      if (payload.requires_confirmation && payload.confirmation_id) {
        setPendingConfirmation({
          confirmationId: payload.confirmation_id,
          command: payload.command || value,
        });
      }

      const replies = (payload.messages || []).map((text, index) => ({
        id: `${Date.now()}-${index}`,
        side: "assistant",
        text: `Grandpa : ${text}`,
        createdAt: Date.now() + index + 1,
      }));
      setMessages((current) => [...current, ...replies]);
      if (payload.state) {
        setUiState(payload.state);
        if (payload.state.voice) {
          setVoiceStatus(payload.state.voice);
        }
        if (payload.state.startup) {
          setStartupState(payload.state.startup);
        }
      }
      setApiError("");
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-error`,
          side: "assistant",
          text: `Grandpa : ${error.message || "Assistant API unavailable."}`,
          createdAt: Date.now(),
        },
      ]);
      setApiError("Python assistant API is not reachable yet.");
    } finally {
      setActivity(mode === "voice" ? "Listening" : "Ready");
    }
  };

  const promptForObjectModel = async () => {
    const currentModel = uiState.object_detection?.model_name || "yolov8n.pt";
    const modelPath = window.prompt("Enter YOLO model file name or full path", currentModel);
    if (!modelPath) return;
    await runCommand(`use object model ${modelPath}`);
  };

  const promptToSaveObjectPreset = async () => {
    const modelPath = uiState.object_detection?.model_name || "";
    const presetName = window.prompt("Enter a preset name for the current object model");
    if (!presetName) return;
    await runCommand(`save object model preset ${modelPath} as ${presetName}`);
  };

  const promptToUseObjectPreset = async () => {
    const presetName = window.prompt("Enter the saved object preset name to use");
    if (!presetName) return;
    await runCommand(`use object preset ${presetName}`);
  };

  const applyObjectModelInput = async () => {
    const value = (objectModelInput || "").trim();
    if (!value) return;
    await runCommand(`use object model ${value}`);
  };

  const saveObjectPresetFromInputs = async () => {
    const modelValue = (objectModelInput || "").trim();
    const presetValue = (objectPresetNameInput || "").trim();
    if (!modelValue || !presetValue) return;
    await runCommand(`save object model preset ${modelValue} as ${presetValue}`);
    setObjectPresetNameInput("");
  };

  const prepareKeyDetection = async () => {
    await runCommand("prepare key detection");
  };

  const useObjectPresetByName = async (presetName) => {
    await runCommand(`use object preset ${presetName}`);
  };

  const deleteObjectPresetByName = async (presetName) => {
    await runCommand(`delete object preset ${presetName}`);
  };

  const handleSend = async (rawInput = input) => {
    const value = (rawInput || "").trim();
    if (!value || isChatLoading) return;

    const userMessage = { id: `user-${Date.now()}`, side: "user", text: value, createdAt: Date.now() };
    const assistantId = `assistant-${Date.now()}`;

    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantId, side: "assistant", text: "", createdAt: Date.now() + 1, streaming: true },
    ]);
    setInput("");
    setActivity("Thinking");
    setApiError("");
    setIsChatLoading(true);
    setSurfaceTab("chat");
    setLastPrompt(value);

    try {
      const response = await fetch(`${CHAT_API_BASE}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: value, session_id: currentSessionId || undefined }),
      });

      if (!response.ok || !response.body) {
        let errorMessage = "Assistant API unavailable.";
        try {
          const payload = await response.json();
          errorMessage = payload?.detail || payload?.error || errorMessage;
        } catch (_error) {
          // Ignore JSON parsing failures for non-JSON error responses.
        }
        throw new Error(errorMessage);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value: chunk, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(chunk, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventBlock of events) {
          const line = eventBlock
            .split("\n")
            .find((entry) => entry.startsWith("data: "));
          if (!line) continue;

          const payload = JSON.parse(line.slice(6));
          if (payload.type === "chunk") {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? { ...message, text: `${message.text}${payload.content}`, streaming: true }
                  : message,
              ),
            );
            continue;
          }

          if (payload.type === "done") {
            if (payload.message?.confirmation_id) {
              setPendingConfirmation({
                confirmationId: payload.message.confirmation_id,
                command: payload.message?.tool?.command || payload.message?.text || "",
              });
            }
            if (payload.session?.id) {
              setCurrentSessionId(payload.session.id);
              setChatSessions((current) => {
                const title = payload.session.title || value.slice(0, 48);
                const next = current.filter((item) => item.id !== payload.session.id);
                return [{ id: payload.session.id, title, message_count: 0 }, ...next];
              });
            }
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      text: payload.message?.content || message.text,
                      createdAt: payload.message?.created_at
                        ? Date.parse(payload.message.created_at)
                        : message.createdAt,
                      streaming: false,
                    }
                  : message,
              ),
            );
            continue;
          }

          if (payload.type === "error") {
            throw new Error(payload.error || "Streaming failed.");
          }
          if (payload.type === "cancelled") {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId ? { ...message, text: "Response cancelled.", streaming: false } : message,
              ),
            );
          }
        }
      }
    } catch (error) {
      const messageText = error.message || "Assistant API unavailable.";
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? { ...message, text: messageText, streaming: false }
            : message,
        ),
      );
      setApiError(messageText);
    } finally {
      setIsChatLoading(false);
      setActivity(mode === "voice" ? "Listening" : "Ready");
    }
  };

  const handleModeChange = async (nextMode) => {
    setMode(nextMode);
    if (nextMode === "voice") {
      try {
        const response = await fetch(`${API_BASE}/api/voice/start`, { method: "POST" });
        const payload = await response.json();
        if (payload?.ok && payload.voice) {
          setVoiceStatus(payload.voice);
          setApiError("");
        }
      } catch (_error) {
        setApiError("Could not start voice mode.");
      }
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/voice/stop`, { method: "POST" });
      const payload = await response.json();
      if (payload?.ok && payload.voice) {
        setVoiceStatus(payload.voice);
      }
      setApiError("");
    } catch (_error) {
      setApiError("Could not switch back to text mode cleanly.");
    }
  };

  const updateStartupSettings = async (changes) => {
    try {
      const response = await fetch(`${API_BASE}/api/settings/startup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          auto_launch_enabled:
            Object.prototype.hasOwnProperty.call(changes, "auto_launch_enabled")
              ? changes.auto_launch_enabled
              : startupState.auto_launch_enabled,
          tray_mode:
            Object.prototype.hasOwnProperty.call(changes, "tray_mode")
              ? changes.tray_mode
              : startupState.tray_mode,
        }),
      });
      const payload = await response.json();
      if (!payload?.ok) {
        throw new Error(payload?.error || "Startup update failed.");
      }
      if (payload.startup) {
        setStartupState(payload.startup);
      }
      if (payload.message) {
        setMessages((current) => [
          ...current,
        {
          id: `startup-${Date.now()}`,
          side: "assistant",
          text: `Grandpa : ${payload.message}`,
          createdAt: Date.now(),
        },
      ]);
      }
      setApiError("");
    } catch (error) {
      setApiError(error.message || "Could not update startup settings.");
    }
  };

  const runPortableSetup = async (action) => {
    try {
      const response = await fetch(`${API_BASE}/api/settings/portable-setup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ action }),
      });
      const payload = await response.json();
      if (!payload?.ok) {
        throw new Error(payload?.error || "Portable setup failed.");
      }
      if (payload.startup) {
        setStartupState(payload.startup);
      }
      setMessages((current) => [
        ...current,
        {
          id: `portable-${Date.now()}`,
          side: "assistant",
          text: `Grandpa : ${payload.message}`,
          createdAt: Date.now(),
        },
      ]);
      setApiError("");
    } catch (error) {
      setApiError(error.message || "Could not run portable setup.");
    }
  };

  const statusItems = useMemo(
    () => [
      { label: "Weather", value: uiState.overview.weather },
      { label: "Health", value: uiState.overview.health },
      { label: "Vision", value: uiState.overview.object_detection },
    ],
    [uiState],
  );

  const recentCommands = uiState.recent_commands || [];
  const quickSuggestions = useMemo(
    () => [
      "plan my day",
      "what should i do now",
      "weather",
      "latest note",
      "today events",
      "voice status",
      "voice diagnostics",
      "smart home status",
      "face security status",
      "what objects do you see",
      "detect objects on screen",
      ...(recentCommands.slice(0, 2) || []),
    ].filter((item, index, array) => item && array.indexOf(item) === index).slice(0, 8),
    [recentCommands],
  );
  const liveSuggestions = useMemo(() => {
    const commandPool = [
      ...quickSuggestions,
      "open chrome",
      "plan my day",
      "what should i do now",
      "add note ",
      "add task ",
      "latest note",
      "today events",
      "weather",
      "voice status",
      "voice diagnostics",
      "show settings",
    ];
    return commandPool
      .filter((item, index, array) => item && array.indexOf(item) === index)
      .filter((item) => matchesCommand(item, input))
      .slice(0, 5);
  }, [input, quickSuggestions]);
  const filteredMessages = useMemo(() => {
    const query = chatSearch.trim().toLowerCase();
    if (!query) return messages;
    return messages.filter((message) => normalizeMessageText(message.text).toLowerCase().includes(query));
  }, [chatSearch, messages]);
  const filteredContacts = useMemo(() => {
    const preview = uiState.contacts.preview || [];
    const query = contactSearch.trim().toLowerCase();
    if (!query) return preview.slice(0, 6);
    return preview.filter((item) => item.toLowerCase().includes(query)).slice(0, 6);
  }, [contactSearch, uiState.contacts.preview]);
  const activeContact = selectedContact || contactSearch.trim() || uiState.contacts.favorite_contact;
  const selectedPlannerLabel = selectedPlanner.text ? `${selectedPlanner.type}: ${selectedPlanner.text}` : "Nothing selected";
  const memoryItems = [
    `Preferred language: ${uiState.memory.preferred_language}`,
    `Favorite contact: ${uiState.memory.favorite_contact}`,
    `Mode: ${mode === "voice" ? "Voice" : "Text"}`,
    `Focus mode: ${uiState.settings.focus_mode ? "On" : "Off"}`,
  ];
  const workspaceTabs = ["planner", "calendar", "notes", "assistant", "settings"];
  const navItems = [
    { id: "planner", label: "Planner", hint: "tasks and reminders" },
    { id: "calendar", label: "Calendar", hint: "events and sync" },
    { id: "notes", label: "Notes", hint: "capture and search" },
    { id: "assistant", label: "Assistant", hint: "voice, proactive, security" },
    { id: "settings", label: "Settings", hint: "voice and startup" },
  ];
  const surfaceTabs = [
    { id: "chat", label: "Chat" },
    { id: "dashboard", label: "Dashboard" },
  ];

  const formatTime = now.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });

  const formatDate = now.toLocaleDateString("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const plannerActions = [
    {
      label: "Add Task",
      action: async () => {
        if (!taskInput.trim()) return;
        await runCommand(`add task ${taskInput}`);
        setTaskInput("");
      },
    },
    {
      label: "Add Reminder",
      action: async () => {
        if (!reminderText.trim()) return;
        await runCommand(`remind me to ${reminderText} ${reminderWhen}`.trim());
      },
    },
    {
      label: "Add Event",
      action: async () => {
        if (!eventText.trim()) return;
        await runCommand(`add event ${eventText} ${eventWhen}`.trim());
      },
    },
  ];

  const focusPlannerSection = (section, itemText) => {
    const cleaned = cleanPlannerItem(itemText);
    setWorkspaceTab("planner");
    setSelectedPlanner({ type: section, text: cleaned });

    if (section === "task") {
      setTaskInput(cleaned);
      setTaskTitleInput(cleaned);
      return;
    }

    if (section === "reminder") {
      setReminderText(cleaned);
      setReminderTitleInput(cleaned);
      return;
    }

    if (section === "event") {
      setEventText(cleaned);
      setEventTitleInput(cleaned);
    }
  };

  const selectContact = (value) => {
    setSelectedContact(value);
    setContactAliasTarget(value);
  };

  const taskQuickActions = [
    { label: "Latest Task", command: "latest task" },
    { label: "Complete Latest", command: "complete latest task" },
    { label: "Delete Latest", command: "delete latest task" },
    { label: "Clear Done", command: "delete completed tasks" },
  ];

  const reminderQuickActions = [
    { label: "Latest Reminder", command: "latest reminder" },
    { label: "Delete Latest", command: "delete latest reminder" },
    { label: "Due Today", command: "what is due today" },
    { label: "Overdue", command: "show overdue items" },
  ];

  const eventQuickActions = [
    { label: "Latest Event", command: "latest event" },
    { label: "Upcoming", command: "upcoming events" },
    { label: "Delete Latest", command: "delete latest event" },
    { label: "Today Events", command: "today events" },
  ];
  const showAutocomplete = mode === "text" && input.trim().length > 0 && liveSuggestions.length > 0;

  const applySuggestion = (value) => {
    setInput(value);
    setActiveSuggestionIndex(0);
  };

  const pinCommand = (value) => {
    const cleaned = String(value || "").trim();
    if (!cleaned) return;
    setPinnedCommands((current) => [cleaned, ...current.filter((item) => item !== cleaned)].slice(0, 6));
  };

  const clearConversation = () => {
    setMessages([]);
    setAttachedDocuments([]);
    setApiError("");
    fetch(`${CHAT_API_BASE}/chat/reset${currentSessionId ? `?session_id=${encodeURIComponent(currentSessionId)}` : ""}`, {
      method: "POST",
    }).catch(() => {});
  };

  const uploadChatDocument = async (file) => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    if (currentSessionId) {
      formData.append("session_id", currentSessionId);
    }

    try {
      setApiError("");
      const response = await fetch(`${CHAT_API_BASE}/chat/upload`, {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!payload?.ok) {
        throw new Error(payload?.detail || "Could not upload document.");
      }
      if (payload.session?.id) {
        setCurrentSessionId(payload.session.id);
      }
      setChatSessions(payload.sessions || []);
      setAttachedDocuments(mapSessionDocuments(payload.documents));
      setMessages((current) => [
        ...current,
        {
          id: `upload-${Date.now()}`,
          side: "assistant",
          text: `Grandpa : Uploaded ${payload.document?.name || file.name}. I can answer questions from it now.`,
          createdAt: Date.now(),
        },
      ]);
    } catch (error) {
      setApiError(error.message || "Could not upload document.");
    }
  };

  const removeChatDocument = async (filename) => {
    if (!currentSessionId || !filename) return;
    try {
      setApiError("");
      const response = await fetch(`${CHAT_API_BASE}/chat/upload/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: currentSessionId, filename }),
      });
      const payload = await response.json();
      if (!payload?.ok) {
        throw new Error(payload?.detail || "Could not remove document.");
      }
      setAttachedDocuments(mapSessionDocuments(payload.documents));
      setMessages((current) => [
        ...current,
        {
          id: `remove-${Date.now()}`,
          side: "assistant",
          text: `Grandpa : Removed document ${filename}.`,
          createdAt: Date.now(),
        },
      ]);
    } catch (error) {
      setApiError(error.message || "Could not remove document.");
    }
  };

  const reloadWorkspace = async () => {
    try {
      const [uiResponse, historyResponse, sessionsResponse, settingsResponse] = await Promise.all([
        fetch(`${API_BASE}/api/ui-state`),
        fetch(`${CHAT_API_BASE}/chat/history${currentSessionId ? `?session_id=${encodeURIComponent(currentSessionId)}` : ""}`),
        fetch(`${CHAT_API_BASE}/chat/sessions`),
        fetch(`${CHAT_API_BASE}/chat/settings`),
      ]);
      const uiPayload = await uiResponse.json();
      const historyPayload = await historyResponse.json();
      const sessionsPayload = await sessionsResponse.json();
      const settingsPayload = await settingsResponse.json();
      if (uiPayload?.ok && uiPayload.state) {
        setUiState(uiPayload.state);
        if (uiPayload.state.voice) {
          setVoiceStatus(uiPayload.state.voice);
        }
        if (uiPayload.state.startup) {
          setStartupState(uiPayload.state.startup);
        }
      }
      if (historyPayload?.ok) {
        setMessages(mapHistoryMessages(historyPayload.messages));
        if (historyPayload.session?.id) {
          setCurrentSessionId(historyPayload.session.id);
        }
        setAttachedDocuments(mapSessionDocuments(historyPayload.session?.documents));
      }
      if (sessionsPayload?.ok) {
        setChatSessions(sessionsPayload.sessions || []);
      }
      if (settingsPayload?.ok && settingsPayload.settings) {
        setChatSettings(settingsPayload.settings);
        setChatSettingsDraft(settingsPayload.settings);
      }
      setApiError("");
    } catch (_error) {
      setApiError("Python assistant API is not reachable yet.");
    }
  };

  const createSession = async () => {
    try {
      const response = await fetch(`${CHAT_API_BASE}/chat/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New chat" }),
      });
      const payload = await response.json();
      if (!payload?.ok) {
        throw new Error(payload?.detail || "Could not create chat.");
      }
      setCurrentSessionId(payload.session.id);
      setChatSessions(payload.sessions || []);
      setLastPrompt("");
      setMessages([]);
      setAttachedDocuments([]);
      setApiError("");
      setSurfaceTab("chat");
    } catch (error) {
      setApiError(error.message || "Could not create chat.");
    }
  };

  const switchSession = async (sessionId) => {
    try {
      const response = await fetch(`${CHAT_API_BASE}/chat/history?session_id=${encodeURIComponent(sessionId)}`);
      const payload = await response.json();
      if (!payload?.ok) {
        throw new Error(payload?.detail || "Could not switch chat.");
      }
      setCurrentSessionId(sessionId);
      setLastPrompt("");
      setMessages(mapHistoryMessages(payload.messages));
      setAttachedDocuments(mapSessionDocuments(payload.session?.documents));
      setApiError("");
      setSurfaceTab("chat");
    } catch (error) {
      setApiError(error.message || "Could not switch chat.");
    }
  };

  const saveChatSettings = async () => {
    try {
      const response = await fetch(`${CHAT_API_BASE}/chat/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(chatSettingsDraft),
      });
      const payload = await response.json();
      if (!payload?.ok) {
        throw new Error(payload?.detail || "Could not save chat settings.");
      }
      setChatSettings(payload.settings);
      setChatSettingsDraft(payload.settings);
      setApiError("");
      setShowChatSettings(false);
    } catch (error) {
      setApiError(error.message || "Could not save chat settings.");
    }
  };

  const regenerateReply = async () => {
    if (!currentSessionId || isChatLoading) return;
    try {
      setIsChatLoading(true);
      const response = await fetch(`${CHAT_API_BASE}/chat/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: currentSessionId }),
      });
      const payload = await response.json();
      if (!payload?.ok) {
        throw new Error(payload?.detail || "Could not regenerate reply.");
      }
      setMessages(mapHistoryMessages(payload.session?.messages || []));
      setApiError("");
    } catch (error) {
      setApiError(error.message || "Could not regenerate reply.");
    } finally {
      setIsChatLoading(false);
    }
  };

  const cancelStreaming = async () => {
    if (!currentSessionId || !isChatLoading) return;
    try {
      await fetch(`${CHAT_API_BASE}/chat/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: currentSessionId }),
      });
    } catch (_error) {
      setApiError("Could not cancel the current response.");
    }
  };

  const retryLastPrompt = async () => {
    if (!lastPrompt || isChatLoading) return;
    await handleSend(lastPrompt);
  };

  const confirmPendingAction = async () => {
    if (!pendingConfirmation?.confirmationId) return;
    const confirmation = pendingConfirmation;
    setPendingConfirmation(null);
    try {
      const response = await fetch(`${API_BASE}/api/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          command: confirmation.command,
          confirmation_id: confirmation.confirmationId,
        }),
      });
      const payload = await response.json();
      if (!payload?.ok) {
        throw new Error(payload?.detail || payload?.error || "Confirmation failed.");
      }
      const replies = (payload.messages || []).map((text, index) => ({
        id: `confirm-${Date.now()}-${index}`,
        side: "assistant",
        text,
        createdAt: Date.now() + index,
      }));
      setMessages((current) => [...current, ...replies]);
      if (payload.state) {
        setUiState(payload.state);
      }
      setApiError("");
    } catch (error) {
      setApiError(error.message || "Could not confirm action.");
    }
  };

  const renameSession = async (session) => {
    const nextTitle = window.prompt("Rename chat", session?.title || "New chat");
    if (!nextTitle || !nextTitle.trim()) return;
    try {
      const response = await fetch(`${CHAT_API_BASE}/chat/sessions/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: session.id, title: nextTitle.trim() }),
      });
      const payload = await response.json();
      if (!payload?.ok) {
        throw new Error(payload?.detail || "Could not rename chat.");
      }
      setChatSessions(payload.sessions || []);
      setApiError("");
    } catch (error) {
      setApiError(error.message || "Could not rename chat.");
    }
  };

  const deleteSession = async (sessionId) => {
    const confirmed = window.confirm("Delete this chat?");
    if (!confirmed) return;
    try {
      const response = await fetch(`${CHAT_API_BASE}/chat/sessions/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const payload = await response.json();
      if (!payload?.ok) {
        throw new Error(payload?.detail || "Could not delete chat.");
      }
      setChatSessions(payload.sessions || []);
      setCurrentSessionId(payload.current_session_id || "");
      if (payload.current_session_id) {
        await switchSession(payload.current_session_id);
      } else {
        setMessages([]);
      }
      setApiError("");
    } catch (error) {
      setApiError(error.message || "Could not delete chat.");
    }
  };

  const exportSession = async () => {
    if (!currentSessionId) return;
    try {
      const response = await fetch(`${CHAT_API_BASE}/chat/export?session_id=${encodeURIComponent(currentSessionId)}`);
      const payload = await response.json();
      if (!payload?.ok) {
        throw new Error(payload?.detail || "Could not export chat.");
      }
      const blob = new Blob([payload.content || ""], { type: "text/markdown;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = payload.filename || "chat.md";
      link.click();
      window.URL.revokeObjectURL(url);
      setApiError("");
    } catch (error) {
      setApiError(error.message || "Could not export chat.");
    }
  };

  return (
    <div className="app-shell">
      {voiceToast ? (
        <div className={`voice-toast ${voiceToast.state || "neutral"}`}>
          <strong>{voiceToast.title}</strong>
          <span>{voiceToast.text}</span>
        </div>
      ) : null}
      <header className="top-bar">
        <div className="brand-wrap">
          <LogoMark />
          <div className="brand-copy">
            <div className="title-row">
              <h1>Grandpa Assistant</h1>
              <div className="mode-switch" role="tablist" aria-label="Mode">
                <button
                  className={mode === "text" ? "active text" : "text"}
                  onClick={() => handleModeChange("text")}
                >
                  Text
                </button>
                <button
                  className={mode === "voice" ? "active voice" : "voice"}
                  onClick={() => handleModeChange("voice")}
                >
                  Voice
                </button>
              </div>
            </div>
            <div className="activity-row">
              <span className={`orb ${activity.toLowerCase()}`} />
              <span>{activity}</span>
              {mode === "voice" && voiceStatus.transcript ? (
                <small className="activity-detail">{voiceStatus.transcript}</small>
              ) : null}
            </div>
          </div>
        </div>
        <div className="clock-wrap">
          <strong>{formatTime}</strong>
          <span>{formatDate}</span>
        </div>
      </header>

      <main className="layout-grid">
        <SidebarPanels
          navItems={navItems}
          workspaceTab={workspaceTab}
          setWorkspaceTab={setWorkspaceTab}
          statusItems={statusItems}
          quickSuggestions={quickSuggestions}
          pinnedCommands={pinnedCommands}
          runCommand={runCommand}
          uiState={uiState}
          focusPlannerSection={focusPlannerSection}
          memoryItems={memoryItems}
          contactSearch={contactSearch}
          setContactSearch={setContactSearch}
          filteredContacts={filteredContacts}
          selectedContact={selectedContact}
          selectContact={selectContact}
          activeContact={activeContact}
          contactAlias={contactAlias}
          setContactAlias={setContactAlias}
          contactAliasTarget={contactAliasTarget}
          setContactAliasTarget={setContactAliasTarget}
          startupState={startupState}
          updateStartupSettings={updateStartupSettings}
        />
{/*
          <SectionCard title="Workspace">
            <div className="nav-stack">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  className={workspaceTab === item.id ? "nav-card active" : "nav-card"}
                  onClick={() => setWorkspaceTab(item.id)}
                >
                  <strong>{item.label}</strong>
                  <span>{item.hint}</span>
                </button>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Overview">
            <ul className="status-list">
              {statusItems.map((item) => (
                <li key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </li>
              ))}
            </ul>
          </SectionCard>

          <SectionCard title="Quick Actions">
            <div className="command-chips">
              {quickSuggestions.map((item) => (
                <button key={item} className="chip-button" onClick={() => runCommand(item)}>
                  {item}
                </button>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Pinned">
            <div className="command-chips">
              {pinnedCommands.map((item) => (
                <button key={`pinned-${item}`} className="chip-button" onClick={() => runCommand(item)}>
                  {item}
                </button>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Today">
            <p>{uiState.today}</p>
          </SectionCard>

          <SectionCard title="Next Event">
            <p>{uiState.next_event}</p>
          </SectionCard>

          <SectionCard title="Latest Note">
            <p>{uiState.latest_note}</p>
          </SectionCard>

          <SectionCard title="Planner">
            <div className="dashboard-group">
              <div>
                <h4>Tasks</h4>
                <ul className="mini-list">
                  {(uiState.dashboard.tasks || []).map((item) => (
                    <li key={`task-${item}`}>
                      <button className="inline-select" onClick={() => focusPlannerSection("task", item)}>
                        {item}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4>Reminders</h4>
                <ul className="mini-list">
                  {(uiState.dashboard.reminders || []).map((item) => (
                    <li key={`reminder-${item}`}>
                      <button className="inline-select" onClick={() => focusPlannerSection("reminder", item)}>
                        {item}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4>Events</h4>
                <ul className="mini-list">
                  {(uiState.dashboard.events || []).map((item) => (
                    <li key={`event-${item}`}>
                      <button className="inline-select" onClick={() => focusPlannerSection("event", item)}>
                        {item}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Notifications">
            {uiState.notifications?.length ? (
              <ul className="notification-list">
                {uiState.notifications.map((item, index) => (
                  <li key={`${item.level}-${index}`} className={`notification-item ${item.level || "neutral"}`}>
                    {item.text}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No active notifications.</p>
            )}
          </SectionCard>

          <SectionCard title="Memory">
            <ul className="mini-list">
              {memoryItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </SectionCard>

          <SectionCard title="Settings">
            <ul className="mini-list">
              <li>{`Wake word: ${uiState.settings.wake_word}`}</li>
              <li>{`Voice profile: ${uiState.settings.voice_profile}`}</li>
              <li>{`Offline mode: ${uiState.settings.offline_mode ? "On" : "Off"}`}</li>
              <li>{`Developer mode: ${uiState.settings.developer_mode ? "On" : "Off"}`}</li>
              <li>{`Emergency mode: ${uiState.settings.emergency_mode ? "On" : "Off"}`}</li>
            </ul>
            <div className="action-grid">
              <button className="action-button" onClick={() => runCommand("show settings")}>Show Settings</button>
              <button className="action-button" onClick={() => runCommand(uiState.settings.offline_mode ? "disable offline mode" : "enable offline mode")}>
                {uiState.settings.offline_mode ? "Disable Offline" : "Enable Offline"}
              </button>
              <button className="action-button" onClick={() => runCommand(uiState.settings.developer_mode ? "disable developer mode" : "enable developer mode")}>
                {uiState.settings.developer_mode ? "Disable Dev" : "Enable Dev"}
              </button>
            </div>
          </SectionCard>

          <SectionCard title="Contacts">
            <p>{`Favorite: ${uiState.contacts.favorite_contact}`}</p>
            <p>{uiState.contacts.recent_changes || "No recent contact changes."}</p>
            <div className="stack-form compact-gap">
              <input
                value={contactSearch}
                onChange={(event) => setContactSearch(event.target.value)}
                placeholder="Search contact..."
              />
            </div>
            {filteredContacts.length ? (
              <div className="command-chips contact-chip-wrap">
                {filteredContacts.map((item) => (
                  <button
                    key={`contact-${item}`}
                    className={selectedContact === item ? "chip-button active-chip" : "chip-button"}
                    onClick={() => selectContact(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            ) : (
              <p>No matching contacts.</p>
            )}
            <p className="contact-active-line">{`Active: ${activeContact || "None selected"}`}</p>
            <div className="action-grid">
              <button
                className="action-button"
                onClick={() => activeContact ? runCommand(`call ${activeContact}`) : null}
              >
                Call Contact
              </button>
              <button
                className="action-button"
                onClick={() => activeContact ? runCommand(`message to ${activeContact} saying hi`) : null}
              >
                Message Contact
              </button>
              <button
                className="action-button"
                onClick={() => activeContact ? runCommand(`mail ${activeContact} about today plan`) : null}
              >
                Mail Contact
              </button>
              <button
                className="action-button"
                onClick={() => activeContact ? runCommand(`favorite contact ${activeContact}`) : null}
              >
                Favorite Contact
              </button>
              <button
                className="action-button"
                onClick={() => activeContact ? runCommand(`unfavorite contact ${activeContact}`) : null}
              >
                Unfavorite Contact
              </button>
              <button className="action-button" onClick={() => runCommand("sync google contacts")}>
                Sync Contacts
              </button>
              <button className="action-button" onClick={() => runCommand("show google contact changes")}>
                Contact Changes
              </button>
            </div>
            <div className="stack-form compact-gap">
              <input
                value={contactAlias}
                onChange={(event) => setContactAlias(event.target.value)}
                placeholder="Alias (appa, bro...)"
              />
              <input
                value={contactAliasTarget}
                onChange={(event) => setContactAliasTarget(event.target.value)}
                placeholder="Exact contact name"
              />
              <button
                onClick={() =>
                  contactAlias.trim() && contactAliasTarget.trim()
                    ? runCommand(`set contact alias ${contactAlias} to ${contactAliasTarget}`.trim())
                    : null
                }
              >
                Save Alias
              </button>
              <button
                onClick={() =>
                  contactAlias.trim()
                    ? runCommand(`remove contact alias ${contactAlias}`.trim())
                    : null
                }
              >
                Remove Alias
              </button>
            </div>
            <ul className="mini-list compact-list">
              <li>{uiState.contacts.aliases_summary}</li>
              <li>{uiState.contacts.favorites_summary}</li>
            </ul>
          </SectionCard>

          <SectionCard title="Emergency">
            <ul className="mini-list">
              <li>{`Emergency contact: ${uiState.emergency.contact}`}</li>
              <li>{`Saved location: ${uiState.emergency.location}`}</li>
              <li>{`Mode: ${uiState.emergency.mode_enabled ? "Enabled" : "Disabled"}`}</li>
              <li>{uiState.emergency.protocol_summary}</li>
            </ul>
            <div className="action-grid">
              <button className="action-button danger" onClick={() => runCommand("start emergency protocol")}>Start Protocol</button>
              <button className="action-button danger" onClick={() => runCommand("send emergency alert")}>Send Alert</button>
              <button className="action-button" onClick={() => runCommand("send i am safe alert")}>I'm Safe</button>
              <button className="action-button" onClick={() => runCommand("share my location everywhere")}>Share Location</button>
              <button className="action-button" onClick={() => runCommand(uiState.emergency.mode_enabled ? "disable emergency mode" : "enable emergency mode")}>
                {uiState.emergency.mode_enabled ? "Disable Emergency" : "Enable Emergency"}
              </button>
              <button className="action-button" onClick={() => runCommand("emergency protocol status")}>Protocol Status</button>
            </div>
          </SectionCard>

          <SectionCard title="Startup">
            <p>{startupState.summary}</p>
            <ul className="mini-list compact-list">
              <li>{`React on tray: ${startupState.react_ui_on_tray_enabled ? "Enabled" : "Disabled"}`}</li>
              <li>{`Tray mode target: ${startupState.react_ui_on_tray_mode || "browser"}`}</li>
              <li>{`Browser launcher: ${startupState.react_frontend_ready ? "Ready" : "Missing"}`}</li>
              <li>{`Desktop launcher: ${startupState.react_desktop_ready ? "Ready" : "Missing"}`}</li>
            </ul>
            <div className="startup-actions">
              <button
                className={startupState.auto_launch_enabled ? "soft danger" : "soft success"}
                onClick={() =>
                  updateStartupSettings({
                    auto_launch_enabled: !startupState.auto_launch_enabled,
                  })
                }
              >
                {startupState.auto_launch_enabled ? "Disable Auto Launch" : "Enable Auto Launch"}
              </button>
              <button
                className={startupState.tray_mode ? "soft active" : "soft"}
                onClick={() =>
                  updateStartupSettings({
                    tray_mode: !startupState.tray_mode,
                  })
                }
              >
                {startupState.tray_mode ? "Tray Startup On" : "Tray Startup Off"}
              </button>
              <button className="soft" onClick={() => runCommand("open react ui")}>
                Open React Browser UI
              </button>
              <button className="soft" onClick={() => runCommand("open react desktop")}>
                Open React Desktop UI
              </button>
            </div>
          </SectionCard>
        </aside>
*/}

        <section className="chat-panel">
          <div className="chat-panel-head">
            <div className="chat-panel-heading">
              <div>
                <h2>Conversation</h2>
                <p>{mode === "voice" ? "Speak naturally. Voice replies stay active." : "Type a command and press Run."}</p>
              </div>
              <div className="panel-tools">
                <div className="surface-tabs" role="tablist" aria-label="Surface">
                  {surfaceTabs.map((item) => (
                    <button
                      key={item.id}
                      className={surfaceTab === item.id ? "active" : ""}
                      onClick={() => setSurfaceTab(item.id)}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
                <button className="ghost-button" onClick={reloadWorkspace}>Reload</button>
                <button className="ghost-button danger" onClick={clearConversation}>Clear Chat</button>
              </div>
            </div>
            {apiError ? <div className="panel-alert">{apiError}</div> : null}
          </div>

          {surfaceTab === "dashboard" ? (
            <DashboardSurface
              uiState={uiState}
              quickSuggestions={quickSuggestions}
              runCommand={runCommand}
              setSurfaceTab={setSurfaceTab}
              setWorkspaceTab={setWorkspaceTab}
              focusPlannerSection={focusPlannerSection}
              mode={mode}
              voiceStatus={voiceStatus}
              activity={activity}
              handleModeChange={handleModeChange}
            />
          ) : (
            <>
              <div className="workspace-panel">
                <div className="workspace-tabs">
                  {workspaceTabs.map((tab) => (
                    <button
                      key={tab}
                      className={workspaceTab === tab ? "active" : ""}
                      onClick={() => setWorkspaceTab(tab)}
                    >
                      {tab === "planner"
                        ? "Planner"
                        : tab === "calendar"
                          ? "Calendar"
                          : tab === "notes"
                            ? "Notes"
                            : "Settings"}
                    </button>
                  ))}
                </div>

                {workspaceTab === "planner" ? (
                  <div className="workspace-grid">
                <div className="workspace-card planner-focus-card">
                  <h3>Selected Item</h3>
                  <p>{selectedPlannerLabel}</p>
                  <div className="action-grid compact two-col">
                    <button
                      className="action-button"
                      onClick={() =>
                        selectedPlanner.type === "task" && selectedPlanner.text
                          ? runCommand(`complete task titled ${selectedPlanner.text}`)
                          : null
                      }
                    >
                      Complete Selected
                    </button>
                    <button
                      className="action-button"
                      onClick={() =>
                        selectedPlanner.type === "task" && selectedPlanner.text
                          ? runCommand(`delete task titled ${selectedPlanner.text}`)
                          : null
                      }
                    >
                      Delete Selected
                    </button>
                    <button
                      className="action-button"
                      onClick={() =>
                        selectedPlanner.type === "reminder" && selectedPlanner.text
                          ? runCommand(`reschedule reminder about ${selectedPlanner.text} to ${reminderRescheduleInput}`.trim())
                          : null
                      }
                    >
                      Move Reminder
                    </button>
                    <button
                      className="action-button"
                      onClick={() =>
                        selectedPlanner.type === "reminder" && selectedPlanner.text
                          ? runCommand(`delete reminder about ${selectedPlanner.text}`.trim())
                          : null
                      }
                    >
                      Delete Reminder
                    </button>
                    <button
                      className="action-button"
                      onClick={() =>
                        selectedPlanner.type === "event" && selectedPlanner.text
                          ? runCommand(`reschedule event about ${selectedPlanner.text} to ${eventRescheduleInput}`.trim())
                          : null
                      }
                    >
                      Move Event
                    </button>
                    <button
                      className="action-button"
                      onClick={() =>
                        selectedPlanner.type === "event" && selectedPlanner.text
                          ? runCommand(`delete event about ${selectedPlanner.text}`.trim())
                          : null
                      }
                    >
                      Delete Event
                    </button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Tasks</h3>
                  <div className="inline-form">
                    <input
                      value={taskInput}
                      onChange={(event) => setTaskInput(event.target.value)}
                      placeholder="Finish resume"
                    />
                    <button onClick={plannerActions[0].action}>Add Task</button>
                  </div>
                  <div className="action-grid compact two-col">
                    {taskQuickActions.map((item) => (
                      <button key={item.label} className="action-button" onClick={() => runCommand(item.command)}>
                        {item.label}
                      </button>
                    ))}
                  </div>
                  <div className="stack-form compact-gap">
                    <input
                      value={taskTitleInput}
                      onChange={(event) => setTaskTitleInput(event.target.value)}
                      placeholder="Task title..."
                    />
                    <button
                      onClick={() =>
                        taskTitleInput.trim()
                          ? runCommand(`complete task titled ${taskTitleInput}`.trim())
                          : null
                      }
                    >
                      Complete By Title
                    </button>
                    <button
                      onClick={() =>
                        taskTitleInput.trim()
                          ? runCommand(`delete task titled ${taskTitleInput}`.trim())
                          : null
                      }
                    >
                      Delete By Title
                    </button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Reminders</h3>
                  <div className="stack-form">
                    <input
                      value={reminderText}
                      onChange={(event) => setReminderText(event.target.value)}
                      placeholder="Submit form"
                    />
                    <input
                      value={reminderWhen}
                      onChange={(event) => setReminderWhen(event.target.value)}
                      placeholder="tomorrow at 8 pm"
                    />
                    <button onClick={plannerActions[1].action}>Add Reminder</button>
                  </div>
                  <div className="action-grid compact two-col">
                    {reminderQuickActions.map((item) => (
                      <button key={item.label} className="action-button" onClick={() => runCommand(item.command)}>
                        {item.label}
                      </button>
                    ))}
                  </div>
                  <div className="stack-form compact-gap">
                    <input
                      value={reminderTitleInput}
                      onChange={(event) => setReminderTitleInput(event.target.value)}
                      placeholder="Reminder title..."
                    />
                    <input
                      value={reminderRescheduleInput}
                      onChange={(event) => setReminderRescheduleInput(event.target.value)}
                      placeholder="tomorrow at 8 pm"
                    />
                    <button
                      onClick={() =>
                        reminderTitleInput.trim() && reminderRescheduleInput.trim()
                          ? runCommand(`reschedule reminder about ${reminderTitleInput} to ${reminderRescheduleInput}`.trim())
                          : null
                      }
                    >
                      Reschedule By Title
                    </button>
                    <button
                      onClick={() =>
                        reminderTitleInput.trim()
                          ? runCommand(`delete reminder about ${reminderTitleInput}`.trim())
                          : null
                      }
                    >
                      Delete By Title
                    </button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Events</h3>
                  <div className="stack-form">
                    <input
                      value={eventText}
                      onChange={(event) => setEventText(event.target.value)}
                      placeholder="Team sync"
                    />
                    <input
                      value={eventWhen}
                      onChange={(event) => setEventWhen(event.target.value)}
                      placeholder="tomorrow at 6 pm"
                    />
                    <button onClick={plannerActions[2].action}>Add Event</button>
                  </div>
                  <div className="action-grid compact two-col">
                    {eventQuickActions.map((item) => (
                      <button key={item.label} className="action-button" onClick={() => runCommand(item.command)}>
                        {item.label}
                      </button>
                    ))}
                  </div>
                  <div className="stack-form compact-gap">
                    <input
                      value={eventTitleInput}
                      onChange={(event) => setEventTitleInput(event.target.value)}
                      placeholder="Event title..."
                    />
                    <input
                      value={eventRescheduleInput}
                      onChange={(event) => setEventRescheduleInput(event.target.value)}
                      placeholder="tomorrow at 6 pm"
                    />
                    <button
                      onClick={() =>
                        eventTitleInput.trim() && eventRescheduleInput.trim()
                          ? runCommand(`reschedule event about ${eventTitleInput} to ${eventRescheduleInput}`.trim())
                          : null
                      }
                    >
                      Reschedule By Title
                    </button>
                    <button
                      onClick={() =>
                        eventTitleInput.trim()
                          ? runCommand(`delete event about ${eventTitleInput}`.trim())
                          : null
                      }
                    >
                      Delete By Title
                    </button>
                  </div>
                </div>
                  </div>
                ) : null}

                {workspaceTab === "calendar" ? (
                  <div className="workspace-grid">
                <div className="workspace-card">
                  <h3>Google Calendar</h3>
                  <div className="action-grid compact">
                    <button className="action-button" onClick={() => runCommand("google calendar status")}>Status</button>
                    <button className="action-button" onClick={() => runCommand("sync google calendar")}>Sync</button>
                    <button className="action-button" onClick={() => runCommand("today in google calendar")}>Today</button>
                    <button className="action-button" onClick={() => runCommand("upcoming google calendar events")}>Upcoming</button>
                    <button className="action-button" onClick={() => runCommand("list google calendar event titles")}>Titles</button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Add Event</h3>
                  <div className="stack-form">
                    <input
                      value={calendarTitle}
                      onChange={(event) => setCalendarTitle(event.target.value)}
                      placeholder="Client sync"
                    />
                    <input
                      value={calendarWhen}
                      onChange={(event) => setCalendarWhen(event.target.value)}
                      placeholder="tomorrow at 6 pm"
                    />
                    <button
                      onClick={() =>
                        calendarTitle.trim() ? runCommand(`add google calendar event ${calendarTitle} ${calendarWhen}`.trim()) : null
                      }
                    >
                      Add Google Event
                    </button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Latest Event</h3>
                  <div className="action-grid compact">
                    <button className="action-button" onClick={() => runCommand("delete latest google calendar event")}>Delete Latest</button>
                    <button className="action-button" onClick={() => runCommand(`rename latest google calendar event to ${calendarTitle || "team sync"}`)}>Rename Latest</button>
                    <button className="action-button" onClick={() => runCommand(`reschedule latest google calendar event to ${calendarWhen}`)}>Reschedule Latest</button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Manage By Title</h3>
                  <div className="stack-form">
                    <input
                      value={calendarTitle}
                      onChange={(event) => setCalendarTitle(event.target.value)}
                      placeholder="Current event title"
                    />
                    <input
                      value={calendarWhen}
                      onChange={(event) => setCalendarWhen(event.target.value)}
                      placeholder="New title or new time"
                    />
                    <button
                      onClick={() =>
                        calendarTitle.trim()
                          ? runCommand(`delete google calendar event ${calendarTitle}`.trim())
                          : null
                      }
                    >
                      Delete By Title
                    </button>
                    <button
                      onClick={() =>
                        calendarTitle.trim() && calendarWhen.trim()
                          ? runCommand(`rename google calendar event ${calendarTitle} to ${calendarWhen}`.trim())
                          : null
                      }
                    >
                      Rename By Title
                    </button>
                    <button
                      onClick={() =>
                        calendarTitle.trim() && calendarWhen.trim()
                          ? runCommand(`reschedule google calendar event ${calendarTitle} to ${calendarWhen}`.trim())
                          : null
                      }
                    >
                      Reschedule By Title
                    </button>
                  </div>
                </div>
                  </div>
                ) : null}

                {workspaceTab === "notes" ? (
                  <div className="workspace-grid">
                <div className="workspace-card">
                  <h3>Quick Note</h3>
                  <div className="stack-form">
                    <input
                      value={noteInput}
                      onChange={(event) => setNoteInput(event.target.value)}
                      placeholder="Write a quick note..."
                    />
                    <button
                      onClick={() => {
                        if (!noteInput.trim()) return;
                        runCommand(`add note ${noteInput}`.trim());
                        setNoteInput("");
                      }}
                    >
                      Save Note
                    </button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Notes Actions</h3>
                  <div className="action-grid compact two-col">
                    <button className="action-button" onClick={() => runCommand("latest note")}>Latest Note</button>
                    <button className="action-button" onClick={() => runCommand("list notes")}>List Notes</button>
                    <button className="action-button" onClick={() => runCommand("summarize notes")}>Summarize</button>
                    <button className="action-button" onClick={() => runCommand("delete note 1")}>Delete Note 1</button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Search Notes</h3>
                  <div className="stack-form">
                    <input
                      value={noteSearch}
                      onChange={(event) => setNoteSearch(event.target.value)}
                      placeholder="Search notes for..."
                    />
                    <button
                      onClick={() =>
                        noteSearch.trim() ? runCommand(`search notes for ${noteSearch}`.trim()) : null
                      }
                    >
                      Search Notes
                    </button>
                  </div>
                </div>
                  </div>
                ) : null}

                {workspaceTab === "assistant" ? (
                  <div className="workspace-grid">
                    <div className="workspace-card">
                      <h3>Proactive Planner</h3>
                      <p>{uiState.proactive?.summary || "No proactive summary yet."}</p>
                      {(uiState.proactive?.suggestions || []).length ? (
                        <ul className="mini-list compact-list">
                          {(uiState.proactive?.suggestions || []).slice(0, 4).map((item, index) => (
                            <li key={`assistant-proactive-${index}`}>{item.text}</li>
                          ))}
                        </ul>
                      ) : (
                        <p>No proactive suggestions yet.</p>
                      )}
                      <div className="action-grid compact">
                        <button className="action-button" onClick={() => runCommand("plan my day")}>Plan My Day</button>
                        <button className="action-button" onClick={() => runCommand("what should i do now")}>What Now</button>
                        <button className="action-button" onClick={() => runCommand("show proactive suggestions")}>Show Suggestions</button>
                        <button className="action-button" onClick={() => runCommand("refresh proactive suggestions")}>Refresh Suggestions</button>
                        <button className="action-button" onClick={() => runCommand(uiState.settings.focus_mode ? "disable focus mode" : "enable focus mode")}>
                          {uiState.settings.focus_mode ? "Disable Focus" : "Enable Focus"}
                        </button>
                      </div>
                    </div>

                    <div className="workspace-card">
                      <h3>Voice Intelligence</h3>
                      <ul className="mini-list compact-list">
                        <li>{`Wake word: ${voiceStatus.wake_word || uiState.settings.wake_word}`}</li>
                        <li>{`Profile: ${voiceStatus.voice_profile || uiState.settings.voice_profile}`}</li>
                        <li>{`Wake threshold: ${voiceStatus.settings?.wake_match_threshold ?? 0.68}`}</li>
                        <li>{`Wake retry: ${voiceStatus.settings?.wake_retry_window_seconds ?? 6}s`}</li>
                        <li>{`Follow-up timeout: ${voiceStatus.settings?.follow_up_timeout_seconds ?? 12}s`}</li>
                        <li>{`Direct fallback: ${voiceStatus.settings?.wake_direct_fallback_enabled ? "On" : "Off"}`}</li>
                        <li>{`Desktop popup: ${voiceStatus.settings?.desktop_popup_enabled ? "On" : "Off"}`}</li>
                        <li>{`Desktop chime: ${voiceStatus.settings?.desktop_chime_enabled ? "On" : "Off"}`}</li>
                        <li>{`Wake hits: ${voiceStatus.diagnostics?.wake_detection_count || 0}`}</li>
                        <li>{`Commands processed: ${voiceStatus.diagnostics?.command_count || 0}`}</li>
                        <li>{`Last heard: ${voiceStatus.diagnostics?.last_heard_phrase || "Nothing yet"}`}</li>
                        <li>{`Last command: ${voiceStatus.diagnostics?.last_processed_command || "Nothing yet"}`}</li>
                      </ul>
                      <div className="action-grid compact">
                        <button className="action-button" onClick={() => runCommand("voice status")}>Voice Status</button>
                        <button className="action-button" onClick={() => runCommand("voice diagnostics")}>Voice Diagnostics</button>
                        <button className="action-button" onClick={() => runCommand("set voice mode to sensitive")}>Sensitive Voice</button>
                        <button className="action-button" onClick={() => runCommand("set voice mode to normal")}>Normal Voice</button>
                        <button className="action-button" onClick={() => runCommand("enable wake direct fallback")}>Fallback On</button>
                        <button className="action-button" onClick={() => runCommand("disable wake direct fallback")}>Fallback Off</button>
                      </div>
                    </div>

                    <div className="workspace-card">
                      <h3>Smart Home</h3>
                      <ul className="mini-list compact-list">
                        <li>{uiState.integrations?.smart_home?.summary || "Smart Home status unavailable."}</li>
                        <li>{`Configured commands: ${uiState.integrations?.smart_home?.device_count || 0}`}</li>
                        <li>{`Enabled: ${uiState.integrations?.smart_home?.enabled ? "Yes" : "No"}`}</li>
                        <li>{`Placeholder webhooks: ${uiState.integrations?.smart_home?.placeholder_count || 0}`}</li>
                      </ul>
                      <div className="command-chips">
                        {(uiState.integrations?.smart_home?.sample_commands || []).slice(0, 4).map((item) => (
                          <button key={`assistant-iot-${item}`} className="chip-button" onClick={() => runCommand(item)}>
                            {item}
                          </button>
                        ))}
                      </div>
                      <div className="action-grid compact">
                        <button className="action-button" onClick={() => runCommand("smart home status")}>Smart Home Status</button>
                        <button className="action-button" onClick={() => runCommand("show settings")}>Reload Config</button>
                      </div>
                    </div>

                    <div className="workspace-card">
                      <h3>Face Security</h3>
                      <ul className="mini-list compact-list">
                        <li>{uiState.integrations?.face_security?.summary || "Face security status unavailable."}</li>
                        <li>{`Enrolled: ${uiState.integrations?.face_security?.enrolled ? "Yes" : "No"}`}</li>
                        <li>{`Camera ready: ${uiState.integrations?.face_security?.camera_ready ? "Yes" : "No"}`}</li>
                        <li>{`Face matching ready: ${uiState.integrations?.face_security?.embedding_ready ? "Yes" : "No"}`}</li>
                        <li>{`Updated: ${uiState.integrations?.face_security?.updated_at || "Never"}`}</li>
                      </ul>
                      <div className="action-grid compact">
                        <button className="action-button" onClick={() => runCommand("face security status")}>Face Status</button>
                        <button className="action-button" onClick={() => runCommand("enroll my face")}>Enroll Face</button>
                        <button className="action-button" onClick={() => runCommand("verify my face")}>Verify Face</button>
                      </div>
                    </div>
                  </div>
                ) : null}

                {workspaceTab === "settings" ? (
                  <div className="workspace-grid">
                <div className="workspace-card">
                  <h3>Runtime</h3>
                  <ul className="mini-list compact-list">
                    <li>{`Wake word: ${uiState.settings.wake_word}`}</li>
                    <li>{`Voice profile: ${uiState.settings.voice_profile}`}</li>
                    <li>{`Voice state: ${voiceStatus.state_label || "ready"}`}</li>
                    <li>{`Wake listener: ${voiceStatus.wake_word || uiState.settings.wake_word}`}</li>
                    <li>{`Follow-up window: ${voiceStatus.follow_up_active ? `${voiceStatus.follow_up_remaining}s left` : "inactive"}`}</li>
                    <li>{`Wake threshold: ${voiceStatus.settings?.wake_match_threshold ?? 0.68}`}</li>
                    <li>{`Wake retry: ${voiceStatus.settings?.wake_retry_window_seconds ?? 6}s`}</li>
                    <li>{`Direct fallback: ${voiceStatus.settings?.wake_direct_fallback_enabled ? "On" : "Off"}`}</li>
                    <li>{`Desktop popup: ${voiceStatus.settings?.desktop_popup_enabled ? "On" : "Off"}`}</li>
                    <li>{`Desktop chime: ${voiceStatus.settings?.desktop_chime_enabled ? "On" : "Off"}`}</li>
                    <li>{`Offline mode: ${uiState.settings.offline_mode ? "On" : "Off"}`}</li>
                    <li>{`Developer mode: ${uiState.settings.developer_mode ? "On" : "Off"}`}</li>
                    <li>{`Emergency mode: ${uiState.settings.emergency_mode ? "On" : "Off"}`}</li>
                    <li>{`Focus mode: ${uiState.settings.focus_mode ? "On" : "Off"}`}</li>
                  </ul>
                  <div className="stack-form">
                    <input
                      value={wakeWordInput}
                      onChange={(event) => setWakeWordInput(event.target.value)}
                      placeholder={uiState.settings.wake_word || "hey grandpa"}
                    />
                    <button onClick={() => wakeWordInput.trim() ? runCommand(`set wake word to ${wakeWordInput}`) : null}>
                      Set Wake Word
                    </button>
                  </div>
                  <div className="stack-form compact-gap">
                    <input
                      value={wakeThresholdInput}
                      onChange={(event) => setWakeThresholdInput(event.target.value)}
                      placeholder="Wake threshold (0.4 - 1.0)"
                    />
                    <button onClick={() => wakeThresholdInput.trim() ? runCommand(`set wake threshold to ${wakeThresholdInput}`) : null}>
                      Set Wake Threshold
                    </button>
                  </div>
                  <div className="stack-form compact-gap">
                    <input
                      value={followUpTimeoutInput}
                      onChange={(event) => setFollowUpTimeoutInput(event.target.value)}
                      placeholder="Follow-up timeout seconds"
                    />
                    <button onClick={() => followUpTimeoutInput.trim() ? runCommand(`set follow up timeout to ${followUpTimeoutInput}`) : null}>
                      Set Follow-up Timeout
                    </button>
                  </div>
                  <div className="stack-form compact-gap">
                    <input
                      value={wakeRetryInput}
                      onChange={(event) => setWakeRetryInput(event.target.value)}
                      placeholder="Wake retry seconds"
                    />
                    <button onClick={() => wakeRetryInput.trim() ? runCommand(`set wake retry window to ${wakeRetryInput}`) : null}>
                      Set Wake Retry
                    </button>
                  </div>
                  <div className="action-grid compact">
                    <button className="action-button" onClick={() => runCommand("show settings")}>Refresh Settings</button>
                    <button className="action-button" onClick={() => runCommand("voice status")}>Voice Status</button>
                    <button className="action-button" onClick={() => runCommand("voice diagnostics")}>Voice Diagnostics</button>
                    <button className="action-button" onClick={() => runCommand("enable wake direct fallback")}>Fallback On</button>
                    <button className="action-button" onClick={() => runCommand("disable wake direct fallback")}>Fallback Off</button>
                    <button
                      className="action-button"
                      onClick={() => runCommand(voiceStatus.settings?.desktop_popup_enabled ? "disable voice desktop popup" : "enable voice desktop popup")}
                    >
                      {voiceStatus.settings?.desktop_popup_enabled ? "Disable Voice Popup" : "Enable Voice Popup"}
                    </button>
                    <button
                      className="action-button"
                      onClick={() => runCommand(voiceStatus.settings?.desktop_chime_enabled ? "disable voice desktop chime" : "enable voice desktop chime")}
                    >
                      {voiceStatus.settings?.desktop_chime_enabled ? "Disable Voice Chime" : "Enable Voice Chime"}
                    </button>
                    <button className="action-button" onClick={() => runCommand("set wake retry window to 8 seconds")}>Wake Retry 8s</button>
                    <button className="action-button" onClick={() => runCommand("set follow up timeout to 12 seconds")}>Follow-up 12s</button>
                    <button className="action-button" onClick={() => runCommand("set wake threshold to 0.68")}>Threshold 0.68</button>
                    <button className="action-button" onClick={() => runCommand("set post wake pause to 0.4 seconds")}>Wake Pause 0.4s</button>
                    <button className="action-button" onClick={() => runCommand("offline mode status")}>Offline Status</button>
                    <button className="action-button" onClick={() => runCommand("developer mode status")}>Developer Status</button>
                    <button className="action-button" onClick={() => runCommand(uiState.settings.emergency_mode ? "disable emergency mode" : "enable emergency mode")}>
                      {uiState.settings.emergency_mode ? "Disable Emergency" : "Enable Emergency"}
                    </button>
                    <button className="action-button" onClick={() => runCommand("set voice mode to sensitive")}>Sensitive Voice</button>
                    <button className="action-button" onClick={() => runCommand("set voice mode to normal")}>Normal Voice</button>
                    <button className="action-button" onClick={() => runCommand("set voice mode to ultra sensitive")}>Ultra Sensitive</button>
                    <button className="action-button" onClick={() => runCommand("set voice mode to noise cancel")}>Noise Cancel</button>
                    <button className="action-button" onClick={() => runCommand("enable compact voice replies")}>Compact Replies</button>
                    <button className="action-button" onClick={() => runCommand("disable compact voice replies")}>Full Replies</button>
                    <button className="action-button" onClick={() => runCommand(uiState.settings.offline_mode ? "disable offline mode" : "enable offline mode")}>
                      {uiState.settings.offline_mode ? "Disable Offline" : "Enable Offline"}
                    </button>
                    <button className="action-button" onClick={() => runCommand(uiState.settings.developer_mode ? "disable developer mode" : "enable developer mode")}>
                      {uiState.settings.developer_mode ? "Disable Dev" : "Enable Dev"}
                    </button>
                    <button className="action-button" onClick={() => runCommand(uiState.settings.focus_mode ? "disable focus mode" : "enable focus mode")}>
                      {uiState.settings.focus_mode ? "Disable Focus" : "Enable Focus"}
                    </button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Preferences</h3>
                  <ul className="mini-list compact-list">
                    <li>{`Preferred language: ${uiState.memory.preferred_language}`}</li>
                    <li>{`Favorite contact: ${uiState.memory.favorite_contact}`}</li>
                    <li>{`Current mode: ${mode === "voice" ? "Voice" : "Text"}`}</li>
                  </ul>
                  <div className="action-grid compact">
                    <button className="action-button" onClick={() => runCommand("set preferred language to tamil")}>Tamil</button>
                    <button className="action-button" onClick={() => runCommand("set preferred language to english")}>English</button>
                    <button className="action-button" onClick={() => runCommand("set preferred tone to friendly")}>Friendly</button>
                    <button className="action-button" onClick={() => runCommand("set preferred tone to professional")}>Professional</button>
                    <button className="action-button" onClick={() => runCommand("what is my preferred language")}>Language Status</button>
                    <button className="action-button" onClick={() => runCommand("what are my settings")}>Profile Summary</button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Startup</h3>
                  <ul className="mini-list compact-list">
                    <li>{startupState.summary}</li>
                    <li>{`Auto launch: ${startupState.auto_launch_enabled ? "Enabled" : "Disabled"}`}</li>
                    <li>{`Tray launch: ${startupState.tray_mode ? "Enabled" : "Disabled"}`}</li>
                    <li>{`Portable setup helper: ${startupState.portable_setup_ready ? "Ready" : "Missing"}`}</li>
                  </ul>
                  <div className="action-grid compact">
                    <button className="action-button" onClick={() => runCommand("enable assistant startup")}>Enable Startup</button>
                    <button className="action-button" onClick={() => runCommand("disable assistant startup")}>Disable Startup</button>
                    <button className="action-button" onClick={() => runCommand("enable tray startup")}>Enable Tray Startup</button>
                    <button className="action-button" onClick={() => runCommand("disable tray startup")}>Disable Tray Startup</button>
                    <button className="action-button" onClick={() => runCommand("enable tray react ui")}>Tray React On</button>
                    <button className="action-button" onClick={() => runCommand("disable tray react ui")}>Tray React Off</button>
                    <button className="action-button" onClick={() => runCommand("set tray react mode to browser")}>Tray Browser</button>
                    <button className="action-button" onClick={() => runCommand("set tray react mode to desktop")}>Tray Desktop</button>
                    <button className="action-button" onClick={() => runCommand("assistant startup status")}>Startup Status</button>
                    <button className="action-button" onClick={() => runCommand("tray react status")}>Tray React Status</button>
                    <button className="action-button" onClick={() => runPortableSetup("desktop")}>Create Desktop Shortcut</button>
                    <button className="action-button" onClick={() => runPortableSetup("startup-on")}>Portable Startup On</button>
                    <button className="action-button" onClick={() => runPortableSetup("startup-off")}>Portable Startup Off</button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Integrations</h3>
                  <div className="action-grid compact">
                    <button className="action-button" onClick={() => runCommand("google calendar status")}>Calendar Status</button>
                    <button className="action-button" onClick={() => runCommand("sync google calendar")}>Sync Calendar</button>
                    <button className="action-button" onClick={() => runCommand("github summary")}>GitHub Summary</button>
                    <button className="action-button" onClick={() => runCommand("offline ai status")}>Offline AI Status</button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Key Detection Quick Start</h3>
                  <div className="quick-start-list">
                    <div className="quick-start-step"><span>1</span><p>Apply your custom key model path.</p></div>
                    <div className="quick-start-step"><span>2</span><p>Enable small object mode and watch target key.</p></div>
                    <div className="quick-start-step"><span>3</span><p>Start camera detection and hold the key near center.</p></div>
                  </div>
                  <div className="action-grid compact two-col">
                    <button className="action-button" onClick={prepareKeyDetection}>Prepare Key Detection</button>
                    <button className="action-button" onClick={() => runCommand("key detection status")}>Key Status</button>
                    <button className="action-button" onClick={() => runCommand("watch for key")}>Watch Key</button>
                    <button className="action-button" onClick={() => runCommand("start object detection")}>Start Key Scan</button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Object Detection</h3>
                  <ul className="mini-list compact-list">
                    <li>{uiState.overview.object_detection}</li>
                    <li>{uiState.object_watch.summary}</li>
                    <li>{`Model: ${uiState.object_detection?.model_name || "yolov8n.pt"}`}</li>
                    <li>{`Small mode: ${uiState.object_detection?.small_object_mode ? "On" : "Off"}`}</li>
                    <li>Camera: live YOLO detection</li>
                    <li>Screen: screenshot object scan</li>
                  </ul>
                  <div className="stack-form compact-gap">
                    <input
                      type="text"
                      value={objectModelInput}
                      onChange={(event) => setObjectModelInput(event.target.value)}
                      placeholder="Custom model path or file name"
                    />
                    <div className="action-grid compact two-col">
                      <button className="action-button" onClick={applyObjectModelInput}>Apply Model Path</button>
                      <button className="action-button" onClick={() => runCommand("use default object model")}>Use Default Model</button>
                    </div>
                    <input
                      type="text"
                      value={objectPresetNameInput}
                      onChange={(event) => setObjectPresetNameInput(event.target.value)}
                      placeholder="Preset name"
                    />
                    <div className="action-grid compact two-col">
                      <button className="action-button" onClick={saveObjectPresetFromInputs}>Save Preset</button>
                      <button className="action-button" onClick={() => runCommand("list object model presets")}>Refresh Presets</button>
                    </div>
                  </div>
                  <div className="action-grid compact">
                    <button className="action-button" onClick={() => runCommand("start object detection")}>Start Camera Detection</button>
                    <button className="action-button" onClick={() => runCommand("stop object detection")}>Stop Camera Detection</button>
                    <button className="action-button" onClick={() => runCommand("what objects do you see")}>What Objects Do You See</button>
                    <button className="action-button" onClick={() => runCommand("detect objects on screen")}>Detect Objects On Screen</button>
                    <button className="action-button" onClick={() => runCommand("is key visible on camera")}>Is Key Visible</button>
                    <button className="action-button" onClick={() => runCommand("count key on camera")}>Count Key</button>
                    <button className="action-button" onClick={() => runCommand("count person on camera")}>Count Person On Camera</button>
                    <button className="action-button" onClick={() => runCommand("is phone visible on screen")}>Is Phone Visible On Screen</button>
                    <button className="action-button" onClick={() => runCommand("watch for person")}>Watch Person</button>
                    <button className="action-button" onClick={() => runCommand("watch for phone")}>Watch Phone</button>
                    <button className="action-button" onClick={() => runCommand("watch for key")}>Watch Key</button>
                    <button className="action-button" onClick={() => runCommand("object watch status")}>Watch Status</button>
                    <button className="action-button" onClick={() => runCommand("stop object watch")}>Stop Watch</button>
                    <button className="action-button" onClick={() => runCommand("enable small object mode")}>Small Mode On</button>
                    <button className="action-button" onClick={() => runCommand("disable small object mode")}>Small Mode Off</button>
                    <button className="action-button" onClick={() => runCommand("supported objects")}>Supported Objects</button>
                    <button className="action-button" onClick={() => runCommand("current object model")}>Current Model</button>
                    <button className="action-button" onClick={() => runCommand("use default object model")}>Default Model</button>
                    <button className="action-button" onClick={promptForObjectModel}>Set Custom Model</button>
                    <button className="action-button" onClick={promptToSaveObjectPreset}>Save Model Preset</button>
                    <button className="action-button" onClick={promptToUseObjectPreset}>Use Saved Preset</button>
                    <button className="action-button" onClick={() => runCommand("list object model presets")}>List Presets</button>
                    <button className="action-button" onClick={() => runCommand("object detection history")}>Detection History</button>
                    <button className="action-button" onClick={() => runCommand("object alert history")}>Alert History</button>
                    <button className="action-button" onClick={() => runCommand("clear object history")}>Clear History</button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Object Model Presets</h3>
                  {(uiState.object_detection?.presets || []).length ? (
                    <div className="preset-list">
                      {uiState.object_detection.presets.slice(0, 8).map((preset, index) => (
                        <div className="preset-item" key={`object-preset-${index}`}>
                          <div className="preset-copy">
                            <strong>{preset.name}</strong>
                            <span>{preset.model}</span>
                          </div>
                          <div className="preset-actions">
                            <button className="ghost-button" onClick={() => useObjectPresetByName(preset.name)}>Use</button>
                            <button className="ghost-button" onClick={() => deleteObjectPresetByName(preset.name)}>Delete</button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p>No object model presets saved yet.</p>
                  )}
                </div>

                <div className="workspace-card">
                  <h3>Recent Detections</h3>
                  {(uiState.object_history || []).length ? (
                    <ul className="mini-list compact-list">
                      {uiState.object_history.slice(0, 6).map((item, index) => (
                        <li key={`vision-history-${index}`}>{item.summary}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>No object detection history yet.</p>
                  )}
                </div>

                <div className="workspace-card">
                  <h3>Watch Alert Log</h3>
                  {(uiState.object_watch_history || []).length ? (
                    <ul className="mini-list compact-list">
                      {uiState.object_watch_history.slice(0, 6).map((item, index) => (
                        <li key={`watch-log-${index}`}>{item.summary}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>No watch alerts yet.</p>
                  )}
                </div>
                  </div>
                ) : null}
              </div>

              {mode === "text" ? (
                <ChatSurface
                  messages={messages}
                  filteredMessages={filteredMessages.map((message) => ({
                    ...message,
                    text: normalizeMessageText(message.text),
                  }))}
                  chatSearch={chatSearch}
                  setChatSearch={setChatSearch}
                  quickSuggestions={quickSuggestions}
                  liveSuggestions={liveSuggestions}
                  input={input}
                  setInput={setInput}
                  showAutocomplete={showAutocomplete}
                  activeSuggestionIndex={activeSuggestionIndex}
                  setActiveSuggestionIndex={setActiveSuggestionIndex}
                  applySuggestion={applySuggestion}
                  pinCommand={pinCommand}
                  handleSend={handleSend}
                  isChatLoading={isChatLoading}
                  clearConversation={clearConversation}
                  reloadWorkspace={reloadWorkspace}
                  apiError={apiError}
                  messagesEndRef={messagesEndRef}
                  chatSessions={chatSessions}
                  currentSessionId={currentSessionId}
                  createSession={createSession}
                  switchSession={switchSession}
                  regenerateReply={regenerateReply}
                  cancelStreaming={cancelStreaming}
                  retryLastPrompt={retryLastPrompt}
                  lastPrompt={lastPrompt}
                  showChatSettings={showChatSettings}
                  setShowChatSettings={setShowChatSettings}
                  chatSettingsDraft={chatSettingsDraft}
                  setChatSettingsDraft={setChatSettingsDraft}
                  saveChatSettings={saveChatSettings}
                  renameSession={renameSession}
                  deleteSession={deleteSession}
                  exportSession={exportSession}
                  pendingConfirmation={pendingConfirmation}
                  confirmPendingAction={confirmPendingAction}
                  attachedDocuments={attachedDocuments}
                  uploadChatDocument={uploadChatDocument}
                  removeChatDocument={removeChatDocument}
                />
              ) : (
                <div className="voice-banner">
                  <span className={`orb ${(voiceStatus.activity || "listening").toLowerCase()}`} />
                  <VoiceWave />
                  <div className="voice-banner-copy">
                    <strong>Voice mode active</strong>
                    <span>{voiceStatus.transcript || "Listening... Speak now."}</span>
                    <small>{`Wake: ${voiceStatus.wake_word || "hey grandpa"} | State: ${voiceStatus.state_label || "ready"}${voiceStatus.follow_up_active ? ` | Follow-up ${voiceStatus.follow_up_remaining}s` : ""}`}</small>
                    {voiceStatus.last_reply ? <small>{`Last reply: ${voiceStatus.last_reply}`}</small> : null}
                  </div>
                </div>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  );
}
