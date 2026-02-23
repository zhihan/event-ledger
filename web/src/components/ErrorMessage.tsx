import { Link } from "react-router-dom";
import { ApiError } from "../api";

export function ErrorMessage({
  error,
  onRetry,
}: {
  error: Error;
  onRetry?: () => void;
}) {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      return (
        <div className="error-container">
          <p className="error">This page is private.</p>
          <Link to="/dashboard">Back to dashboard</Link>
        </div>
      );
    }
    if (error.status === 404) {
      return (
        <div className="error-container">
          <p className="error">Page not found.</p>
          <Link to="/dashboard">Back to dashboard</Link>
        </div>
      );
    }
  }

  return (
    <div className="error-container">
      <p className="error">Unable to connect. Please try again.</p>
      {onRetry && (
        <button type="button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
