import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { getMe, getMyPages, type UserProfile, type PageSummary } from "../api";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { PageCard } from "../components/PageCard";

export function Dashboard() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [pages, setPages] = useState<PageSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [u, p] = await Promise.all([getMe(), getMyPages()]);
      setUser(u);
      setPages(p);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <LoadingSpinner message="Loading dashboard..." />;
  if (error) return <ErrorMessage error={error} onRetry={load} />;

  return (
    <div className="dashboard">
      <section className="section">
        <h2>Personal Page</h2>
        {user?.default_personal_page_id ? (
          <p>
            <Link to={`/p/${user.default_personal_page_id}`}>
              View your personal page
            </Link>
          </p>
        ) : (
          <p className="placeholder">
            You don't have a personal page yet.
          </p>
        )}
      </section>

      <section className="section">
        <h2>My Pages</h2>
        {pages && pages.length > 0 ? (
          <ul className="page-list">
            {pages.map((page) => (
              <PageCard key={page.slug} page={page} />
            ))}
          </ul>
        ) : (
          <p className="placeholder">No pages yet.</p>
        )}
      </section>
    </div>
  );
}
