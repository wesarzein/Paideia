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
  periods: { id: string; name: string; starts_on?: string; ends_on?: string; bimester_months?: Record<string, number> }[];
  students: { id: string; student_code: string | null; name: string }[];
  literal_scale: { greater_than: number; grade: string }[];
}

export interface AcademicPeriod {
  id: string;
  name: string;
  starts_on: string;
  ends_on: string;
}
export type PeriodPayload = Omit<AcademicPeriod, 'id'>;
export interface AcademicGrade { id: string; name: string; level: string; is_active: boolean; }
export interface AcademicSection { id: string; name: string; grade_id: string; is_active: boolean; }
export interface Enrollment { id: string; student_id: string; course_id: string; period_id: string; status: string; }
export interface FollowUp { id: string; student_id: string; recorded_by_id: string | null; recorded_by_name: string | null; created_at: string | null; category: string; action: string; status: string; }

export interface LoginPayload {
  email: string;
  password: string;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active?: boolean;
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
  is_active?: boolean;
  student_id?: string | null;
  student_ids?: string[];
}

export interface GradePayload {
  student_id: string;
  course_id: string;
  period_id: string;
  component_id?: string;
  academic_bimester?: number;
  evaluation_block?: 1 | 2;
  evaluation_criterion_key?: string;
  score: number;
  qualitative_note?: string;
  evaluation_name?: string;
  evaluation_type?: string;
  assessment_date?: string;
}
export interface GradeRecord { data_origin?: string; academic_month?: number | null; source_reference?: string | null; id: string; student_id: string; course_id: string; period_id: string; component_id: string | null; assessment_weight: number; evaluation_name: string; evaluation_type: string; assessment_date: string | null; record_kind?: "evaluation" | "historical_bimester"; evaluation_revision_id?: string | null; score: number; academic_bimester: number | null; evaluation_block: 1 | 2 | null; evaluation_criterion_key: string | null; qualitative_note?: string | null; }

export interface AttendancePayload {
  student_id: string;
  course_id: string;
  period_id: string;
  attendance_date: string;
  status: string;
  remarks?: string | null;
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

export interface EvaluationCompetency {
  key: string;
  name: string;
  position: number;
  is_active: boolean;
}

export interface EvaluationCriterion {
  key: string;
  name: string;
  block: 1 | 2;
  position: number;
  weight: string;
  competency_key: string | null;
  is_active: boolean;
  is_optional: boolean;
  source_header: string | null;
  legacy_component_id: string | null;
}

export interface EvaluationFormula {
  key: string;
  expression: string;
}

export interface EvaluationConfiguration {
  course_id: string;
  period_id: string;
  competencies: EvaluationCompetency[];
  criteria: EvaluationCriterion[];
  formulas: EvaluationFormula[];
  template_id: string;
  final_formula: string;
  schema_version: number;
  formula_language: string;
  weight_mode: string;
  block_weeks: number;
  bimester_weeks: number;
}

export interface EvaluationRevision {
  id: string | null;
  course_id: string;
  period_id: string;
  version: number;
  state: 'default' | 'draft' | 'published';
  previous_revision_id: string | null;
  configuration: EvaluationConfiguration;
  content_hash: string;
  reason: string;
  created_by_id: string | null;
  created_at: string | null;
}

export interface EvaluationPreview {
  weighted_blocks: Record<string, number | null>;
  formula_results: Record<string, number | null>;
  literal: string | null;
  warnings: { block: number; missing_required: string[] }[];
  configuration_fingerprint: string;
  preview_only: boolean;
}

export interface DashboardSummary {
  total_students: number;
  active_students: number;
  average_score: number | null;
  attendance_rate: number | null;
  at_risk_count: number;
}

export interface RiskAlert {
  student_id: string;
  student_code?: string;
  student_name: string;
  average_score: number | null;
  attendance_rate: number | null;
  grade_count: number;
  grade_weight_sum: number;
  attendance_count: number;
  risk_level: string;
  risk_factors?: string[];
  recommendation?: string;
  detection_method?: string;
}

export interface GradeImportReviewRow {
  row: number;
  status: 'new' | 'identical' | 'different' | 'ambiguous' | 'duplicate_in_file';
  component_id: string | null;
  existing: { id: string; score: number; qualitative_note: string | null } | null;
  review_token: string | null;
  decision?: 'keep' | 'update' | '';
}

export interface GradeImportReview {
  reference_results?: { source_row: number; monthly: Record<string, number | null>; final: number | null; literal: string | null; reference_only: boolean }[];
  rows: GradeImportReviewRow[];
  total: number;
  errors: { row: number; error: string }[];
}

export interface InstitutionalContext {
  historical?: boolean;
  school_year: number | null;
  bimestre: number | null;
  grade_id: string;
  section_id: string;
  confirmed: boolean;
  blocks: Record<string, { evaluation_name: string; assessment_date: string }>;
}

export interface ImportPreview {
  name_split_warning?: string;
  institutional?: { template: string; sheet: string; blank_inputs: number; warning: string; students: {source_row: number; student_code: string; name: string}[]; unsupported_formula_rows: number[]; blocks: { block: string; label: string; criteria: { name: string; header: string }[] }[]; derived: { cell: string; formula: string; cached: unknown }[] };
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
  errors: { row: number; error: string }[];
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  getAcademicHistory<T>(studentId: string, offset = 0) {
    return this.http.get<T>(`${environment.apiUrl}/academic/history`, { params: { student_id: studentId, limit: 50, offset } });
  }
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

