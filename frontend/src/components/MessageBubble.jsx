export default function MessageBubble({ side, text, createdAt, streaming = false }) {
  const timeLabel = new Date(createdAt || Date.now()).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });

  const copyText = async () => {
    if (!text || side !== "assistant") return;
    await navigator.clipboard.writeText(text);
  };

  return (
    <div className={`message-row ${side}`}>
      <div className={`message-bubble ${side}`}>
        <div>{text}</div>
        <div className="message-meta">
          <small>{streaming ? "Typing..." : timeLabel}</small>
          {side === "assistant" && text ? (
            <button className="message-copy" onClick={copyText} type="button">
              Copy
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
