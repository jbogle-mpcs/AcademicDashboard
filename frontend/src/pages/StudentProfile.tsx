import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getStudent,
  getStudentAssessments,
  getStudentCourses,
  StudentRead,
  StudentAssessments,
  StudentCourse,
  SATScore,
  PSATScore,
  ACTScore,
  MAPScore,
  DIBELSScore,
} from "../api/api";
import { ScoreCard, AssessmentSection, CardGrid } from "../components/ScoreCard";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

type Tab = "overview" | "sat" | "psat" | "act" | "map" | "dibels" | "courses";

export function StudentProfile() {
  const { id } = useParams<{ id: string }>();
  const studentId = Number(id);

  const [student, setStudent] = useState<StudentRead | null>(null);
  const [assessments, setAssessments] = useState<StudentAssessments | null>(null);
  const [courses, setCourses] = useState<StudentCourse[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getStudent(studentId),
      getStudentAssessments(studentId),
      getStudentCourses(studentId),
    ])
      .then(([s, a, c]) => {
        setStudent(s);
        setAssessments(a);
        setCourses(c);
      })
      .finally(() => setLoading(false));
  }, [studentId]);

  if (loading) return <LoadingState />;
  if (!student) return <div style={{ padding: 40, color: "var(--text-muted)" }}>Student not found.</div>;

  const latestSAT = assessments?.sat.at(-1);
  const latestACT = assessments?.act.at(-1);
  const latestPSAT = assessments?.psat.at(-1);

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "overview", label: "Overview" },
    { key: "sat", label: "SAT", count: assessments?.sat.length },
    { key: "psat", label: "PSAT", count: assessments?.psat.length },
    { key: "act", label: "ACT", count: assessments?.act.length },
    { key: "map", label: "MAP", count: assessments?.map.length },
    { key: "dibels", label: "DIBELS", count: assessments?.dibels.length },
    { key: "courses", label: "Courses", count: courses.length },
  ];

  return (
    <div style={{ padding: "36px 40px" }}>
      {/* Breadcrumb */}
      <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 20 }}>
        <Link to="/students" style={{ color: "var(--text-muted)" }}>Students</Link>
        {" › "}
        <span>{student.last_name}, {student.preferred_name ?? student.first_name}</span>
      </div>

      {/* Student header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 20, marginBottom: 32 }}>
        <BigAvatar name={`${student.first_name} ${student.last_name}`} />
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>
            {student.preferred_name ?? student.first_name} {student.last_name}
            {student.preferred_name && student.preferred_name !== student.first_name && (
              <span style={{ fontSize: 14, color: "var(--text-muted)", fontWeight: 400, marginLeft: 8 }}>
                ({student.first_name})
              </span>
            )}
          </h1>
          <div style={{ display: "flex", gap: 16, fontSize: 13, color: "var(--text-secondary)" }}>
            {student.division && <span>{student.division}</span>}
            {student.grade && <span>Grade {student.grade}</span>}
            {student.graduation_year && <span>Class of {student.graduation_year}</span>}
            {student.email && <span style={{ color: "var(--text-muted)" }}>{student.email}</span>}
          </div>
          <div className="mono" style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
            {student.student_id}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: 2,
          borderBottom: "2px solid var(--border)",
          marginBottom: 28,
        }}
      >
        {tabs.map(({ key, label, count }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            style={{
              padding: "8px 14px",
              fontSize: 13,
              fontWeight: tab === key ? 600 : 400,
              color: tab === key ? "var(--navy)" : "var(--text-secondary)",
              borderBottom: tab === key ? "2px solid var(--navy)" : "2px solid transparent",
              marginBottom: -2,
              background: "none",
              display: "flex",
              alignItems: "center",
              gap: 5,
              transition: "color 0.1s",
            }}
          >
            {label}
            {count != null && count > 0 && (
              <span
                style={{
                  fontSize: 10,
                  background: tab === key ? "var(--navy)" : "var(--border)",
                  color: tab === key ? "#fff" : "var(--text-muted)",
                  borderRadius: 99,
                  padding: "1px 5px",
                  fontWeight: 600,
                }}
              >
                {count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "overview" && (
        <OverviewTab
          student={student}
          latestSAT={latestSAT}
          latestACT={latestACT}
          latestPSAT={latestPSAT}
          assessments={assessments}
          courses={courses}
        />
      )}
      {tab === "sat" && <SATTab scores={assessments?.sat ?? []} />}
      {tab === "psat" && <PSATTab scores={assessments?.psat ?? []} />}
      {tab === "act" && <ACTTab scores={assessments?.act ?? []} />}
      {tab === "map" && <MAPTab scores={assessments?.map ?? []} />}
      {tab === "dibels" && <DIBELSTab scores={assessments?.dibels ?? []} />}
      {tab === "courses" && <CoursesTab courses={courses} />}
    </div>
  );
}

// ── Overview ────────────────────────────────────────────────────────────────

function OverviewTab({
  latestSAT,
  latestACT,
  latestPSAT,
  assessments,
  courses,
}: {
  student: StudentRead;
  latestSAT?: SATScore;
  latestACT?: ACTScore;
  latestPSAT?: PSATScore;
  assessments: StudentAssessments | null;
  courses: StudentCourse[];
}) {
  const hasCollegeReadiness = latestSAT || latestACT || latestPSAT;

  // MAP trend data for chart
  const mapBySubject: Record<string, { date: string; rit: number }[]> = {};
  assessments?.map.forEach((m) => {
    if (m.rit_score == null) return;
    if (!mapBySubject[m.subject]) mapBySubject[m.subject] = [];
    mapBySubject[m.subject].push({ date: m.test_date, rit: Number(m.rit_score) });
  });

  const subjectColors: Record<string, string> = {
    Reading: "var(--color-reading)",
    Mathematics: "var(--color-math)",
    Science: "var(--color-science)",
    Language: "var(--color-english)",
  };

  const mapChartData = buildMAPChartData(assessments?.map ?? []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {hasCollegeReadiness && (
        <section>
          <SectionLabel>College Readiness</SectionLabel>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {latestSAT && (
              <AssessmentSection title="SAT" date={latestSAT.test_date} testType={latestSAT.test_type}>
                <CardGrid>
                  <ScoreCard label="Total" value={latestSAT.total_score} sub={pct(latestSAT.total_percentile)} accent="var(--amber)" />
                  <ScoreCard label="EBRW" value={latestSAT.ebrw_score} sub={pct(latestSAT.ebrw_percentile)} accent="var(--color-reading)" />
                  <ScoreCard label="Math" value={latestSAT.math_score} sub={pct(latestSAT.math_percentile)} accent="var(--color-math)" />
                </CardGrid>
              </AssessmentSection>
            )}
            {latestACT && (
              <AssessmentSection title="ACT" date={latestACT.test_date} testType={latestACT.test_type}>
                <CardGrid>
                  <ScoreCard label="Composite" value={latestACT.composite_score} sub={pct(latestACT.composite_percentile)} accent="var(--amber)" />
                  <ScoreCard label="English" value={latestACT.english_score} accent="var(--color-english)" />
                  <ScoreCard label="Math" value={latestACT.math_score} accent="var(--color-math)" />
                  <ScoreCard label="Reading" value={latestACT.reading_score} accent="var(--color-reading)" />
                  <ScoreCard label="Science" value={latestACT.science_score} accent="var(--color-science)" />
                </CardGrid>
              </AssessmentSection>
            )}
            {latestPSAT && (
              <AssessmentSection title="PSAT" date={latestPSAT.test_date} testType={latestPSAT.test_type}>
                <CardGrid>
                  <ScoreCard label="Total" value={latestPSAT.total_score} sub={pct(latestPSAT.total_percentile)} accent="var(--amber)" />
                  <ScoreCard label="EBRW" value={latestPSAT.ebrw_score} accent="var(--color-reading)" />
                  <ScoreCard label="Math" value={latestPSAT.math_score} accent="var(--color-math)" />
                  {latestPSAT.selection_index != null && (
                    <ScoreCard label="Selection Index" value={latestPSAT.selection_index} accent="var(--color-writing)" />
                  )}
                </CardGrid>
              </AssessmentSection>
            )}
          </div>
        </section>
      )}

      {mapChartData.length > 1 && (
        <section>
          <SectionLabel>MAP Growth (RIT Scores)</SectionLabel>
          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
              padding: "20px 24px 16px",
            }}
          >
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={mapChartData}>
                <XAxis dataKey="term" tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} width={36} />
                <Tooltip
                  contentStyle={{ fontSize: 12, border: "1px solid var(--border)", borderRadius: 4 }}
                />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                {Object.keys(subjectColors).map((subj) =>
                  mapChartData.some((d) => d[subj] != null) ? (
                    <Line
                      key={subj}
                      type="monotone"
                      dataKey={subj}
                      stroke={subjectColors[subj] ?? "#999"}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      connectNulls
                    />
                  ) : null
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {courses.length > 0 && (
        <section>
          <SectionLabel>Current Courses</SectionLabel>
          <CoursesTab courses={courses.slice(0, 6)} compact />
        </section>
      )}
    </div>
  );
}

// ── SAT Tab ─────────────────────────────────────────────────────────────────

function SATTab({ scores }: { scores: SATScore[] }) {
  if (!scores.length) return <Empty label="No SAT scores on record." />;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {[...scores].reverse().map((s) => (
        <AssessmentSection key={s.id} title="SAT" date={s.test_date} testType={s.test_type}>
          <CardGrid>
            <ScoreCard label="Total" value={s.total_score} sub={pct(s.total_percentile)} accent="var(--amber)" />
            <ScoreCard label="EBRW" value={s.ebrw_score} sub={pct(s.ebrw_percentile)} accent="var(--color-reading)" />
            <ScoreCard label="Math" value={s.math_score} sub={pct(s.math_percentile)} accent="var(--color-math)" />
            {s.reading_test_score != null && <ScoreCard label="Reading Test" value={s.reading_test_score} accent="var(--color-reading)" />}
            {s.writing_test_score != null && <ScoreCard label="Writing Test" value={s.writing_test_score} accent="var(--color-writing)" />}
            {s.math_test_score != null && <ScoreCard label="Math Test" value={s.math_test_score} accent="var(--color-math)" />}
          </CardGrid>
        </AssessmentSection>
      ))}
    </div>
  );
}

// ── PSAT Tab ─────────────────────────────────────────────────────────────────

function PSATTab({ scores }: { scores: PSATScore[] }) {
  if (!scores.length) return <Empty label="No PSAT scores on record." />;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {[...scores].reverse().map((s) => (
        <AssessmentSection key={s.id} title="PSAT" date={s.test_date} testType={s.test_type}>
          <CardGrid>
            <ScoreCard label="Total" value={s.total_score} sub={pct(s.total_percentile)} accent="var(--amber)" />
            <ScoreCard label="EBRW" value={s.ebrw_score} sub={pct(s.ebrw_percentile)} accent="var(--color-reading)" />
            <ScoreCard label="Math" value={s.math_score} sub={pct(s.math_percentile)} accent="var(--color-math)" />
            {s.selection_index != null && <ScoreCard label="Selection Index" value={s.selection_index} accent="var(--color-writing)" />}
          </CardGrid>
        </AssessmentSection>
      ))}
    </div>
  );
}

// ── ACT Tab ─────────────────────────────────────────────────────────────────

function ACTTab({ scores }: { scores: ACTScore[] }) {
  if (!scores.length) return <Empty label="No ACT scores on record." />;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {[...scores].reverse().map((s) => (
        <AssessmentSection key={s.id} title="ACT" date={s.test_date} testType={s.test_type}>
          <CardGrid>
            <ScoreCard label="Composite" value={s.composite_score} sub={pct(s.composite_percentile)} accent="var(--amber)" />
            <ScoreCard label="English" value={s.english_score} sub={pct(s.english_percentile)} accent="var(--color-english)" />
            <ScoreCard label="Math" value={s.math_score} sub={pct(s.math_percentile)} accent="var(--color-math)" />
            <ScoreCard label="Reading" value={s.reading_score} sub={pct(s.reading_percentile)} accent="var(--color-reading)" />
            <ScoreCard label="Science" value={s.science_score} sub={pct(s.science_percentile)} accent="var(--color-science)" />
            {s.writing_score != null && <ScoreCard label="Writing" value={s.writing_score} accent="var(--color-writing)" />}
            {s.ela_score != null && <ScoreCard label="ELA" value={s.ela_score} accent="var(--color-ela)" />}
            {s.stem_score != null && <ScoreCard label="STEM" value={s.stem_score} accent="var(--color-stem)" />}
          </CardGrid>
        </AssessmentSection>
      ))}
    </div>
  );
}

// ── MAP Tab ─────────────────────────────────────────────────────────────────

function MAPTab({ scores }: { scores: MAPScore[] }) {
  if (!scores.length) return <Empty label="No MAP scores on record." />;

  const byTerm: Record<string, MAPScore[]> = {};
  scores.forEach((s) => {
    const key = s.term_name;
    if (!byTerm[key]) byTerm[key] = [];
    byTerm[key].push(s);
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {Object.entries(byTerm)
        .reverse()
        .map(([term, termScores]) => (
          <AssessmentSection key={term} title={term}>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {termScores.map((s) => (
                <div key={s.id}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>
                    {s.subject}
                  </div>
                  <CardGrid>
                    <ScoreCard label="RIT Score" value={s.rit_score != null ? Number(s.rit_score).toFixed(1) : null} sub={pct(s.percentile)} accent="var(--color-reading)" />
                    {s.norm_rit_mean != null && <ScoreCard label="Norm RIT Mean" value={Number(s.norm_rit_mean).toFixed(1)} accent="var(--border)" />}
                    {s.growth_rit != null && <ScoreCard label="Growth" value={`${Number(s.growth_rit) > 0 ? "+" : ""}${Number(s.growth_rit).toFixed(1)}`} accent={Number(s.growth_rit) >= 0 ? "var(--color-science)" : "var(--color-english)"} />}
                    {s.met_projected_growth != null && <ScoreCard label="Met Growth" value={s.met_projected_growth} accent="var(--amber)" />}
                  </CardGrid>
                </div>
              ))}
            </div>
          </AssessmentSection>
        ))}
    </div>
  );
}

// ── DIBELS Tab ───────────────────────────────────────────────────────────────

function DIBELSTab({ scores }: { scores: DIBELSScore[] }) {
  if (!scores.length) return <Empty label="No DIBELS scores on record." />;

  const byTerm: Record<string, DIBELSScore[]> = {};
  scores.forEach((s) => {
    if (!byTerm[s.term_name]) byTerm[s.term_name] = [];
    byTerm[s.term_name].push(s);
  });

  const benchmarkColor = (status: string | null) => {
    if (!status) return "var(--border)";
    const s = status.toLowerCase();
    if (s.includes("well above") || s.includes("above")) return "var(--color-science)";
    if (s.includes("at")) return "var(--color-reading)";
    if (s.includes("below") || s.includes("risk")) return "var(--color-english)";
    return "var(--border)";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {Object.entries(byTerm)
        .reverse()
        .map(([term, termScores]) => (
          <AssessmentSection key={term} title={term}>
            <CardGrid>
              {termScores.map((s) => (
                <ScoreCard
                  key={s.id}
                  label={s.measure}
                  value={s.score}
                  sub={s.benchmark_status}
                  accent={benchmarkColor(s.benchmark_status)}
                />
              ))}
            </CardGrid>
          </AssessmentSection>
        ))}
    </div>
  );
}

// ── Courses Tab ───────────────────────────────────────────────────────────────

function CoursesTab({ courses, compact }: { courses: StudentCourse[]; compact?: boolean }) {
  if (!courses.length) return <Empty label="No courses on record." />;

  const gradeColor = (grade: string | null) => {
    if (!grade) return "var(--text-muted)";
    const g = grade.toUpperCase();
    if (g.startsWith("A")) return "var(--color-science)";
    if (g.startsWith("B")) return "var(--color-reading)";
    if (g.startsWith("C")) return "var(--amber)";
    return "var(--color-english)";
  };

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: compact ? "1fr 60px" : "1fr 100px 80px 80px",
          padding: "8px 16px",
          background: "#fafaf9",
          borderBottom: "1px solid var(--border)",
          fontSize: 11,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: "var(--text-muted)",
        }}
      >
        <span>Course</span>
        {!compact && <span>Year</span>}
        {!compact && <span>Grade</span>}
        <span>Score</span>
      </div>
      {courses.map((c, i) => (
        <div
          key={c.id}
          style={{
            display: "grid",
            gridTemplateColumns: compact ? "1fr 60px" : "1fr 100px 80px 80px",
            padding: "11px 16px",
            borderTop: i > 0 ? "1px solid var(--border)" : undefined,
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>{c.course_name}</div>
            {c.course_code && (
              <div className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
                {c.course_code}
              </div>
            )}
          </div>
          {!compact && (
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{c.school_year ?? "—"}</span>
          )}
          {!compact && (
            <span
              style={{
                fontSize: 15,
                fontWeight: 600,
                fontFamily: "DM Mono, monospace",
                color: gradeColor(c.current_grade),
              }}
            >
              {c.current_grade ?? "—"}
            </span>
          )}
          <span className="mono" style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            {c.current_score != null ? `${Number(c.current_score).toFixed(1)}%` : "—"}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function pct(p: number | null | undefined) {
  if (p == null) return undefined;
  return `${p}th percentile`;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
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
      {children}
    </div>
  );
}

function Empty({ label }: { label: string }) {
  return (
    <div
      style={{
        padding: "48px 24px",
        textAlign: "center",
        color: "var(--text-muted)",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        fontSize: 14,
      }}
    >
      {label}
    </div>
  );
}

function LoadingState() {
  return (
    <div style={{ padding: 40, color: "var(--text-muted)" }}>Loading…</div>
  );
}

function BigAvatar({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase();
  return (
    <div
      style={{
        width: 52,
        height: 52,
        borderRadius: "50%",
        background: "var(--navy)",
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 18,
        fontWeight: 600,
        flexShrink: 0,
      }}
    >
      {initials}
    </div>
  );
}

function buildMAPChartData(scores: MAPScore[]) {
  const termOrder: string[] = [];
  const byTermSubject: Record<string, Record<string, number>> = {};

  scores.forEach((s) => {
    if (!termOrder.includes(s.term_name)) termOrder.push(s.term_name);
    if (!byTermSubject[s.term_name]) byTermSubject[s.term_name] = {};
    if (s.rit_score != null) byTermSubject[s.term_name][s.subject] = Number(s.rit_score);
  });

  return termOrder.map((term) => ({ term, ...byTermSubject[term] }));
}