
export type Division = "LS" | "MS" | "HS";
 
export interface Student {
  id: number;
  student_id: string;
  first_name: string;
  last_name: string;
  preferred_name: string | null;
  email: string | null;
  grade: number | null;
  division: Division | null;
  graduation_year: number | null;
  is_active: boolean;
}
 
export const DIVISIONS: Division[] = ["LS", "MS", "HS"];
 
export const DIVISION_LABELS: Record<Division, string> = {
  LS: "Lower School",
  MS: "Middle School",
  HS: "High School",
};
 
export const GRADES_BY_DIVISION: Record<Division, number[]> = {
  LS: [1, 2, 3, 4, 5],
  MS: [6, 7, 8],
  HS: [9, 10, 11, 12],
};
 