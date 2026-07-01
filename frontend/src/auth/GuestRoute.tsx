import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export default function GuestRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="card"><p>Loading…</p></div>;
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
