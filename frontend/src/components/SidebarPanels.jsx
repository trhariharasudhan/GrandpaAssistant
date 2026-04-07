import SectionCard from "./SectionCard";

export default function SidebarPanels({
  navItems,
  workspaceTab,
  setWorkspaceTab,
  statusItems,
  quickSuggestions,
  pinnedCommands,
  runCommand,
  uiState,
  focusPlannerSection,
  memoryItems,
  contactSearch,
  setContactSearch,
  filteredContacts,
  selectedContact,
  selectContact,
  activeContact,
  contactAlias,
  setContactAlias,
  contactAliasTarget,
  setContactAliasTarget,
  startupState,
  updateStartupSettings,
  authState,
  accountProfile,
  accountDraft,
  setAccountDraft,
  saveAccountProfile,
  accountBusy,
}) {
  const proactive = uiState.proactive || {};
  const proactiveSuggestions = proactive.suggestions || [];
  const hardware = uiState.integrations?.hardware || {};
  const smartHome = uiState.integrations?.smart_home || {};
  const faceSecurity = uiState.integrations?.face_security || {};
  const plugins = uiState.integrations?.plugins || uiState.runtime?.plugins || {};
  const runtime = uiState.runtime || {};
  const runtimeState = runtime.runtime || {};
  const mood = uiState.memory?.mood || {};
  const agentCount = Object.keys(runtime.agents || {}).length;
  const accountUser = accountProfile?.user || authState?.user || null;
  const accountPreferences = accountProfile?.preferences || authState?.preferences || {};

  return (
    <aside className="sidebar">
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

      <SectionCard title="Daily Snapshot">
        <ul className="mini-list compact-list snapshot-list">
          <li>
            <strong>Today</strong>
            <span>{uiState.today}</span>
          </li>
          <li>
            <strong>Next Event</strong>
            <span>{uiState.next_event}</span>
          </li>
          <li>
            <strong>Latest Note</strong>
            <span>{uiState.latest_note}</span>
          </li>
        </ul>
      </SectionCard>

      <SectionCard title="Planner">
        <div className="dashboard-group">
          <div>
            <h4>Tasks</h4>
            <ul className="mini-list">
              {(uiState.dashboard.tasks || []).slice(0, 5).map((item) => (
                <li key={`task-${item}`}>
                  <button className="inline-select" onClick={() => focusPlannerSection("task", item)}>
                    {item}
                  </button>
                </li>
              ))}
              {(uiState.dashboard.tasks || []).length ? null : <li>No tasks.</li>}
            </ul>
          </div>
          <div>
            <h4>Reminders</h4>
            <ul className="mini-list">
              {(uiState.dashboard.reminders || []).slice(0, 5).map((item) => (
                <li key={`reminder-${item}`}>
                  <button className="inline-select" onClick={() => focusPlannerSection("reminder", item)}>
                    {item}
                  </button>
                </li>
              ))}
              {(uiState.dashboard.reminders || []).length ? null : <li>No reminders.</li>}
            </ul>
          </div>
          <div>
            <h4>Events</h4>
            <ul className="mini-list">
              {(uiState.dashboard.events || []).slice(0, 5).map((item) => (
                <li key={`event-${item}`}>
                  <button className="inline-select" onClick={() => focusPlannerSection("event", item)}>
                    {item}
                  </button>
                </li>
              ))}
              {(uiState.dashboard.events || []).length ? null : <li>No events.</li>}
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

      <SectionCard title="Agent Runtime">
        <ul className="mini-list compact-list">
          <li>{runtime.running ? "Runtime active." : "Runtime offline."}</li>
          <li>{`Thinking mode: ${runtimeState.thinking_mode || "adaptive"}`}</li>
          <li>{`Context: ${runtimeState.current_context || "casual"}`}</li>
          <li>{`Autonomous mode: ${runtimeState.autonomous_mode ? "On" : "Off"}`}</li>
          <li>{`Mood: ${mood.last_mood || "neutral"} | Streak: ${mood.streak || 0}`}</li>
          <li>{`Agents: ${agentCount} | Plugins: ${plugins.enabled || 0}/${plugins.total || 0}`}</li>
        </ul>
      </SectionCard>

      <SectionCard title="Account">
        {accountUser ? (
          <>
            <p>{`Signed in as ${accountUser.username} (${accountUser.role || "user"}).`}</p>
            <div className="stack-form compact-gap">
              <input
                value={accountDraft.displayName}
                onChange={(event) => setAccountDraft((current) => ({ ...current, displayName: event.target.value }))}
                placeholder="Display name"
              />
              <select
                value={accountDraft.preferredLanguage}
                onChange={(event) => setAccountDraft((current) => ({ ...current, preferredLanguage: event.target.value }))}
              >
                <option value="en-US">English (US)</option>
                <option value="en-IN">English (India)</option>
                <option value="ta-IN">Tamil input aware</option>
              </select>
              <select
                value={accountDraft.responseStyle}
                onChange={(event) => setAccountDraft((current) => ({ ...current, responseStyle: event.target.value }))}
              >
                <option value="concise">Concise</option>
                <option value="balanced">Balanced</option>
                <option value="detailed">Detailed</option>
              </select>
              <select
                value={accountDraft.tone}
                onChange={(event) => setAccountDraft((current) => ({ ...current, tone: event.target.value }))}
              >
                <option value="friendly">Friendly</option>
                <option value="professional">Professional</option>
                <option value="empathetic">Empathetic</option>
              </select>
              <select
                value={accountDraft.theme}
                onChange={(event) => setAccountDraft((current) => ({ ...current, theme: event.target.value }))}
              >
                <option value="system">System</option>
                <option value="dark">Dark</option>
                <option value="light">Light</option>
              </select>
              <label className="toggle-line">
                <input
                  type="checkbox"
                  checked={Boolean(accountDraft.shortAnswers)}
                  onChange={(event) => setAccountDraft((current) => ({ ...current, shortAnswers: event.target.checked }))}
                />
                <span>Prefer shorter answers</span>
              </label>
            </div>
            <p>{`Current style: ${accountPreferences.response_style || "balanced"} | Tone: ${accountPreferences.tone || "friendly"}`}</p>
            <div className="action-grid compact two-col">
              <button className="action-button" onClick={saveAccountProfile} disabled={accountBusy}>
                {accountBusy ? "Saving..." : "Save Profile"}
              </button>
              <button className="action-button" onClick={() => runCommand("what are my settings")}>
                Profile Summary
              </button>
            </div>
          </>
        ) : (
          <p>Sign in to manage your account profile.</p>
        )}
      </SectionCard>

      <SectionCard title="Settings">
        <ul className="mini-list">
          <li>{`Wake word: ${uiState.settings.wake_word}`}</li>
          <li>{`Voice profile: ${uiState.settings.voice_profile}`}</li>
          <li>{`Offline mode: ${uiState.settings.offline_mode ? "On" : "Off"}`}</li>
          <li>{`Developer mode: ${uiState.settings.developer_mode ? "On" : "Off"}`}</li>
          <li>{`Emergency mode: ${uiState.settings.emergency_mode ? "On" : "Off"}`}</li>
          <li>{`Focus mode: ${uiState.settings.focus_mode ? "On" : "Off"}`}</li>
        </ul>
        <div className="action-grid compact two-col">
          <button className="action-button" onClick={() => runCommand("show settings")}>Show Settings</button>
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
      </SectionCard>

      <SectionCard title="Proactive">
        <p>{proactive.summary || "No proactive summary yet."}</p>
        {proactiveSuggestions.length ? (
          <ul className="mini-list compact-list">
            {proactiveSuggestions.slice(0, 3).map((item, index) => (
              <li key={`sidebar-proactive-${index}`}>{item.text}</li>
            ))}
          </ul>
        ) : (
          <p>No suggestions yet.</p>
        )}
        <div className="action-grid">
          <button className="action-button" onClick={() => runCommand("plan my day")}>Plan My Day</button>
          <button className="action-button" onClick={() => runCommand("what should i do now")}>What Now</button>
          <button className="action-button" onClick={() => runCommand("show proactive suggestions")}>Show Suggestions</button>
          <button className="action-button" onClick={() => runCommand("refresh proactive suggestions")}>Refresh Suggestions</button>
        </div>
      </SectionCard>

      <SectionCard title="Integrations">
        <ul className="mini-list compact-list">
          <li>{hardware.capabilities?.summary || "Hardware status unavailable."}</li>
          <li>{smartHome.summary || "Smart Home status unavailable."}</li>
          <li>{`Smart devices: ${smartHome.discovered_count || 0} | Control ready: ${smartHome.control_ready_count || 0}`}</li>
          <li>{faceSecurity.summary || "Face security status unavailable."}</li>
        </ul>
        <div className="command-chips">
          {(smartHome.sample_commands || []).slice(0, 2).map((item) => (
            <button key={`sidebar-iot-${item}`} className="chip-button" onClick={() => runCommand(item)}>
              {item}
            </button>
          ))}
        </div>
        <div className="action-grid">
          <button className="action-button" onClick={() => runCommand("smart home status")}>Smart Home</button>
          <button className="action-button" onClick={() => runCommand("iot inventory")}>IoT Inventory</button>
          <button className="action-button" onClick={() => runCommand("piper setup status")}>Piper Setup</button>
          <button className="action-button" onClick={() => runCommand("face security status")}>Face Security</button>
          <button className="action-button" onClick={() => runCommand("enroll my face")}>Enroll Face</button>
          <button className="action-button" onClick={() => runCommand("verify my face")}>Verify Face</button>
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
          <button className="action-button" onClick={() => activeContact ? runCommand(`call ${activeContact}`) : null}>Call Contact</button>
          <button className="action-button" onClick={() => activeContact ? runCommand(`message to ${activeContact} saying hi`) : null}>Message Contact</button>
          <button className="action-button" onClick={() => activeContact ? runCommand(`mail ${activeContact} about today plan`) : null}>Mail Contact</button>
          <button className="action-button" onClick={() => activeContact ? runCommand(`favorite contact ${activeContact}`) : null}>Favorite Contact</button>
          <button className="action-button" onClick={() => activeContact ? runCommand(`unfavorite contact ${activeContact}`) : null}>Unfavorite Contact</button>
          <button className="action-button" onClick={() => runCommand("sync google contacts")}>Sync Contacts</button>
          <button className="action-button" onClick={() => runCommand("show google contact changes")}>Contact Changes</button>
        </div>
        <div className="stack-form compact-gap">
          <input value={contactAlias} onChange={(event) => setContactAlias(event.target.value)} placeholder="Alias (appa, bro...)" />
          <input value={contactAliasTarget} onChange={(event) => setContactAliasTarget(event.target.value)} placeholder="Exact contact name" />
          <button onClick={() => contactAlias.trim() && contactAliasTarget.trim() ? runCommand(`set contact alias ${contactAlias} to ${contactAliasTarget}`.trim()) : null}>Save Alias</button>
          <button onClick={() => contactAlias.trim() ? runCommand(`remove contact alias ${contactAlias}`.trim()) : null}>Remove Alias</button>
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
          <button className={startupState.auto_launch_enabled ? "soft danger" : "soft success"} onClick={() => updateStartupSettings({ auto_launch_enabled: !startupState.auto_launch_enabled })}>
            {startupState.auto_launch_enabled ? "Disable Auto Launch" : "Enable Auto Launch"}
          </button>
          <button className={startupState.tray_mode ? "soft active" : "soft"} onClick={() => updateStartupSettings({ tray_mode: !startupState.tray_mode })}>
            {startupState.tray_mode ? "Tray Startup On" : "Tray Startup Off"}
          </button>
          <button className="soft" onClick={() => runCommand("open react ui")}>Open React Browser UI</button>
          <button className="soft" onClick={() => runCommand("open react desktop")}>Open React Desktop UI</button>
        </div>
      </SectionCard>
    </aside>
  );
}
