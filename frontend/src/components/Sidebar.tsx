import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";

const NAV = [
  { to: "/", label: "Dashboard", icon: "⊞" },
  { to: "/students", label: "Students", icon: "⊡" },
];

export function Sidebar() {
  const { account, permissions, logout } = useAuth();

  const displayName =
    account?.name?.split(" ").slice(0, 2).join(" ") ?? account?.username ?? "";

  return (
    <aside
      style={{
        width: "var(--sidebar-width)",
        minHeight: "100vh",
        background: "var(--navy)",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
      }}
    >
      {/* Wordmark */}
      <div
        style={{
          padding: "24px 20px 20px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div
          style={{
            fontWeight: 600,
            fontSize: 15,
            color: "#fff",
            lineHeight: 1.2,
          }}
        >
          Achievement
        </div>
        <div style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", marginTop: 2 }}>
          Dashboard
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: "12px 0", flex: 1 }}>
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            style={({ isActive }) => ({
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "9px 20px",
              fontSize: 13.5,
              fontWeight: isActive ? 600 : 400,
              color: isActive ? "#fff" : "rgba(255,255,255,0.55)",
              background: isActive ? "rgba(255,255,255,0.1)" : "transparent",
              borderLeft: isActive ? "3px solid var(--amber)" : "3px solid transparent",
              transition: "all 0.15s",
            })}
          >
            <span style={{ fontSize: 16, lineHeight: 1 }}>{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div
        style={{
          padding: "16px 20px",
          borderTop: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", marginBottom: 2 }}>
          {permissions.map((p) => p.replace("_", " ")).join(", ")}
        </div>
        <div style={{ fontSize: 13, color: "rgba(255,255,255,0.75)", marginBottom: 10 }}>
          {displayName}
        </div>
        <button
          onClick={logout}
          style={{
            fontSize: 12,
            color: "rgba(255,255,255,0.4)",
            padding: 0,
            transition: "color 0.15s",
          }}
          onMouseEnter={(e) => ((e.target as HTMLElement).style.color = "rgba(255,255,255,0.8)")}
          onMouseLeave={(e) => ((e.target as HTMLElement).style.color = "rgba(255,255,255,0.4)")}
        >
          Sign out →
        </button>
      </div>
    </aside>
  );
}