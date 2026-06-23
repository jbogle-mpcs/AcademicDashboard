import { useEffect, useState, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getStudents, StudentSummary } from "../api/api";
import { DIVISIONS } from "../types/Student";

export function Students() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [students, setStudents] = useState<StudentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(searchParams.get("search") ?? "");

  const division = searchParams.get("division") ?? "";
  const grade = searchParams.get("grade") ?? "";

  const load = useCallback(() => {
    setLoading(true);
    getStudents({
      division: division || undefined,
      grade: grade ? Number(grade) : undefined,
      search: search || undefined,
      limit: 200,
    })
      .then(setStudents)
      .finally(() => setLoading(false));
  }, [division, grade, search]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  const setParam = (key: string, val: string) => {
    const next = new URLSearchParams(searchParams);
    if (val) next.set(key, val);
    else next.delete(key);
    if (key !== "grade") next.delete("grade");
    setSearchParams(next);
  };

  return (
    <div style={{ padding: "36px 40px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Students</h1>
        <span
          style={{
            fontSize: 12,
            background: "var(--navy)",
            color: "#fff",
            borderRadius: 99,
            padding: "2px 9px",
            fontWeight: 500,
          }}
        >
          {students.length}
        </span>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
        <input
          type="search"
          placeholder="Search by name or ID…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            flex: "1 1 200px",
            maxWidth: 300,
            padding: "8px 12px",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            background: "var(--surface)",
            outline: "none",
          }}
          onFocus={(e) => (e.target.style.borderColor = "var(--navy)")}
          onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
        />

        <FilterChips
          value={division}
          options={[{ value: "", label: "All" }, ...DIVISIONS.map((d) => ({ value: d, label: d }))]}
          onChange={(v) => setParam("division", v)}
        />

        {division && (
          <select
            value={grade}
            onChange={(e) => {
              const next = new URLSearchParams(searchParams);
              if (e.target.value) next.set("grade", e.target.value);
              else next.delete("grade");
              setSearchParams(next);
            }}
            style={{
              padding: "7px 10px",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
              background: "var(--surface)",
              color: grade ? "var(--text-primary)" : "var(--text-muted)",
            }}
          >
            <option value="">All grades</option>
            {(division === "LS" ? [1,2,3,4,5] : division === "MS" ? [6,7,8] : [9,10,11,12]).map((g) => (
              <option key={g} value={g}>Grade {g}</option>
            ))}
          </select>
        )}
      </div>

      {/* Table */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius)",
          overflow: "hidden",
        }}
      >
        {/* Table header */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 80px 80px 180px",
            padding: "9px 18px",
            background: "#fafaf9",
            borderBottom: "1px solid var(--border)",
            fontSize: 11,
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: "var(--text-muted)",
          }}
        >
          <span>Name</span>
          <span>Division</span>
          <span>Grade</span>
          <span>Student ID</span>
        </div>

        {loading ? (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-muted)" }}>
            Loading…
          </div>
        ) : students.length === 0 ? (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-muted)" }}>
            No students found.
          </div>
        ) : (
          students.map((s, i) => (
            <Link
              key={s.id}
              to={`/students/${s.id}`}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 80px 80px 180px",
                padding: "12px 18px",
                borderTop: i > 0 ? "1px solid var(--border)" : undefined,
                alignItems: "center",
                transition: "background 0.1s",
              }}
              onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "#fafaf9")}
              onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "transparent")}
            >
              <div>
                <span style={{ fontWeight: 500 }}>
                  {s.last_name}, {s.preferred_name ?? s.first_name}
                </span>
                {s.email && (
                  <span style={{ marginLeft: 10, fontSize: 12, color: "var(--text-muted)" }}>
                    {s.email}
                  </span>
                )}
              </div>
              <DivisionBadge division={s.division} />
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                {s.grade != null ? `${s.grade}` : "—"}
              </span>
              <span className="mono" style={{ fontSize: 12, color: "var(--text-muted)" }}>
                {s.student_id}
              </span>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

function DivisionBadge({ division }: { division: string | null }) {
  const colors: Record<string, { bg: string; color: string }> = {
    HS: { bg: "#eff6ff", color: "#1d4ed8" },
    MS: { bg: "#f0fdf4", color: "#15803d" },
    LS: { bg: "#fdf4ff", color: "#7e22ce" },
  };
  const style = division ? colors[division] : undefined;
  return division && style ? (
    <span
      style={{
        display: "inline-block",
        fontSize: 11,
        fontWeight: 600,
        padding: "2px 7px",
        borderRadius: 4,
        background: style.bg,
        color: style.color,
      }}
    >
      {division}
    </span>
  ) : (
    <span style={{ color: "var(--text-muted)" }}>—</span>
  );
}

function FilterChips({
  value,
  options,
  onChange,
}: {
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <div style={{ display: "flex", gap: 4 }}>
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          style={{
            padding: "6px 12px",
            borderRadius: "var(--radius)",
            fontSize: 13,
            fontWeight: value === o.value ? 600 : 400,
            background: value === o.value ? "var(--navy)" : "var(--surface)",
            color: value === o.value ? "#fff" : "var(--text-secondary)",
            border: `1px solid ${value === o.value ? "var(--navy)" : "var(--border)"}`,
            transition: "all 0.1s",
          }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}