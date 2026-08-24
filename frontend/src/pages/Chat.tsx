import { useState } from "react";
import { api } from "../api/client";
import type { ChatMessage } from "../api/types";

const TOOL_LABELS: Record<string, string> = {
  search_animals: "durchsucht Tierbestand",
  get_animal_detail: "lädt Tierdetails",
  get_siblings: "sucht Geschwister",
  find_weak_category: "sucht schwache Bewertungen",
  list_breeds: "listet Rassen",
};

function bubbleText(content: ChatMessage["content"]): string {
  return content
    .filter((b) => b.type === "text")
    .map((b) => b.text ?? "")
    .join("\n")
    .trim();
}

function toolCalls(content: ChatMessage["content"]): string[] {
  return content.filter((b) => b.type === "tool_use").map((b) => TOOL_LABELS[b.name ?? ""] ?? b.name ?? "");
}

export function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    setError(null);
    const next = [...messages, { role: "user" as const, content: [{ type: "text", text }] }];
    setMessages(next);
    setInput("");
    setSending(true);
    try {
      const res = await api.chat.send(next);
      setMessages(res.messages);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  const displayMessages = messages.filter((m) => bubbleText(m.content) || toolCalls(m.content).length > 0);

  return (
    <div>
      <h1>Zucht-Assistent</h1>
      <p className="hint" style={{ marginBottom: 16 }}>
        Fragen zu deinem Bestand ("welche Tiere haben eine schwache Fellbewertung?", "zeig mir die
        Geschwister von 45245") oder allgemeine Zuchtfragen.
      </p>

      <div className="card section" style={{ minHeight: 300 }}>
        {displayMessages.length === 0 && <p className="empty-state">Noch keine Nachrichten.</p>}
        <div className="list">
          {displayMessages.map((m, i) => (
            <div
              key={i}
              className="card"
              style={{
                background: m.role === "user" ? "var(--color-primary-soft)" : "var(--color-surface)",
                marginLeft: m.role === "user" ? "15%" : 0,
                marginRight: m.role === "user" ? 0 : "15%",
              }}
            >
              {toolCalls(m.content).length > 0 && (
                <div className="hint" style={{ marginBottom: 4 }}>
                  🔧 {toolCalls(m.content).join(", ")}…
                </div>
              )}
              {bubbleText(m.content) && <div style={{ whiteSpace: "pre-wrap" }}>{bubbleText(m.content)}</div>}
            </div>
          ))}
          {sending && <p className="hint">Antwort wird erstellt…</p>}
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <form className="toolbar" onSubmit={handleSend}>
        <input
          type="text"
          placeholder="Frag den Zucht-Assistenten…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={sending}
          style={{ flex: 1 }}
        />
        <button className="btn" type="submit" disabled={sending || !input.trim()}>
          Senden
        </button>
      </form>
    </div>
  );
}
