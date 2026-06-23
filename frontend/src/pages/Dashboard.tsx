import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getStudents, StudentSummary } from "../api/api";
import { useAuth } from "../auth/AuthProvider";

export function Dashboard() {
  const { account, permissions } = useAuth();
  const [recentStudents, setRecentStudents] = useState<StudentSummary[]>([]);

  useEffect(() => {
    getStudents({ limit: 5 }).then(setRecentStudents).catch(() => {});
  }, []);

  const name = account?.name?.split(" ")[0] ?? "there";

  return (
    <div style={{ padding: "36px 40px", maxWidth: 900 }}>
      {/* Header */}
      <div style={{ marginBottom: 36 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 4 }}>
          Good morning, {name}.
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
          Student Achievement Dashboard
          {permissions.length > 0 && (
            <span style={{ marginLeft: 10, fontSize: 12, color: "var(--text-muted)" }}>
              {permissions.map((p) => p.replace(/_/g, " ")).join(" · ")}
            </span>
          )}
        </p>
      </div>

      {/* Quick actions */}
      <div style={{ display: "flex", gap: 12, marginBottom: 40 }}>
        <QuickLink to="/students" label="Browse Students" desc="Search and filter the full roster" />
        <QuickLink to="/students?division=HS" label="High School" desc="Grades 9–12 students" />
        <QuickLink to="/students?division=MS" label="Middle School" desc="Grades 6–8 students" />
        <QuickLink to="/students?division=LS" label="Lower School" desc="Grades 1–5 students" />
      </div>

      {/* Recent students */}
      {recentStudents.length > 0 && (
        <div>
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-muted)",
              marginBottom: 12,
            }}
          >
            Students
          </div>
          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
              overflow: "hidden",
            }}
          >
            {recentStudents.map((s, i) => (
              <Link
                key={s.id}
                to={`/students/${s.id}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "12px 18px",
                  borderTop: i > 0 ? "1px solid var(--border)" : undefined,
                  gap: 12,
                  transition: "background 0.1s",
                }}
                onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "#fafaf9")}
                onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "transparent")}
              >
                <Avatar name={`${s.first_name} ${s.last_name}`} />
                <div>
                  <div style={{ fontWeight: 500, fontSize: 14 }}>
                    {s.preferred_name ?? s.first_name} {s.last_name}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                    {s.division && `${s.division} · `}
                    {s.grade ? `Grade ${s.grade}` : ""}
                    {s.student_id && ` · ${s.student_id}`}
                  </div>
                </div>
                <span style={{ marginLeft: "auto", fontSize: 18, color: "var(--border)" }}>›</span>
              </Link>
            ))}
            <Link
              to="/students"
              style={{
                display: "block",
                padding: "11px 18px",
                borderTop: "1px solid var(--border)",
                fontSize: 13,
                color: "var(--text-secondary)",
                background: "#fafaf9",
                textAlign: "center",
              }}
            >
              View all students →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

function QuickLink({ to, label, desc }: { to: string; label: string; desc: string }) {
  return (
    <Link
      to={to}
      style={{
        flex: 1,
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        padding: "16px 18px",
        display: "block",
        transition: "border-color 0.15s, box-shadow 0.15s",
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.borderColor = "var(--navy)";
        el.style.boxShadow = "var(--shadow-sm)";
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.borderColor = "var(--border)";
        el.style.boxShadow = "none";
      }}
    >
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{desc}</div>
    </Link>
  );
}

function Avatar({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase();

  return (
    <div
      style={{
        width: 34,
        height: 34,
        borderRadius: "50%",
        background: "var(--navy)",
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 12,
        fontWeight: 600,
        flexShrink: 0,
      }}
    >
      {initials}
    </div>
  );
}