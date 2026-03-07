import { useState, useRef, useEffect } from "react";
import { sendChat } from "../services/api";
import { useI18n } from "../i18n";
import type { ChatMessage } from "../types/product";

export default function Chat() {
  const { t } = useI18n();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    const updated = [...messages, userMsg];
    setMessages(updated);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChat(text, updated);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.reply },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Failed to get a response. Is the matcher service running?",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <h1>{t('chat.title')}</h1>
        <p>{t('chat.subtitle')}</p>
      </div>
      <div className="page-body">
        <div
          className="card"
          style={{
            display: "flex",
            flexDirection: "column",
            height: "calc(100vh - 180px)",
            padding: 0,
            overflow: "hidden",
          }}
        >
          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflow: "auto",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            {messages.length === 0 && (
              <div className="empty-state" style={{ margin: "auto" }}>
                <div className="empty-icon">
                  <svg
                    width="48"
                    height="48"
                    viewBox="0 0 48 48"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    opacity="0.3"
                  >
                    <rect x="4" y="4" width="40" height="30" rx="6" />
                    <path d="M14 40L20 34H28L34 40" />
                    <line x1="14" y1="16" x2="34" y2="16" />
                    <line x1="14" y1="22" x2="28" y2="22" />
                  </svg>
                </div>
                <h3>Ask me anything</h3>
                <p>
                  Try "Find Samsung TVs under 500" or "Which products are
                  unmatched?" or "Compare P_1234 with P_5678"
                </p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent:
                    msg.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    maxWidth: "75%",
                    padding: "12px 16px",
                    borderRadius: "var(--radius-md)",
                    background:
                      msg.role === "user"
                        ? "var(--stone-800)"
                        : "var(--cream-200)",
                    color:
                      msg.role === "user"
                        ? "var(--cream-100)"
                        : "var(--stone-800)",
                    fontSize: "0.9rem",
                    lineHeight: 1.6,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <div
                  style={{
                    padding: "12px 16px",
                    borderRadius: "var(--radius-md)",
                    background: "var(--cream-200)",
                  }}
                >
                  <span className="spinner" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div
            style={{
              padding: "16px 24px",
              borderTop: "1px solid var(--cream-300)",
              display: "flex",
              gap: "10px",
            }}
          >
            <input
              className="input-field"
              style={{ flex: 1 }}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Type a message..."
              disabled={loading}
            />
            <button
              className="btn btn-primary"
              onClick={handleSend}
              disabled={loading || !input.trim()}
            >
              {t('common.send')}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}