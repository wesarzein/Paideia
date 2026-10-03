import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { environment } from '../../../environments/environment';

export interface Student {
  id: string;
  student_code: string | null;
  first_name: string;
  last_name: string;
  birth_date: string | null;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  grade_id: string | null;
  section_id: string | null;
  student_user_id: string | null;
  parent_user_id: string | null;
}

export interface StudentSummary {
  total: number;
  active: number;
  inactive: number;
}

export interface StudentPayload {
  student_code?: string | null;
  first_name: string;
  last_name: string;
  birth_date?: string;
  status: string;
  grade_id?: string;
  section_id?: string;
}

export interface AcademicCatalog {
  grades: { id: string; name: string; level: string }[];
  sections: { id: string; name: string; grade_id: string }[];
  courses: { id: string; name: string; code: string | null }[];
  periods: { id: string; name: string }[];
  students: { id: string; student_code: string | null; name: string }[];
  literal_scale: { greater_than: number; grade: string }[];
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  student_id: string | null;
  student_ids: string[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface UserPayload {
  email: string;
  full_name: string;
  password: string;
  role_code: string;
  student_id?: string | null;
  student_ids?: string[];
}

export interface GradePayload {
  student_id: string;
  course_id: string;
  period_id: string;
  component_id?: string;
  score: number;
  qualitative_note?: string;
  evaluation_name?: string;
  evaluation_type?: string;
  assessment_date?: string;
}
export interface GradeRecord { id: string; student_id: string; course_id: string; period_id: string; evaluation_name: string; evaluation_type: string; assessment_date: string; score: number; qualitative_note?: string | null; }

export interface AttendancePayload {
  student_id: string;
  course_id: string;
  period_id: string;
  attendance_date: string;
  status: string;
  remarks?: string;
}
export interface AttendanceRecord extends AttendancePayload { id: string; }

export interface CoursePayload {
  name: string;
  code?: string | null;
  is_active?: boolean;
}

export interface AssessmentComponent {
  id: string;
  course_id: string;
  name: string;
  weight: number;
  is_optional: boolean;
  is_active: boolean;
}

export interface CourseAssignment {
  id: string;
  course_id: string;
  grade_id: string;
  section_id: string;
  teacher_id: string | null;
  teacher_name: string | null;
}

export interface DashboardSummary {
  total_students: number;
  active_students: number;
  average_score: number;
  attendance_rate: number;
  at_risk_count: number;
}

export interface RiskAlert {
  student_id: string;
  student_code?: string;
  student_name: string;
  average_score: number;
  attendance_rate: number;
  risk_level: string;
  risk_factors?: string[];
  recommendation?: string;
  detection_method?: string;
}

export interface ImportPreview {
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
  errors: { row: number; error: string }[];
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  getHealth() {
    return this.http.get<{ status: string }>(`${environment.apiUrl}/health`);
  }

  login(payload: LoginPayload) {
    return this.http.post<LoginResponse>(`${environment.apiUrl}/auth/login`, payload);
  }

  logout() {
    return this.http.post<{ message: string }>(`${environment.apiUrl}/auth/logout`, {});
  }

  getStudentSummary() {
    return this.http.get<StudentSummary>(`${environment.apiUrl}/students/summary`);
  }

  getDashboardSummary(filters: Record<string, string> = {}) {
    return this.http.get<DashboardSummary>(`${environment.apiUrl}/dashboard/summary`, { params: filters });
  }

  getStudents(search = '', filters: Record<string, string> = {}) {
    return this.http.get<Student[]>(`${environment.apiUrl}/students`, {
      params: search ? { search, ...filters } : filters,
    });
  }

  getAcademicCatalog(filters: Record<string, string> = {}) {
    return this.http.get<AcademicCatalog>(`${environment.apiUrl}/academic/catalog`, { params: filters });
  }

  createStudent(payload: StudentPayload) {
    return this.http.post<Student>(`${environment.apiUrl}/students`, payload);
  }
  updateStudent(id: string, payload: Partial<StudentPayload>) { return this.http.patch<Student>(`${environment.apiUrl}/students/${id}`, payload); }
  deleteStudent(id: string) { return this.http.delete<void>(`${environment.apiUrl}/students/${id}`); }

  listUsers() {
    return this.http.get<AuthUser[]>(`${environment.apiUrl}/users`);
  }

  createUser(payload: UserPayload) {
    return this.http.post<AuthUser>(`${environment.apiUrl}/users`, payload);
  }
  updateUser(id: string, payload: Partial<UserPayload>) { return this.http.patch<AuthUser>(`${environment.apiUrl}/users/${id}`, payload); }
  deleteUser(id: string) { return this.http.delete<void>(`${environment.apiUrl}/users/${id}`); }

  listGrades(filters: Record<string, string> = {}) {
    return this.http.get<GradeRecord[]>(`${environment.apiUrl}/grades`, { params: filters });
  }
  getMonthlyGradeSummary(filters: Record<string, string>) {
    return this.http.get<{ thresholds: { greater_than: number; grade: string }[]; students: { student_id: string; average: number; literal: string; components_recorded: number }[] }>(`${environment.apiUrl}/grades/monthly-summary`, { params: filters });
  }
  listAssessmentComponents(courseId: string) { return this.http.get<AssessmentComponent[]>(`${environment.apiUrl}/courses/${courseId}/assessment-components`); }
  listCourseAssignments(courseId: string) { return this.http.get<CourseAssignment[]>(`${environment.apiUrl}/courses/${courseId}/assignments`); }
  createCourseAssignment(courseId: string, payload: { section_id: string; teacher_id?: string; teacher_name?: string }) { return this.http.post<CourseAssignment>(`${environment.apiUrl}/courses/${courseId}/assignments`, payload); }
  deleteCourseAssignment(courseId: string, assignmentId: string) { return this.http.delete<void>(`${environment.apiUrl}/courses/${courseId}/assignments/${assignmentId}`); }

  createGrade(payload: GradePayload) {
    return this.http.post<unknown>(`${environment.apiUrl}/grades`, payload);
  }
  updateGrade(id: string, payload: { score?: number; qualitative_note?: string }) { return this.http.patch(`${environment.apiUrl}/grades/${id}`, payload); }
  deleteGrade(id: string) { return this.http.delete<void>(`${environment.apiUrl}/grades/${id}`); }

  listAttendance(filters: Record<string, string> = {}) {
    return this.http.get<AttendanceRecord[]>(`${environment.apiUrl}/attendance`, { params: filters });
  }

  createAttendance(payload: AttendancePayload) {
    return this.http.post<unknown>(`${environment.apiUrl}/attendance`, payload);
  }

  listCourses() {
    return this.http.get<{ id: string; name: string; code: string | null; is_active: boolean }[]>(`${environment.apiUrl}/courses`);
  }

  getStudentReports(filters: Record<string, string> = {}) {
    return this.http.get<RiskAlert[]>(`${environment.apiUrl}/reports/students`, { params: filters });
  }
  getIndividualReport(studentId: string, filters: Record<string, string> = {}) { return this.http.get<Record<string, unknown>>(`${environment.apiUrl}/reports/students/${studentId}`, { params: filters }); }
  exportGroupReport(filters: Record<string, string>) { return this.http.get(`${environment.apiUrl}/reports/export.xlsx`, { params: filters, responseType: 'blob' }); }

  listFollowUps(filters: Record<string, string> = {}) { return this.http.get<{ id: string; student_id: string; recorded_by_id: string | null; category: string; action: string; status: string }[]>(`${environment.apiUrl}/follow-ups`, { params: filters }); }
  createFollowUp(payload: { student_id: string; category: string; action: string; status: string }) { return this.http.post(`${environment.apiUrl}/follow-ups`, payload); }
  updateFollowUp(id: string, payload: { category?: string; action?: string; status?: string }) { return this.http.patch(`${environment.apiUrl}/follow-ups/${id}`, payload); }
  deleteFollowUp(id: string) { return this.http.delete<void>(`${environment.apiUrl}/follow-ups/${id}`); }

  createCourse(payload: CoursePayload) {
    return this.http.post<{ id: string; name: string; code: string | null }>(`${environment.apiUrl}/courses`, payload);
  }
  createAssessmentComponent(courseId: string, payload: { name: string; weight: number; is_optional: boolean }) { return this.http.post<AssessmentComponent>(`${environment.apiUrl}/courses/${courseId}/assessment-components`, payload); }
  updateAssessmentComponent(courseId: string, componentId: string, payload: Partial<AssessmentComponent>) { return this.http.patch<AssessmentComponent>(`${environment.apiUrl}/courses/${courseId}/assessment-components/${componentId}`, payload); }
  deactivateAssessmentComponent(courseId: string, componentId: string) { return this.http.delete<AssessmentComponent>(`${environment.apiUrl}/courses/${courseId}/assessment-components/${componentId}`); }
  updateCourse(id: string, payload: Partial<CoursePayload>) { return this.http.patch(`${environment.apiUrl}/courses/${id}`, payload); }
  deleteCourse(id: string) { return this.http.delete<void>(`${environment.apiUrl}/courses/${id}`); }

  previewStudentImport(file: File) {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<ImportPreview>(`${environment.apiUrl}/imports/preview`, form);
  }

  commitStudentRows(rows: Record<string, unknown>[], gradeId: string, sectionId: string) {
    return this.http.post<{ processed: number; imported: number; rejected: number }>(`${environment.apiUrl}/imports/students/commit`, { rows, grade_id: gradeId, section_id: sectionId });
  }

  previewGradeImport(file: File, periodId: string) {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<ImportPreview>(`${environment.apiUrl}/imports/grades/preview`, form, { params: { period_id: periodId } });
  }

  commitGradeRows(rows: Record<string, unknown>[], courseId: string, periodId: string) {
    return this.http.post<{ processed: number; imported: number; rejected: number }>(`${environment.apiUrl}/imports/grades/commit`, { rows, course_id: courseId, period_id: periodId });
  }
}