  getAcademicDataStatus() { return this.http.get<{ total: number; origins: Record<string, number>; monthly_records: number }>(`${environment.apiUrl}/academic/data-status`); }
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
    return this.http.get<{ thresholds: { greater_than: number; grade: string }[]; students: { student_id: string; average: number | null; literal: string | null; components_recorded: number }[] }>(`${environment.apiUrl}/grades/monthly-summary`, { params: filters });
  }
  listPeriods() { return this.http.get<AcademicPeriod[]>(`${environment.apiUrl}/academic/periods`); }
  createPeriod(payload: PeriodPayload) { return this.http.post<AcademicPeriod>(`${environment.apiUrl}/academic/periods`, payload); }
  updatePeriod(id: string, payload: Partial<PeriodPayload>) { return this.http.patch<AcademicPeriod>(`${environment.apiUrl}/academic/periods/${id}`, payload); }
  listAssessmentComponents(courseId: string) { return this.http.get<AssessmentComponent[]>(`${environment.apiUrl}/courses/${courseId}/assessment-components`); }
  listCourseAssignments(courseId: string) { return this.http.get<CourseAssignment[]>(`${environment.apiUrl}/courses/${courseId}/assignments`); }
  createCourseAssignment(courseId: string, payload: { section_id: string; teacher_id?: string; teacher_name?: string }) { return this.http.post<CourseAssignment>(`${environment.apiUrl}/courses/${courseId}/assignments`, payload); }
  deleteCourseAssignment(courseId: string, assignmentId: string) { return this.http.delete<void>(`${environment.apiUrl}/courses/${courseId}/assignments/${assignmentId}`); }

  createGrade(payload: GradePayload) {
    return this.http.post<GradeRecord>(`${environment.apiUrl}/grades`, payload);
  }
  updateGrade(id: string, payload: { score?: number; qualitative_note?: string }) { return this.http.patch<GradeRecord>(`${environment.apiUrl}/grades/${id}`, payload); }
  deleteGrade(id: string) { return this.http.delete<void>(`${environment.apiUrl}/grades/${id}`); }

  listAttendance(filters: Record<string, string> = {}) {
    return this.http.get<AttendanceRecord[]>(`${environment.apiUrl}/attendance`, { params: filters });
  }

  listAcademicGrades() { return this.http.get<AcademicGrade[]>(`${environment.apiUrl}/academic/grades`); }
  listEnrollments(filters: Record<string, string> = {}) { return this.http.get<Enrollment[]>(`${environment.apiUrl}/enrollments`, { params: filters }); }
  createEnrollment(payload: { student_id: string; course_id: string; period_id: string }) { return this.http.post<Enrollment>(`${environment.apiUrl}/enrollments`, payload); }
  createAcademicGrade(payload: { name: string; level: string }) { return this.http.post<AcademicGrade>(`${environment.apiUrl}/academic/grades`, payload); }
  updateAcademicGrade(id: string, name: string) { return this.http.patch<AcademicGrade>(`${environment.apiUrl}/academic/grades/${id}`, { name }); }
  listAcademicSections() { return this.http.get<AcademicSection[]>(`${environment.apiUrl}/academic/sections`); }
  createAcademicSection(payload: { name: string; grade_id: string }) { return this.http.post<AcademicSection>(`${environment.apiUrl}/academic/sections`, payload); }
  updateAcademicSection(id: string, name: string) { return this.http.patch<AcademicSection>(`${environment.apiUrl}/academic/sections/${id}`, { name }); }

  createAttendance(payload: AttendancePayload) {
    return this.http.post<AttendanceRecord>(`${environment.apiUrl}/attendance`, payload);
  }

  listCourses() {
    return this.http.get<{ id: string; name: string; code: string | null; is_active: boolean }[]>(`${environment.apiUrl}/courses`);
  }

  getStudentReports(filters: Record<string, string> = {}) {
    return this.http.get<RiskAlert[]>(`${environment.apiUrl}/reports/students`, { params: filters });
  }
  getIndividualReport(studentId: string, filters: Record<string, string> = {}) { return this.http.get<Record<string, unknown>>(`${environment.apiUrl}/reports/students/${studentId}`, { params: filters }); }
  exportGroupReport(filters: Record<string, string>) { return this.http.get(`${environment.apiUrl}/reports/export.xlsx`, { params: filters, responseType: 'blob' }); }

