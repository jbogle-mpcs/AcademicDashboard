import { CSSProperties, ReactNode } from "react";

interface ScoreCardProps {
  label: string;
  value: number | string | null | undefined;
  sub?: string | null;
  accent?: string;
  wide?: boolean;
}

export function ScoreCard({ label, value, sub, accent = "var(--amber)", wide }: ScoreCardProps) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderLeft: `4px solid ${accent}`,
        borderRadius: "var(--radius)",
        padding: "14px 16px",
        minWidth: wide ? 160 : 110,
      }}
    >
      <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
        {label}
      </div>
      <div
        className="mono"
        style={{
          fontSize: value != null ? 26 : 18,
          fontWeight: 500,
          color: value != null ? "var(--text-primary)" : "var(--text-muted)",
          lineHeight: 1,
        }}
      >
        {value != null ? value : "—"}
      </div>
      {sub != null && (
        <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
          {sub}
        </div>
      )}
    </div>
  );
}

interface SectionProps {
  title: string;
  date?: string;
  testType?: string;
  children: ReactNode;
  style?: CSSProperties;
}

export function AssessmentSection({ title, date, testType, children, style }: SectionProps) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        overflow: "hidden",
        ...style,
      }}
    >
      <div
        style={{
          padding: "12px 18px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "baseline",
          gap: 12,
          background: "#fafaf9",
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 13 }}>{title}</span>
        {testType && (
          <span
            style={{
              fontSize: 11,
              background: "var(--amber-light)",
              color: "#92600a",
              padding: "2px 7px",
              borderRadius: 99,
              fontWeight: 500,
            }}
          >
            {testType}
          </span>
        )}
        {date && (
          <span style={{ fontSize: 12, color: "var(--text-muted)", marginLeft: "auto" }}>
            {new Date(date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
          </span>
        )}
      </div>
      <div style={{ padding: 18 }}>{children}</div>
    </div>
  );
}

export function CardGrid({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 10,
      }}
    >
      {children}
    </div>
  );
}