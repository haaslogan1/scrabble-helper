import { useState } from "react";
import { useLocation } from "react-router-dom";
import { submitFeedback } from "../api";

const MAX_MESSAGE_LENGTH = 2000;

export default function FeedbackButton() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [category, setCategory] = useState<"bug" | "idea" | "other" | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const isPlayPage = /^\/game\/\d+\/play/.test(location.pathname);
  const gameMatch = location.pathname.match(/^\/game\/(\d+)/);
  const gameId = gameMatch ? Number(gameMatch[1]) : undefined;

  function resetForm() {
    setMessage("");
    setCategory("");
    setError("");
    setSuccess(false);
  }

  function closeModal() {
    setOpen(false);
    resetForm();
  }

  function handleMessageChange(value: string) {
    setMessage(value.slice(0, MAX_MESSAGE_LENGTH));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await submitFeedback({
        message: message.trim(),
        category: category || undefined,
        page_url: location.pathname,
        game_id: gameId,
      });
      setSuccess(true);
      setTimeout(closeModal, 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className={`feedback-fab${isPlayPage ? " feedback-fab--play" : ""}`}
        onClick={() => setOpen(true)}
        aria-label="Send feedback"
        title="Send feedback"
      >
        💬
      </button>

      {open && (
        <div className="feedback-modal-overlay" onClick={closeModal} role="presentation">
          <div
            className="feedback-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-labelledby="feedback-modal-title"
            aria-modal="true"
          >
            <h2 id="feedback-modal-title">Send feedback</h2>
            {success ? (
              <p className="feedback-success">Thanks — your feedback was sent.</p>
            ) : (
              <form onSubmit={handleSubmit}>
                <label className="feedback-field">
                  Category
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value as typeof category)}
                  >
                    <option value="">General</option>
                    <option value="bug">Bug</option>
                    <option value="idea">Idea</option>
                    <option value="other">Other</option>
                  </select>
                </label>
                <label className="feedback-field">
                  Message
                  <textarea
                    value={message}
                    onChange={(e) => handleMessageChange(e.target.value)}
                    maxLength={MAX_MESSAGE_LENGTH}
                    rows={5}
                    placeholder="Tell us what you think…"
                    required
                  />
                  <span
                    className={`feedback-char-count${
                      message.length >= MAX_MESSAGE_LENGTH ? " feedback-char-count--limit" : ""
                    }`}
                  >
                    {message.length}/{MAX_MESSAGE_LENGTH}
                  </span>
                </label>
                {error && <p className="error-text">{error}</p>}
                <div className="btn-row">
                  <button type="button" className="btn secondary" onClick={closeModal}>
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn"
                    disabled={submitting || message.trim().length === 0}
                  >
                    {submitting ? "Sending…" : "Submit"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
