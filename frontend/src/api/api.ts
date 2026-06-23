import axios from "axios";
import { msalInstance, loginRequest } from "../auth/msal";

const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use(async (config) => {
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length > 0) {
    try {
      const result = await msalInstance.acquireTokenSilent({
        ...loginRequest,
        account: accounts[0],
      });
      config.headers.Authorization = `Bearer ${result.accessToken}`;
    } catch {
      // silent refresh failed — let the request go unauthenticated,
      // the 401 response will trigger a redirect to login
    }
  }
  return config;
});

// ── Students ──────────────────────────────────────────────────────────────

export interface StudentSummary {
  id: number;
  student_id: string;
  first_name: string;
  last_name: string;
  preferred_name: string | null;
  email: string | null;
  grade: number | null;
  division: string | null;
  is_active: boolean;
}

export interface StudentRead extends StudentSummary {
  ad_object_id: string | null;
  canvas_user_id: number | null;
  graduation_year: number | null;
  created_at: string;
  updated_at: string;
}

export interface StudentListParams {
  division?: string;
  grade?: number;
  active_only?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}

export const getStudents = (params?: StudentListParams) =>
  api.get<StudentSummary[]>("/students/", { params }).then((r) => r.data);

export const getStudent = (id: number) =>
  api.get<StudentRead>(`/students/${id}`).then((r) => r.data);

// ── Assessments ───────────────────────────────────────────────────────────

export interface SATScore {
  id: number; student_id: number; test_date: string; test_type: string;
  ebrw_score: number | null; math_score: number | null; total_score: number | null;
  ebrw_percentile: number | null; math_percentile: number | null; total_percentile: number | null;
  reading_test_score: number | null; writing_test_score: number | null; math_test_score: number | null;
}

export interface PSATScore {
  id: number; student_id: number; test_date: string; test_type: string;
  ebrw_score: number | null; math_score: number | null; total_score: number | null;
  ebrw_percentile: number | null; math_percentile: number | null; total_percentile: number | null;
  selection_index: number | null;
}

export interface ACTScore {
  id: number; student_id: number; test_date: string; test_type: string;
  english_score: number | null; math_score: number | null; reading_score: number | null;
  science_score: number | null; composite_score: number | null; writing_score: number | null;
  ela_score: number | null; stem_score: number | null;
  english_percentile: number | null; math_percentile: number | null;
  reading_percentile: number | null; science_percentile: number | null;
  composite_percentile: number | null;
}

export interface MAPScore {
  id: number; student_id: number; test_date: string; term_name: string;
  season: string | null; school_year: string | null; subject: string;
  rit_score: number | null; percentile: number | null; standard_error: number | null;
  norm_rit_mean: number | null; norm_percentile: number | null;
  growth_rit: number | null; projected_growth: number | null; met_projected_growth: string | null;
  grade_at_testing: number | null;
}

export interface DIBELSScore {
  id: number; student_id: number; test_date: string; term_name: string;
  season: string | null; school_year: string | null; measure: string;
  score: number | null; accuracy: number | null; benchmark_status: string | null;
  percentile: number | null; grade_at_testing: number | null;
}

export interface StudentAssessments {
  student_id: number;
  sat: SATScore[];
  psat: PSATScore[];
  act: ACTScore[];
  map: MAPScore[];
  dibels: DIBELSScore[];
}

export const getStudentAssessments = (studentId: number) =>
  api.get<StudentAssessments>(`/assessments/students/${studentId}`).then((r) => r.data);

// ── Canvas ─────────────────────────────────────────────────────────────────

export interface StudentCourse {
  id: number; student_id: number; canvas_course_id: number;
  enrollment_type: string; enrollment_state: string | null;
  current_grade: string | null; current_score: number | null;
  final_grade: string | null; final_score: number | null;
  course_name: string; course_code: string | null;
  term_name: string | null; school_year: string | null;
  synced_at: string;
}

export const getStudentCourses = (studentId: number, schoolYear?: string) =>
  api.get<StudentCourse[]>(`/canvas/students/${studentId}/courses`, {
    params: schoolYear ? { school_year: schoolYear } : undefined,
  }).then((r) => r.data);

export default api;