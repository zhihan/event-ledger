import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth";
import { getMe } from "../api";

export function SignIn() {
  const { user, loading, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/dashboard";

  useEffect(() => {
    if (!loading && user) {
      // Ensure user profile exists in backend, then redirect back
      getMe()
        .then(() => navigate(from, { replace: true }))
        .catch(() => navigate(from, { replace: true }));
    }
  }, [user, loading, navigate, from]);

  if (loading) {
    return <div className="loading-screen">Loading...</div>;
  }

  return (
    <div className="sign-in">
      <h1>Sign in</h1>
      <button type="button" onClick={signIn} className="btn btn-primary">
        Sign in with Google
      </button>
    </div>
  );
}
