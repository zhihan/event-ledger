import { useState, type FormEvent } from "react";
import { createMemory } from "../api";

interface AddMemoryFormProps {
  slug: string;
  onSuccess: () => void;
}

export function AddMemoryForm({ slug, onSuccess }: AddMemoryFormProps) {
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = message.trim();
    if (!text) return;

    setSubmitting(true);
    setError(null);
    try {
      await createMemory(slug, text);
      setMessage("");
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add memory");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="add-memory-form" onSubmit={handleSubmit}>
      <div className="add-memory-input-row">
        <input
          type="text"
          className="add-memory-input"
          placeholder="What do you want to add to the events?"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={submitting}
        />
        <button
          type="submit"
          className="btn btn-primary"
          disabled={submitting || !message.trim()}
        >
          {submitting ? "Adding..." : "Add"}
        </button>
      </div>
      {error && (
        <div className="add-memory-error-box">
          <p className="add-memory-error">{error}</p>
          <button
            type="button"
            className="add-memory-error-dismiss"
            onClick={() => setError(null)}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      )}
    </form>
  );
}
