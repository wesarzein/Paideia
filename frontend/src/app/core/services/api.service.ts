import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { environment } from '../../../environments/environment';

export interface Student {
  id: string;
  student_code: string;
  first_name: string;
  last_name: string;
  birth_date: string | null;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  grade_id: string | null;
  section_id: string | null;
}

export interface StudentSummary {
  total: number;
  active: number;
  inactive: number;
}

export interface StudentPayload {
  student_code: string;
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
  courses: { id: string; name: string; code: string }[];
  periods: { id: string; name: string }[];
  students: { id: string; name: string }[];
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
}

export interface GradePayload {
  student_id: string;
  course_id: string;
  period_id: string;
  score: number;
  qualitative_note?: string;
}
export interface GradeRecord { id: string; student_id: string; course_id: string; period_id: string; score: number; qualitative_note?: string | null; }

export interface AttendancePayload {
  student_id: string;
  course_id: string;
  period_id: string;
  attendance_date: string;
  status: string;
  remarks?: string;
}

export interface CoursePayload {
  name: string;
  code: string;
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
  student_name: string;
  average_score: number;
  attendance_rate: number;
  risk_level: string;
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

  getRiskAlerts() {
    return this.http.get<RiskAlert[]>(`${environment.apiUrl}/dashboard/risk-alerts`);
  }

  getStudents(search = '', filters: Record<string, string> = {}) {
    return this.http.get<Student[]>(`${environment.apiUrl}/students`, {
      params: search ? { search, ...filters } : filters,
    });
  }

  getAcademicCatalog() {
    return this.http.get<AcademicCatalog>(`${environment.apiUrl}/academic/catalog`);
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

  createGrade(payload: GradePayload) {
    return this.http.post<unknown>(`${environment.apiUrl}/grades`, payload);
  }
  updateGrade(id: string, payload: { score?: number; qualitative_note?: string }) { return this.http.patch(`${environment.apiUrl}/grades/${id}`, payload); }
  deleteGrade(id: string) { return this.http.delete<void>(`${environment.apiUrl}/grades/${id}`); }

  listAttendance() {
    return this.http.get<unknown[]>(`${environment.apiUrl}/attendance`);
  }

  createAttendance(payload: AttendancePayload) {
    return this.http.post<unknown>(`${environment.apiUrl}/attendance`, payload);
  }

  listCourses() {
    return this.http.get<unknown[]>(`${environment.apiUrl}/courses`);
  }

  getStudentReports(filters: Record<string, string> = {}) {
    return this.http.get<RiskAlert[]>(`${environment.apiUrl}/reports/students`, { params: filters });
  }

  getKpis() { return this.http.get<{ average_score: number; attendance_rate: number; grades_count: number; attendance_count: number }>(`${environment.apiUrl}/kpis`); }
  listFollowUps() { return this.http.get<{ id: string; student_id: string; action: string; status: string }[]>(`${environment.apiUrl}/follow-ups`); }
  createFollowUp(payload: { student_id: string; action: string; status: string }) { return this.http.post(`${environment.apiUrl}/follow-ups`, payload); }

  createCourse(payload: CoursePayload) {
    return this.http.post<{ id: string; name: string; code: string }>(`${environment.apiUrl}/courses`, payload);
  }
  updateCourse(id: string, payload: Partial<CoursePayload>) { return this.http.patch(`${environment.apiUrl}/courses/${id}`, payload); }
  deleteCourse(id: string) { return this.http.delete<void>(`${environment.apiUrl}/courses/${id}`); }

  previewStudentImport(file: File) {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<{ columns: string[]; rows: Record<string, unknown>[]; total: number; errors: { row: number; error: string }[] }>(`${environment.apiUrl}/imports/preview`, form);
  }
}
