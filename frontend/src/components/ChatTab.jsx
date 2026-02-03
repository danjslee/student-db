import { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "../api";

export default function ChatTab() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res = await sendChatMessage(text);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          sql: res.sql || null,
          data: res.data || null,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="chat-placeholder">
            Ask a question about the student database...
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg chat-msg-${msg.role}`}>
            <div className="chat-bubble">
              <p>{msg.content}</p>
              {msg.sql && (
                <details className="chat-sql">
                  <summary>SQL Query</summary>
                  <pre><code>{msg.sql}</code></pre>
                </details>
              )}
              {msg.data && msg.data.length > 0 && (
                <div className="chat-data-wrapper">
                  <table className="chat-data-table">
                    <thead>
                      <tr>
                        {Object.keys(msg.data[0]).map((col) => (
                          <th key={col}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {msg.data.slice(0, 50).map((row, ri) => (
                        <tr key={ri}>
                          {Object.values(row).map((val, ci) => (
                            <td key={ci}>{val == null ? "" : String(val)}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {msg.data.length > 50 && (
                    <p className="chat-data-note">
                      Showing 50 of {msg.data.length} rows
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-msg chat-msg-assistant">
            <div className="chat-bubble chat-loading-bubble">Thinking...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input-bar">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question..."
          disabled={loading}
          className="chat-input"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="chat-send-btn"
        >
          Send
        </button>
      </div>
    </div>
  );
}
