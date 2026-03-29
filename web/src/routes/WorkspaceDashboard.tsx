import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  getMyWorkspaces,
  createWorkspace,
  type WorkspaceSummary,
} from "../api";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { TimezoneSelect } from "../components/TimezoneSelect";

export function WorkspaceDashboard() {
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [formTitle, setFormTitle] = useState("");
  const [formTimezone, setFormTimezone] = useState(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const ws = await getMyWorkspaces();
      setWorkspaces(ws);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!formTitle.trim()) return;
    setFormSubmitting(true);
    setFormError(null);
    try {
      await createWorkspace(formTitle.trim(), "shared", formTimezone);
      setShowForm(false);
      setFormTitle("");
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create workspace");
    } finally {
      setFormSubmitting(false);
    }
  }

  if (loading) return <LoadingSpinner message="Loading workspaces..." />;
  if (error) return <ErrorMessage error={error} onRetry={load} />;

  return (
    <div className="dashboard">
      <section className="section">
        <div className="section-header">
          <h2>My Workspaces</h2>
          {!showForm && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setShowForm(true)}
            >
              + New
            </button>
          )}
        </div>

        {showForm && (
          <form className="create-page-form" onSubmit={handleCreate}>
            <div className="form-field">
              <label htmlFor="ws-title">Name</label>
              <input
                id="ws-title"
                type="text"
                className="form-input"
                value={formTitle}
                onChange={(e) => setFormTitle(e.target.value)}
                placeholder="e.g. Weekly Team Sync"
                required
                autoFocus
                disabled={formSubmitting}
              />
            </div>
            <div className="form-field">
              <label htmlFor="ws-tz">Timezone</label>
              <TimezoneSelect
                id="ws-tz"
                value={formTimezone}
                onChange={setFormTimezone}
              />
            </div>
            {formError && <p className="form-error">{formError}</p>}
            <div className="form-actions">
              <button
                type="submit"
                className="btn btn-primary btn-sm"
                disabled={formSubmitting || !formTitle.trim()}
              >
                {formSubmitting ? "Creating..." : "Create"}
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => { setShowForm(false); setFormError(null); }}
                disabled={formSubmitting}
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {workspaces && workspaces.length > 0 ? (
          <ul className="page-list">
            {workspaces.map((ws) => (
              <WorkspaceCard key={ws.workspace_id} workspace={ws} />
            ))}
          </ul>
        ) : (
          !showForm && (
            <p className="placeholder">
              No workspaces yet. Create one to start scheduling.
            </p>
          )
        )}
      </section>
    </div>
  );
}

function WorkspaceCard({ workspace }: { workspace: WorkspaceSummary }) {
  return (
    <li className="page-card workspace-card">
      <Link to={`/w/${workspace.workspace_id}`}>
        <strong>{workspace.title}</strong>
      </Link>
      <p className="page-meta-tz">{workspace.timezone}</p>
    </li>
  );
}