  listFollowUps(filters: Record<string, string> = {}) { return this.http.get<FollowUp[]>(`${environment.apiUrl}/follow-ups`, { params: filters }); }
  createFollowUp(payload: { student_id: string; category: string; action: string; status: string }) { return this.http.post(`${environment.apiUrl}/follow-ups`, payload); }
  updateFollowUp(id: string, payload: { category?: string; action?: string; status?: string }) { return this.http.patch(`${environment.apiUrl}/follow-ups/${id}`, payload); }
  deleteFollowUp(id: string) { return this.http.delete<void>(`${environment.apiUrl}/follow-ups/${id}`); }

  createCourse(payload: CoursePayload) {
    return this.http.post<{ id: string; name: string; code: string | null }>(`${environment.apiUrl}/courses`, payload);
  }
  createAssessmentComponent(courseId: string, payload: { name: string; weight: number; is_optional: boolean }) { return this.http.post<AssessmentComponent>(`${environment.apiUrl}/courses/${courseId}/assessment-components`, payload); }
  updateAssessmentComponent(courseId: string, componentId: string, payload: Partial<AssessmentComponent>) { return this.http.patch<AssessmentComponent>(`${environment.apiUrl}/courses/${courseId}/assessment-components/${componentId}`, payload); }
  deactivateAssessmentComponent(courseId: string, componentId: string) { return this.http.delete<AssessmentComponent>(`${environment.apiUrl}/courses/${courseId}/assessment-components/${componentId}`); }
  getEvaluationConfiguration(courseId: string, periodId: string) {
    return this.http.get<EvaluationRevision>(`${environment.apiUrl}/courses/${courseId}/evaluation-configurations/current`, { params: { period_id: periodId } });
  }
  getActiveEvaluationConfiguration(courseId: string, periodId: string) {
    return this.http.get<EvaluationRevision>(`${environment.apiUrl}/courses/${courseId}/evaluation-configurations/active`, { params: { period_id: periodId } });
  }
  listEvaluationVersions(courseId: string, periodId: string) {
    return this.http.get<EvaluationRevision[]>(`${environment.apiUrl}/courses/${courseId}/evaluation-configurations/versions`, { params: { period_id: periodId } });
  }
  previewEvaluation(courseId: string, configuration: EvaluationConfiguration, scores: Record<string, number | null>) {
    return this.http.post<EvaluationPreview>(`${environment.apiUrl}/courses/${courseId}/evaluation-preview`, { configuration, scores });
  }
  saveEvaluationDraft(courseId: string, configuration: EvaluationConfiguration, expectedVersion: number, reason: string) {
    return this.http.post<EvaluationRevision>(`${environment.apiUrl}/courses/${courseId}/evaluation-configurations/drafts`, { configuration, expected_version: expectedVersion, reason });
  }
  publishEvaluation(courseId: string, configuration: EvaluationConfiguration, expectedVersion: number, reason: string) {
    return this.http.post<EvaluationRevision>(`${environment.apiUrl}/courses/${courseId}/evaluation-configurations/publish`, { configuration, expected_version: expectedVersion, reason });
  }
  restoreInstitutionalEvaluation(courseId: string, periodId: string, expectedVersion: number, reason: string) {
    return this.http.post<EvaluationRevision>(`${environment.apiUrl}/courses/${courseId}/evaluation-configurations/restore-institutional`, { period_id: periodId, expected_version: expectedVersion, reason });
  }
  updateCourse(id: string, payload: Partial<CoursePayload>) { return this.http.patch(`${environment.apiUrl}/courses/${id}`, payload); }
  deleteCourse(id: string) { return this.http.delete<void>(`${environment.apiUrl}/courses/${id}`); }

  previewStudentImport(file: File) {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<ImportPreview>(`${environment.apiUrl}/imports/preview`, form);
  }

  commitStudentRows(rows: Record<string, unknown>[], gradeId: string, sectionId: string) {
    return this.http.post<{ processed: number; imported: number; updated: number; skipped: number; rejected: number }>(`${environment.apiUrl}/imports/students/commit`, { rows, grade_id: gradeId, section_id: sectionId });
  }

  previewGradeImport(file: File, periodId: string) {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<ImportPreview>(`${environment.apiUrl}/imports/grades/preview`, form, { params: { period_id: periodId } });
  }

  commitGradeRows(rows: Record<string, unknown>[], courseId: string, periodId: string, academicContext?: InstitutionalContext, correctionsOnly = false) {
    return this.http.post<{ processed: number; imported: number; updated: number; skipped: number; rejected: number }>(`${environment.apiUrl}/imports/grades/commit`, { rows, course_id: courseId, period_id: periodId, academic_context: academicContext, corrections_only: correctionsOnly });
  }

  reviewGradeRows(rows: Record<string, unknown>[], courseId: string, periodId: string, academicContext?: InstitutionalContext) {
    return this.http.post<GradeImportReview>(`${environment.apiUrl}/imports/grades/review`, { rows, course_id: courseId, period_id: periodId, academic_context: academicContext });
  }
}
