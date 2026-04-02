import MessageBubble from "./MessageBubble";
import { useRef } from "react";

export default function ChatSurface({
  messages,
  filteredMessages,
  chatSearch,
  setChatSearch,
  quickSuggestions,
  liveSuggestions,
  input,
  setInput,
  showAutocomplete,
  activeSuggestionIndex,
  setActiveSuggestionIndex,
  applySuggestion,
  pinCommand,
  handleSend,
  isChatLoading,
  clearConversation,
  reloadWorkspace,
  apiError,
  messagesEndRef,
  chatSessions,
  currentSessionId,
  createSession,
  switchSession,
  regenerateReply,
  cancelStreaming,
  retryLastPrompt,
  lastPrompt,
  showChatSettings,
  setShowChatSettings,
  chatSettingsDraft,
  setChatSettingsDraft,
  saveChatSettings,
  renameSession,
  deleteSession,
  exportSession,
  pendingConfirmation,
  confirmPendingAction,
  attachedDocuments,
  uploadChatDocument,
  removeChatDocument,
}) {
  const fileInputRef = useRef(null);
  const isApiHealthy = !apiError;
  const activeSession = chatSessions.find((session) => session.id === currentSessionId);
  const activeSessionLabel = activeSession?.title ? `Chat: ${activeSession.title}` : "Chat: New";

  return (
    <div className="chat-surface-grid">
      <aside className="chat-session-rail">
        <div className="chat-session-head">
          <h3>Chats</h3>
          <button className="ghost-button" onClick={createSession}>New</button>
        </div>
        <div className="chat-session-list">
          {chatSessions.length ? (
            chatSessions.map((session) => (
              <button
                key={session.id}
                className={currentSessionId === session.id ? "session-item active" : "session-item"}
                onClick={() => switchSession(session.id)}
              >
                <strong>{session.title || "New chat"}</strong>
                <span>{session.message_count || 0} messages</span>
                <div className="session-inline-actions">
                  <button
                    type="button"
                    className="mini-ghost"
                    onClick={(event) => {
                      event.stopPropagation();
                      renameSession(session);
                    }}
                  >
                    Rename
                  </button>
                  <button
                    type="button"
                    className="mini-ghost danger-text"
                    onClick={(event) => {
                      event.stopPropagation();
                      deleteSession(session.id);
                    }}
                  >
                    Delete
                  </button>
                </div>
              </button>
            ))
          ) : (
            <div className="session-empty">No chats yet.</div>
          )}
        </div>
        <div className="chat-session-actions">
          <button className="ghost-button" onClick={() => setShowChatSettings((value) => !value)}>
            {showChatSettings ? "Close Settings" : "AI Settings"}
          </button>
          <button className="ghost-button" onClick={exportSession} disabled={!currentSessionId}>
            Export
          </button>
          <button className="ghost-button danger" onClick={clearConversation}>Clear</button>
        </div>
      </aside>

      <div className="chat-main-shell">
        <div className="conversation-toolbar">
          <div className="surface-tabs">
            <span className="surface-kicker">Conversation</span>
            <span className="surface-session-label">{activeSessionLabel}</span>
          </div>
          <div className="conversation-status-row">
            <span className={isChatLoading ? "status-pill busy" : "status-pill idle"}>
              {isChatLoading ? "Assistant thinking" : "Ready"}
            </span>
            <span className={isApiHealthy ? "status-pill ok" : "status-pill error"}>
              {isApiHealthy ? "API connected" : "API issue"}
            </span>
          </div>
          <div className="conversation-actions">
            <button className="ghost-button" onClick={reloadWorkspace} disabled={isChatLoading}>Reload</button>
            <button className="ghost-button" onClick={regenerateReply} disabled={!currentSessionId || isChatLoading}>Regenerate</button>
            <button className="ghost-button" onClick={retryLastPrompt} disabled={!lastPrompt || isChatLoading}>Retry</button>
            <button className="ghost-button danger" onClick={cancelStreaming} disabled={!isChatLoading}>Cancel</button>
          </div>
        </div>

        {showChatSettings ? (
          <section className="chat-settings-panel">
            {!chatSettingsDraft?.llm_status?.ready ? (
              <div className="llm-status-card">
                <strong>AI Setup Needed</strong>
                <span>Set `OPENAI_API_KEY` in the project root `.env` file, then restart the app.</span>
                <small>{`Provider: ${chatSettingsDraft?.llm_status?.provider || "openai-compatible"} | Model: ${chatSettingsDraft?.llm_status?.model || chatSettingsDraft.model}`}</small>
              </div>
            ) : null}
            <div className="llm-status-card compact">
              <strong>{`Active Provider: ${chatSettingsDraft?.llm_status?.provider || chatSettingsDraft?.llm_provider || "ollama"}`}</strong>
              <span>{`Current model: ${chatSettingsDraft?.llm_status?.model || chatSettingsDraft?.ollama_model || chatSettingsDraft?.model}`}</span>
              <small>{`Fallback ready: ${chatSettingsDraft?.llm_status?.fallback_available ? "Yes" : "No"}`}</small>
            </div>
            <div className="chat-settings-grid">
              <label>
                <span>Provider</span>
                <select
                  value={chatSettingsDraft.llm_provider || "ollama"}
                  onChange={(event) => setChatSettingsDraft((current) => ({ ...current, llm_provider: event.target.value }))}
                >
                  <option value="ollama">Ollama Local</option>
                  <option value="openai">OpenAI</option>
                  <option value="auto">Auto Fallback</option>
                </select>
              </label>
              <label>
                <span>OpenAI Model</span>
                <input
                  value={chatSettingsDraft.model}
                  onChange={(event) => setChatSettingsDraft((current) => ({ ...current, model: event.target.value }))}
                  placeholder="gpt-4.1-mini"
                />
              </label>
              <label>
                <span>Ollama Model</span>
                <select
                  value={chatSettingsDraft.ollama_model || "llama3:8b"}
                  onChange={(event) => setChatSettingsDraft((current) => ({ ...current, ollama_model: event.target.value }))}
                >
                  <option value="llama3:8b">llama3:8b</option>
                  <option value="phi3:latest">phi3:latest</option>
                </select>
              </label>
              <label>
                <span>Tone</span>
                <input
                  value={chatSettingsDraft.tone}
                  onChange={(event) => setChatSettingsDraft((current) => ({ ...current, tone: event.target.value }))}
                  placeholder="friendly"
                />
              </label>
              <label>
                <span>Response Style</span>
                <input
                  value={chatSettingsDraft.response_style}
                  onChange={(event) => setChatSettingsDraft((current) => ({ ...current, response_style: event.target.value }))}
                  placeholder="balanced"
                />
              </label>
              <label className="toggle-row">
                <span>Tool-aware mode</span>
                <input
                  type="checkbox"
                  checked={chatSettingsDraft.tool_mode}
                  onChange={(event) => setChatSettingsDraft((current) => ({ ...current, tool_mode: event.target.checked }))}
                />
              </label>
              <label className="prompt-field">
                <span>System Prompt</span>
                <textarea
                  value={chatSettingsDraft.system_prompt}
                  onChange={(event) => setChatSettingsDraft((current) => ({ ...current, system_prompt: event.target.value }))}
                  rows={4}
                />
              </label>
            </div>
            <div className="chat-settings-actions">
              <button className="ghost-button" onClick={saveChatSettings}>Save Settings</button>
            </div>
          </section>
        ) : null}

        {isChatLoading ? (
          <div className="status-banner info">Working on your request. You can cancel if it takes too long.</div>
        ) : null}
        {apiError ? <div className="status-banner error">{apiError}</div> : null}
        {pendingConfirmation ? (
          <div className="confirmation-bar">
            <span>{`Confirm action: ${pendingConfirmation.command}`}</span>
            <button className="ghost-button danger" onClick={confirmPendingAction}>Confirm</button>
          </div>
        ) : null}

        {attachedDocuments?.length ? (
          <div className="attachment-strip">
            <div className="attachment-strip-head">
              <span>{`Attached docs (${attachedDocuments.length})`}</span>
              <small>Remove old docs to keep answers focused.</small>
            </div>
            <div className="attachment-chips">
              {attachedDocuments.map((item) => (
                <div key={item.id} className="attachment-chip">
                  <div className="attachment-copy">
                    <strong>{item.name}</strong>
                    <span>{`${item.kind.toUpperCase()} | ${item.chunk_count || 0} chunks | ${item.char_count || 0} chars`}</span>
                  </div>
                  <button
                    type="button"
                    className="mini-ghost danger-text"
                    onClick={() => removeChatDocument(item.name)}
                    title="Remove document"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        <div className="messages">
          <div className="chat-search-bar">
            <input
              value={chatSearch}
              onChange={(event) => setChatSearch(event.target.value)}
              placeholder="Search conversation..."
            />
          </div>
          {filteredMessages.length ? (
            filteredMessages.map((message) => (
              <MessageBubble
                key={message.id}
                side={message.side}
                text={message.text}
                createdAt={message.createdAt}
                streaming={message.streaming}
              />
            ))
          ) : (
            <div className="empty-chat">
              <span className="empty-kicker">Assistant ready</span>
              <h3>Start with a simple command</h3>
              <p>Try asking about weather, planning your day, notes, reminders, or desktop actions.</p>
              <div className="command-chips">
                {quickSuggestions.slice(0, 4).map((item) => (
                  <button key={`empty-${item}`} className="chip-button" onClick={() => handleSend(item)}>
                    {item}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {input.trim() ? (
          <div className="suggestion-strip">
            <span>Suggestions</span>
            <div className="command-chips">
              {liveSuggestions.length ? (
                liveSuggestions.map((item) => (
                  <button key={`suggest-${item}`} className="chip-button small" onClick={() => applySuggestion(item)}>
                    {item}
                  </button>
                ))
              ) : (
                <button className="chip-button small" onClick={() => setInput("")}>Clear input</button>
              )}
            </div>
          </div>
        ) : null}

        <footer className="composer">
          <div className="composer-stack">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="hidden-file-input"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  uploadChatDocument(file);
                }
                event.target.value = "";
              }}
            />
            <button
              type="button"
              className="composer-plus"
              onClick={() => fileInputRef.current?.click()}
              title="Upload PDF, DOCX, or TXT"
              disabled={isChatLoading}
            >
              +
            </button>
            <div className="composer-input-wrap">
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Tab" && showAutocomplete) {
                    event.preventDefault();
                    applySuggestion(liveSuggestions[activeSuggestionIndex] || input);
                    return;
                  }
                  if (event.key === "ArrowDown" && showAutocomplete) {
                    event.preventDefault();
                    setActiveSuggestionIndex((current) => (current >= liveSuggestions.length - 1 ? 0 : current + 1));
                    return;
                  }
                  if (event.key === "ArrowUp" && showAutocomplete) {
                    event.preventDefault();
                    setActiveSuggestionIndex((current) => (current <= 0 ? liveSuggestions.length - 1 : current - 1));
                    return;
                  }
                  if (event.key === "Enter" && showAutocomplete) {
                    event.preventDefault();
                    applySuggestion(liveSuggestions[activeSuggestionIndex] || input);
                    return;
                  }
                  if (event.key === "Enter") {
                    event.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Type a command, question, or task..."
              />
              {showAutocomplete ? (
                <div className="autocomplete-panel">
                  {liveSuggestions.map((item, index) => (
                    <button
                      key={`autocomplete-${item}`}
                      className={activeSuggestionIndex === index ? "autocomplete-item active" : "autocomplete-item"}
                      onClick={() => applySuggestion(item)}
                      onDoubleClick={() => pinCommand(item)}
                    >
                      <strong>{item}</strong>
                      <span>Use or double-click to pin</span>
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
            <button onClick={() => handleSend()} disabled={isChatLoading}>
              {isChatLoading ? "Working..." : input.trim() ? "Send" : "Run"}
            </button>
          </div>
          <div className="composer-hint">
            {attachedDocuments?.length
              ? `${attachedDocuments.length} document(s) attached for RAG.`
              : "No documents attached. Upload PDF, DOCX, or TXT to ask file-based questions."}
          </div>
        </footer>
      </div>
    </div>
  );
}

