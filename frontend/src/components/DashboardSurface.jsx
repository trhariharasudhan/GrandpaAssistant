export default function DashboardSurface({
  uiState,
  quickSuggestions,
  runCommand,
  setSurfaceTab,
  setWorkspaceTab,
  focusPlannerSection,
  mode,
  voiceStatus,
  activity,
  handleModeChange,
}) {
  const proactive = uiState.proactive || {};
  const proactiveSuggestions = proactive.suggestions || [];
  const smartHome = uiState.integrations?.smart_home || {};
  const faceSecurity = uiState.integrations?.face_security || {};
  const voiceSettings = voiceStatus.settings || {};
  const voiceDiagnostics = voiceStatus.diagnostics || {};

  return (
    <div className="dashboard-surface">
      <div className="dashboard-surface-grid">
        <section className="dashboard-hero">
          <span className="dashboard-kicker">Today</span>
          <h3>{uiState.today}</h3>
          <p>{uiState.next_event}</p>
          <div className="command-chips">
            {quickSuggestions.slice(0, 4).map((item) => (
              <button
                key={`dash-quick-${item}`}
                className="chip-button"
                onClick={() => {
                  setSurfaceTab("chat");
                  runCommand(item);
                }}
              >
                {item}
              </button>
            ))}
          </div>
        </section>

        <section className="dashboard-metrics">
          <div className="metric-card">
            <span>Weather</span>
            <strong>{uiState.overview.weather}</strong>
          </div>
          <div className="metric-card">
            <span>Health</span>
            <strong>{uiState.overview.health}</strong>
          </div>
          <div className="metric-card">
            <span>Voice</span>
            <strong>{mode === "voice" ? voiceStatus.activity || "Listening" : "Text mode"}</strong>
          </div>
          <div className="metric-card">
            <span>Wake word</span>
            <strong>{uiState.settings.wake_word}</strong>
          </div>
          <div className="metric-card">
            <span>Focus mode</span>
            <strong>{uiState.settings.focus_mode ? "On" : "Off"}</strong>
          </div>
          <div className="metric-card">
            <span>Vision</span>
            <strong>{uiState.overview.object_detection}</strong>
          </div>
        </section>

        <section className="dashboard-card wide">
          <div className="dashboard-card-head">
            <h3>Planner Snapshot</h3>
            <button
              className="ghost-button"
              onClick={() => {
                setSurfaceTab("chat");
                setWorkspaceTab("planner");
              }}
            >
              Open Planner
            </button>
          </div>
          <div className="dashboard-lanes">
            <div>
              <h4>Tasks</h4>
              <ul className="mini-list">
                {(uiState.dashboard.tasks || []).slice(0, 4).map((item) => (
                  <li key={`dashboard-task-${item}`}>
                    <button
                      className="inline-select"
                      onClick={() => {
                        focusPlannerSection("task", item);
                        setSurfaceTab("chat");
                      }}
                    >
                      {item}
                    </button>
                  </li>
                ))}
                {(uiState.dashboard.tasks || []).length ? null : <li>No tasks right now.</li>}
              </ul>
            </div>
            <div>
              <h4>Reminders</h4>
              <ul className="mini-list">
                {(uiState.dashboard.reminders || []).slice(0, 4).map((item) => (
                  <li key={`dashboard-reminder-${item}`}>
                    <button
                      className="inline-select"
                      onClick={() => {
                        focusPlannerSection("reminder", item);
                        setSurfaceTab("chat");
                      }}
                    >
                      {item}
                    </button>
                  </li>
                ))}
                {(uiState.dashboard.reminders || []).length ? null : <li>No reminders right now.</li>}
              </ul>
            </div>
            <div>
              <h4>Events</h4>
              <ul className="mini-list">
                {(uiState.dashboard.events || []).slice(0, 4).map((item) => (
                  <li key={`dashboard-event-${item}`}>
                    <button
                      className="inline-select"
                      onClick={() => {
                        focusPlannerSection("event", item);
                        setSurfaceTab("chat");
                      }}
                    >
                      {item}
                    </button>
                  </li>
                ))}
                {(uiState.dashboard.events || []).length ? null : <li>No events right now.</li>}
              </ul>
            </div>
          </div>
        </section>

        <section className="dashboard-card">
          <div className="dashboard-card-head">
            <h3>Voice Panel</h3>
            <button className="ghost-button" onClick={() => handleModeChange(mode === "voice" ? "text" : "voice")}>
              {mode === "voice" ? "Switch to Text" : "Switch to Voice"}
            </button>
          </div>
          <div className="voice-stage">
            <span className={`voice-stage-orb orb ${(voiceStatus.activity || activity || "ready").toLowerCase()}`} />
            <div>
              <strong>{mode === "voice" ? "Voice mode active" : "Text mode active"}</strong>
              <p>{mode === "voice" ? (voiceStatus.transcript || "Listening... Speak now.") : "Enable voice mode to speak naturally with Grandpa Assistant."}</p>
              {mode === "voice" ? (
                <>
                  <small>{`Wake word: ${voiceStatus.wake_word || "hey grandpa"} | State: ${voiceStatus.state_label || "ready"}${voiceStatus.follow_up_active ? ` | Follow-up: ${voiceStatus.follow_up_remaining}s` : ""}`}</small>
                  <small>{`Threshold: ${voiceSettings.wake_match_threshold ?? 0.68} | Retry: ${voiceSettings.wake_retry_window_seconds ?? 6}s | Fallback: ${voiceSettings.wake_direct_fallback_enabled ? "On" : "Off"}`}</small>
                  <small>{`Wake hits: ${voiceDiagnostics.wake_detection_count || 0} | Commands: ${voiceDiagnostics.command_count || 0} | Interrupts: ${voiceDiagnostics.interrupt_count || 0}`}</small>
                </>
              ) : null}
            </div>
          </div>
        </section>

        <section className="dashboard-card">
          <div className="dashboard-card-head">
            <h3>Proactive Suggestions</h3>
            <button className="ghost-button" onClick={() => runCommand("refresh proactive suggestions")}>
              Refresh
            </button>
          </div>
          <p>{proactive.summary || "No proactive summary yet."}</p>
          {proactiveSuggestions.length ? (
            <ul className="mini-list compact-list">
              {proactiveSuggestions.slice(0, 4).map((item, index) => (
                <li key={`proactive-${index}`}>{item.text}</li>
              ))}
            </ul>
          ) : (
            <p>No proactive suggestions yet.</p>
          )}
          <div className="action-grid compact two-col">
            <button className="action-button" onClick={() => runCommand("plan my day")}>Plan My Day</button>
            <button className="action-button" onClick={() => runCommand("what should i do now")}>What Now</button>
            <button className="action-button" onClick={() => runCommand("show proactive suggestions")}>Show Suggestions</button>
            <button className="action-button" onClick={() => runCommand(uiState.settings.focus_mode ? "disable focus mode" : "enable focus mode")}>
              {uiState.settings.focus_mode ? "Disable Focus" : "Enable Focus"}
            </button>
          </div>
        </section>

        <section className="dashboard-card">
          <div className="dashboard-card-head">
            <h3>Object Detection</h3>
          </div>
          <p>{(uiState.dashboard.vision || [uiState.overview.object_detection])[0]}</p>
          <p>{uiState.object_watch?.summary}</p>
          <p>{`Model: ${uiState.object_detection?.model_name || "yolov8n.pt"} | Small mode: ${uiState.object_detection?.small_object_mode ? "On" : "Off"}`}</p>
          <div className="action-grid compact two-col">
            <button className="action-button" onClick={() => runCommand("prepare key detection")}>Prepare Key</button>
            <button className="action-button" onClick={() => runCommand("key detection status")}>Key Status</button>
            <button className="action-button" onClick={() => runCommand("start object detection")}>Start Camera</button>
            <button className="action-button" onClick={() => runCommand("stop object detection")}>Stop Camera</button>
            <button className="action-button" onClick={() => runCommand("detect objects on screen")}>Scan Screen</button>
            <button
              className="action-button"
              onClick={() =>
                runCommand(uiState.object_detection?.small_object_mode ? "disable small object mode" : "enable small object mode")
              }
            >
              {uiState.object_detection?.small_object_mode ? "Small Mode Off" : "Small Mode On"}
            </button>
            <button className="action-button" onClick={() => runCommand("current object model")}>Current Model</button>
            <button className="action-button" onClick={() => runCommand("list object model presets")}>List Presets</button>
          </div>
        </section>

        <section className="dashboard-card">
          <div className="dashboard-card-head">
            <h3>Notifications</h3>
          </div>
          {uiState.notifications?.length ? (
            <ul className="notification-list">
              {uiState.notifications.slice(0, 4).map((item, index) => (
                <li key={`dashboard-note-${index}`} className={`notification-item ${item.level || "neutral"}`}>
                  {item.text}
                </li>
              ))}
            </ul>
          ) : (
            <p>No active notifications.</p>
          )}
        </section>

        <section className="dashboard-card">
          <div className="dashboard-card-head">
            <h3>Integrations</h3>
          </div>
          <p>{smartHome.summary || "Smart Home status unavailable."}</p>
          <p>{faceSecurity.summary || "Face security status unavailable."}</p>
          <div className="command-chips">
            {(smartHome.sample_commands || []).slice(0, 3).map((item) => (
              <button key={`iot-${item}`} className="chip-button" onClick={() => runCommand(item)}>
                {item}
              </button>
            ))}
          </div>
          <div className="action-grid compact two-col">
            <button className="action-button" onClick={() => runCommand("smart home status")}>Smart Home Status</button>
            <button className="action-button" onClick={() => runCommand("face security status")}>Face Security</button>
            <button className="action-button" onClick={() => runCommand("enroll my face")}>Enroll Face</button>
            <button className="action-button" onClick={() => runCommand("verify my face")}>Verify Face</button>
          </div>
        </section>

        <section className="dashboard-card">
          <div className="dashboard-card-head">
            <h3>Recent Detections</h3>
          </div>
          {(uiState.object_history || []).length ? (
            <ul className="mini-list compact-list">
              {uiState.object_history.slice(0, 4).map((item, index) => (
                <li key={`object-history-${index}`}>{item.summary}</li>
              ))}
            </ul>
          ) : (
            <p>No detection history yet.</p>
          )}
        </section>

        <section className="dashboard-card">
          <div className="dashboard-card-head">
            <h3>Watch Alerts</h3>
          </div>
          {(uiState.object_watch_history || []).length ? (
            <ul className="mini-list compact-list">
              {uiState.object_watch_history.slice(0, 4).map((item, index) => (
                <li key={`watch-history-${index}`}>{item.summary}</li>
              ))}
            </ul>
          ) : (
            <p>No watch alerts yet.</p>
          )}
        </section>
      </div>
    </div>
  );
}
