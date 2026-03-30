import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = "http://127.0.0.1:8765";

const initialMessages = [
  {
    id: 1,
    side: "assistant",
    text: "Grandpa : Hello Grandchild! I am ready.",
  },
  {
    id: 2,
    side: "assistant",
    text: "Grandpa : Good morning. You have 1 pending task and 2 overdue reminders.",
  },
];

function LogoMark() {
  return (
    <div className="logo-mark" aria-hidden="true">
      <div className="logo-ear left" />
      <div className="logo-ear right" />
      <div className="logo-face">
        <div className="logo-eye left" />
        <div className="logo-eye right" />
        <div className="logo-nose" />
        <div className="logo-beard left" />
        <div className="logo-beard center" />
        <div className="logo-beard right" />
      </div>
    </div>
  );
}

function SectionCard({ title, children }) {
  return (
    <section className="sidebar-card">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function MessageBubble({ side, text }) {
  return (
    <div className={`message-row ${side}`}>
      <div className={`message-bubble ${side}`}>{text}</div>
    </div>
  );
}

export default function App() {
  const messagesEndRef = useRef(null);
  const [mode, setMode] = useState("text");
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
  const [messages, setMessages] = useState(initialMessages);
  const [activity, setActivity] = useState("Ready");
  const [uiState, setUiState] = useState({
    overview: {
      tasks: "Loading...",
      reminders: "Loading...",
      weather: "Loading...",
      health: "Loading...",
    },
    today: "Loading...",
    next_event: "Loading...",
    latest_note: "Loading...",
    recent_commands: [],
    dashboard: {
      tasks: [],
      reminders: [],
      events: [],
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
    },
    emergency: {
      location: "Loading...",
      contact: "Loading...",
    },
    memory: {
      preferred_language: "Loading...",
      favorite_contact: "Loading...",
    },
  });
  const [apiError, setApiError] = useState("");
  const [voiceStatus, setVoiceStatus] = useState({
    enabled: false,
    activity: "Ready",
    transcript: "",
    error: "",
    messages: [],
  });
  const [startupState, setStartupState] = useState({
    auto_launch_enabled: false,
    tray_mode: false,
    summary: "Loading...",
  });

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  useEffect(() => {
    setActivity(mode === "voice" ? voiceStatus.activity || "Ready" : "Ready");
  }, [mode, voiceStatus.activity]);

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
    const timer = window.setInterval(loadVoiceStatus, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [mode]);

  useEffect(() => {
    let cancelled = false;

    const loadState = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/ui-state`);
        const payload = await response.json();
        if (!cancelled && payload?.ok && payload.state) {
          setUiState(payload.state);
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
    const userMessage = { id: Date.now(), side: "user", text: value };
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

      const replies = (payload.messages || []).map((text, index) => ({
        id: `${Date.now()}-${index}`,
        side: "assistant",
        text: `Grandpa : ${text}`,
      }));
      setMessages((current) => [...current, ...replies]);
      if (payload.state) {
        setUiState(payload.state);
      }
      setApiError("");
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-error`,
          side: "assistant",
          text: `Grandpa : ${error.message || "Assistant API unavailable."}`,
        },
      ]);
      setApiError("Python assistant API is not reachable yet.");
    } finally {
      setActivity(mode === "voice" ? "Listening" : "Ready");
    }
  };

  const handleSend = async () => {
    await runCommand(input);
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
          },
        ]);
      }
      setApiError("");
    } catch (error) {
      setApiError(error.message || "Could not update startup settings.");
    }
  };

  const statusItems = useMemo(
    () => [
      { label: "Tasks", value: uiState.overview.tasks },
      { label: "Reminders", value: uiState.overview.reminders },
      { label: "Weather", value: uiState.overview.weather },
      { label: "Health", value: uiState.overview.health },
    ],
    [uiState],
  );

  const recentCommands = uiState.recent_commands || [];
  const memoryItems = [
    `Preferred language: ${uiState.memory.preferred_language}`,
    `Favorite contact: ${uiState.memory.favorite_contact}`,
    `Mode: ${mode === "voice" ? "Voice" : "Text"}`,
  ];
  const workspaceTabs = ["planner", "calendar", "notes", "settings"];

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

  return (
    <div className="app-shell">
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
            </div>
          </div>
        </div>
        <div className="clock-wrap">
          <strong>{formatTime}</strong>
          <span>{formatDate}</span>
        </div>
      </header>

      <main className="layout-grid">
        <aside className="sidebar">
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
                    <li key={`task-${item}`}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4>Reminders</h4>
                <ul className="mini-list">
                  {(uiState.dashboard.reminders || []).map((item) => (
                    <li key={`reminder-${item}`}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4>Events</h4>
                <ul className="mini-list">
                  {(uiState.dashboard.events || []).map((item) => (
                    <li key={`event-${item}`}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Recent Commands">
            {recentCommands.length ? (
              <div className="command-chips">
                {recentCommands.map((item) => (
                  <button key={item} className="chip-button" onClick={() => runCommand(item)}>
                    {item}
                  </button>
                ))}
              </div>
            ) : (
              <p>No recent commands yet.</p>
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
            <ul className="mini-list">
              {(uiState.contacts.preview || []).map((item) => (
                <li key={`contact-${item}`}>{item}</li>
              ))}
            </ul>
            <div className="action-grid">
              <button className="action-button" onClick={() => runCommand("call appa")}>Call Appa</button>
              <button className="action-button" onClick={() => runCommand("message to amma saying saptiya")}>Message Amma</button>
              <button className="action-button" onClick={() => runCommand("mail appa about today plan")}>Mail Appa</button>
            </div>
          </SectionCard>

          <SectionCard title="Emergency">
            <ul className="mini-list">
              <li>{`Emergency contact: ${uiState.emergency.contact}`}</li>
              <li>{`Saved location: ${uiState.emergency.location}`}</li>
            </ul>
            <div className="action-grid">
              <button className="action-button danger" onClick={() => runCommand("start emergency protocol")}>Start Protocol</button>
              <button className="action-button danger" onClick={() => runCommand("send emergency alert")}>Send Alert</button>
              <button className="action-button" onClick={() => runCommand("send i am safe alert")}>I'm Safe</button>
              <button className="action-button" onClick={() => runCommand("share my location everywhere")}>Share Location</button>
            </div>
          </SectionCard>

          <SectionCard title="Startup">
            <p>{startupState.summary}</p>
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
            </div>
          </SectionCard>
        </aside>

        <section className="chat-panel">
          <div className="chat-panel-head">
            <h2>Conversation</h2>
            <p>{mode === "voice" ? "Speak naturally. Voice replies stay active." : "Type a command and press Run."}</p>
            {apiError ? <span className="api-warning">{apiError}</span> : null}
          </div>

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

            {workspaceTab === "settings" ? (
              <div className="workspace-grid">
                <div className="workspace-card">
                  <h3>Runtime</h3>
                  <ul className="mini-list compact-list">
                    <li>{`Wake word: ${uiState.settings.wake_word}`}</li>
                    <li>{`Voice profile: ${uiState.settings.voice_profile}`}</li>
                    <li>{`Offline mode: ${uiState.settings.offline_mode ? "On" : "Off"}`}</li>
                    <li>{`Developer mode: ${uiState.settings.developer_mode ? "On" : "Off"}`}</li>
                    <li>{`Emergency mode: ${uiState.settings.emergency_mode ? "On" : "Off"}`}</li>
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
                  <div className="action-grid compact">
                    <button className="action-button" onClick={() => runCommand("show settings")}>Refresh Settings</button>
                    <button className="action-button" onClick={() => runCommand("voice status")}>Voice Status</button>
                    <button className="action-button" onClick={() => runCommand("offline mode status")}>Offline Status</button>
                    <button className="action-button" onClick={() => runCommand("developer mode status")}>Developer Status</button>
                    <button className="action-button" onClick={() => runCommand(uiState.settings.offline_mode ? "disable offline mode" : "enable offline mode")}>
                      {uiState.settings.offline_mode ? "Disable Offline" : "Enable Offline"}
                    </button>
                    <button className="action-button" onClick={() => runCommand(uiState.settings.developer_mode ? "disable developer mode" : "enable developer mode")}>
                      {uiState.settings.developer_mode ? "Disable Dev" : "Enable Dev"}
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
                  </ul>
                  <div className="action-grid compact">
                    <button className="action-button" onClick={() => runCommand("enable assistant startup")}>Enable Startup</button>
                    <button className="action-button" onClick={() => runCommand("disable assistant startup")}>Disable Startup</button>
                    <button className="action-button" onClick={() => runCommand("enable tray startup")}>Enable Tray Startup</button>
                    <button className="action-button" onClick={() => runCommand("disable tray startup")}>Disable Tray Startup</button>
                    <button className="action-button" onClick={() => runCommand("assistant startup status")}>Startup Status</button>
                    <button className="action-button" onClick={() => runCommand("tray react status")}>Tray React Status</button>
                  </div>
                </div>

                <div className="workspace-card">
                  <h3>Integrations</h3>
                  <div className="action-grid compact">
                    <button className="action-button" onClick={() => runCommand("google calendar status")}>Calendar Status</button>
                    <button className="action-button" onClick={() => runCommand("sync google calendar")}>Sync Calendar</button>
                    <button className="action-button" onClick={() => runCommand("telegram status")}>Telegram Status</button>
                    <button className="action-button" onClick={() => runCommand("telegram remote status")}>Telegram Remote</button>
                    <button className="action-button" onClick={() => runCommand("github summary")}>GitHub Summary</button>
                    <button className="action-button" onClick={() => runCommand("offline ai status")}>Offline AI Status</button>
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          <div className="messages">
            {messages.map((message) => (
              <MessageBubble key={message.id} side={message.side} text={message.text} />
            ))}
            <div ref={messagesEndRef} />
          </div>

          {mode === "text" && recentCommands.length ? (
            <div className="quick-strip">
              <span>Quick run</span>
              <div className="command-chips">
                {recentCommands.slice(0, 3).map((item) => (
                  <button
                    key={`quick-${item}`}
                    className="chip-button small"
                    onClick={() => runCommand(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <footer className="composer">
            {mode === "text" ? (
              <>
                <input
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") handleSend();
                  }}
                  placeholder="Type your command..."
                />
                <button onClick={handleSend}>Run</button>
              </>
            ) : (
              <div className="voice-banner">
                <span className="orb listening" />
                <div className="voice-banner-copy">
                  <strong>Voice mode active</strong>
                  <span>{voiceStatus.transcript || "Listening... Speak now."}</span>
                </div>
              </div>
            )}
          </footer>
        </section>
      </main>
    </div>
  );
}
