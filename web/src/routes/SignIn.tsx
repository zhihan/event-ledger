import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { getMe } from "../api";

export function SignIn() {
  const { user, loading, signIn } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) {
      // Ensure user profile exists in backend, then go to dashboard
      getMe()
        .then(() => navigate("/dashboard", { replace: true }))
        .catch(() => navigate("/dashboard", { replace: true }));
    }
  }, [user, loading, navigate]);

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
