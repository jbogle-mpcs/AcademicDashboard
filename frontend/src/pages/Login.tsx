import { useAuth } from "../auth/AuthProvider";

export function Login() {
  const { login } = useAuth();

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg)",
      }}
    >
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 10,
          padding: "48px 56px",
          maxWidth: 380,
          width: "100%",
          textAlign: "center",
          boxShadow: "var(--shadow-md)",
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            background: "var(--navy)",
            borderRadius: 10,
            margin: "0 auto 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span style={{ color: "var(--amber)", fontSize: 22, fontWeight: 700 }}>A</span>
        </div>
        <h1 style={{ fontSize: 18, fontWeight: 600, marginBottom: 6 }}>
          Achievement Dashboard
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 32 }}>
          Sign in with your school Microsoft account to continue.
        </p>
        <button
          onClick={login}
          style={{
            width: "100%",
            padding: "11px 0",
            background: "var(--navy)",
            color: "#fff",
            borderRadius: "var(--radius)",
            fontSize: 14,
            fontWeight: 600,
            border: "none",
            cursor: "pointer",
            transition: "background 0.15s",
          }}
          onMouseEnter={(e) => ((e.target as HTMLElement).style.background = "var(--navy-light)")}
          onMouseLeave={(e) => ((e.target as HTMLElement).style.background = "var(--navy)")}
        >
          Sign in with Microsoft
        </button>
        <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 20 }}>
          Access is restricted to authorised school staff.
        </p>
      </div>
    </div>
  );
}