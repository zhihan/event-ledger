import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { acceptInvite, getPublicInviteInfo, getRoom } from "../api";
import { useAuth } from "../auth";
import { LoadingSpinner } from "../components/LoadingSpinner";

const ACCEPT_INVITE_TIMEOUT_MS = 15000;

export function AcceptInvite() {
  const { inviteId } = useParams<{ inviteId: string }>();
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState(false);
  const [roomTitle, setRoomTitle] = useState<string | null>(null);
  const [roomId, setRoomId] = useState<string | null>(null);
  const [inviteInfoLoaded, setInviteInfoLoaded] = useState(false);
  const [checkingMembership, setCheckingMembership] = useState(false);
  const [alreadyAccepted, setAlreadyAccepted] = useState(false);

  useEffect(() => {
    if (!inviteId || authLoading) return;
    let cancelled = false;
    setInviteInfoLoaded(false);
    setCheckingMembership(Boolean(user));
    setAlreadyAccepted(false);
    setRoomTitle(null);
    setRoomId(null);

    getPublicInviteInfo(inviteId)
      .then(async (info) => {
        if (cancelled) return;
        setRoomTitle(info.room_title);
        setRoomId(info.room_id);

        if (!user) return;
        try {
          await getRoom(info.room_id);
          if (!cancelled) setAlreadyAccepted(true);
        } catch {
          // Not a member yet, or membership lookup is unavailable. Keep normal invite flow.
        }
      })
      .catch(() => {}) // non-critical, fall back to generic text
      .finally(() => {
        if (!cancelled) {
          setInviteInfoLoaded(true);
          setCheckingMembership(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [authLoading, inviteId, user]);

  async function doAccept() {
    if (!inviteId) return;
    setStarted(true);
    setError(null);
    try {
      const result = await Promise.race([
        acceptInvite(inviteId),
        new Promise<never>((_, reject) => {
          window.setTimeout(() => {
            reject(new Error("Invite acceptance timed out. Retry or open Dashboard to check whether it already succeeded."));
          }, ACCEPT_INVITE_TIMEOUT_MS);
        }),
      ]);
      navigate(`/room/${result.room_id}`, { replace: true });
    } catch (err) {
      console.error("Failed to accept invite:", err);
      setError(err instanceof Error ? err.message : "Failed to accept invite");
    }
  }

  if (error) {
    return (
      <div className="invite-page">
        <h2>Invite Error</h2>
        <p className="form-error">{error}</p>
        <div className="invite-actions">
          <button className="btn btn-primary btn-sm" onClick={doAccept}>
            Retry
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => navigate("/dashboard")}
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (
    !started &&
    (authLoading || (user && !inviteInfoLoaded) || checkingMembership)
  ) {
    return <LoadingSpinner message="Loading invite..." />;
  }

  if (alreadyAccepted && roomId) {
    return (
      <div className="invite-page">
        <h2>You already accepted</h2>
        <p>
          {roomTitle
            ? <>You already joined <strong>{roomTitle}</strong>.</>
            : "You already joined this room."}
        </p>
        <button
          className="btn btn-primary"
          onClick={() => navigate(`/room/${roomId}`, { replace: true })}
        >
          Open Room
        </button>
      </div>
    );
  }

  if (!started) {
    return (
      <div className="invite-page">
        <h2>You've been invited!</h2>
        <p>
          {roomTitle
            ? <>Click below to join <strong>{roomTitle}</strong>.</>
            : "Click below to join this room."}
        </p>
        <button className="btn btn-primary" onClick={doAccept}>
          Accept Invite
        </button>
      </div>
    );
  }

  return <LoadingSpinner message="Accepting invite..." />;
}
