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
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  getHealth() {
    return this.http.get<{ status: string }>(`${environment.apiUrl}/health`);
  }

  getStudentSummary() {
    return this.http.get<StudentSummary>(`${environment.apiUrl}/students/summary`);
  }

  getStudents(search = '') {
    return this.http.get<Student[]>(`${environment.apiUrl}/students`, {
      params: search ? { search } : {},
    });
  }

  createStudent(payload: StudentPayload) {
    return this.http.post<Student>(`${environment.apiUrl}/students`, payload);
  }
}
