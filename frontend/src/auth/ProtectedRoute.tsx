import { ReactNode } from "react";
import { useAuth } from "./AuthProvider";

interface Props {
  children: ReactNode;
  require?: string; // permission string e.g. "admin"
}

export function ProtectedRoute({ children, require: perm }: Props) {
  const { account, permissions, loading, login } = useAuth();

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", color: "var(--text-muted)" }}>
        Loading…
      </div>
    );
  }

  if (!account) {
    login();
    return null;
  }

  if (perm && !permissions.includes(perm)) {
    return (
      <div style={{ padding: "40px", color: "var(--text-secondary)" }}>
        You don't have permission to view this page.
      </div>
    );
  }

  return <>{children}</>;
}