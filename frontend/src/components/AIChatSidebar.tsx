"use client";

import { type KeyboardEvent } from "react";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type AIChatSidebarProps = {
  messages: ChatMessage[];
  input: string;
  isSending: boolean;
  errorMessage: string | null;
  onInputChange: (value: string) => void;
  onSend: () => void;
};

export const AIChatSidebar = ({
  messages,
  input,
  isSending,
  errorMessage,
  onInputChange,
  onSend,
}: AIChatSidebarProps) => {
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  return (
    <aside
      className="flex h-full flex-col gap-4 rounded-[32px] border border-[var(--stroke)] bg-white/85 p-6 shadow-[var(--shadow)] backdrop-blur"
      data-testid="ai-chat"
    >
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--gray-text)]">
            AI Studio
          </p>
          <h2 className="mt-2 font-display text-2xl font-semibold text-[var(--navy-dark)]">
            Board Copilot
          </h2>
          <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
            Ask the assistant to create, move, or refine cards. Changes apply immediately.
          </p>
        </div>
        {isSending ? (
          <span className="rounded-full border border-[var(--primary-blue)] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--primary-blue)]">
            Thinking
          </span>
        ) : null}
      </header>

      <div className="flex-1 overflow-hidden">
        <div className="flex h-full flex-col gap-3 overflow-y-auto pr-1">
          {messages.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[var(--stroke)] bg-[var(--surface)] p-4 text-sm text-[var(--gray-text)]">
              No messages yet. Start with something like "Move card-1 to Done.".
            </div>
          ) : null}
          {messages.map((message, index) => (
            <div
              key={message.id}
              data-testid={`ai-message-${index}`}
              className={`rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${
                message.role === "user"
                  ? "self-end bg-[var(--primary-blue)] text-white"
                  : "self-start border border-[var(--stroke)] bg-white text-[var(--navy-dark)]"
              }`}
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] opacity-70">
                {message.role === "user" ? "You" : "Assistant"}
              </p>
              <p className="mt-2 whitespace-pre-wrap">{message.content}</p>
            </div>
          ))}
        </div>
      </div>

      {errorMessage ? (
        <p className="rounded-2xl border border-[rgba(117,57,145,0.3)] bg-[rgba(117,57,145,0.08)] px-4 py-3 text-sm text-[var(--secondary-purple)]">
          {errorMessage}
        </p>
      ) : null}

      <div className="rounded-2xl border border-[var(--stroke)] bg-white p-4">
        <label
          htmlFor="ai-message"
          className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
        >
          Ask the AI
        </label>
        <textarea
          id="ai-message"
          value={input}
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Summarize the backlog and move the top priority into Progress..."
          rows={4}
          className="mt-3 w-full resize-none rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
        />
        <div className="mt-3 flex items-center justify-between">
          <p className="text-xs text-[var(--gray-text)]">
            Press Enter to send. Shift+Enter for a new line.
          </p>
          <button
            type="button"
            disabled={isSending}
            onClick={onSend}
            className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSending ? "Sending..." : "Send"}
          </button>
        </div>
      </div>
    </aside>
  );
};
