import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth";
import { getMe } from "../api";

export function SignIn() {
  const { user, loading, signIn } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirect = searchParams.get("redirect") || "/dashboard";

  useEffect(() => {
    if (!loading && user) {
      // Ensure user profile exists in backend, then redirect back
      getMe()
        .then(() => navigate(redirect, { replace: true }))
        .catch(() => navigate(redirect, { replace: true }));
    }
  }, [user, loading, navigate, redirect]);

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
