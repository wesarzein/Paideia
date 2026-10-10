import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { environment } from '../../../environments/environment';

export interface MetricGroup { id: string; name: string; count: number; average: number | null; weight_sum: number; }
export interface BusinessIndicators {
  generated_at: string; scope: string; students_in_scope: number; students_with_grades: number;
  grade_count: number; average: number | null; zero_scores: number; weight_sum: number;
  literal_distribution: Record<string, number>;
  numeric_distribution: Record<string, number>;
  evaluation_coverage: { required_complete: number; required_incomplete: number; optional_missing: number; legacy_records_unknown: number; };
  attendance_months: { month: string; present: number; absent: number; late: number; count: number; }[];
  coverage: { active_enrollments: number; with_grades: number; without_grades: number; percent: number | null; evaluation_completion: string; };
  attendance: { count: number; present: number; absent: number; late: number; present_percent: number | null; absent_percent: number | null; late_percent: number | null; students_with_repeated_absences: number; };
  periods: MetricGroup[]; months: MetricGroup[]; courses: MetricGroup[]; students: MetricGroup[];
  ai: { status: string; institutional_predictions: boolean; run_id?: string; model_date?: string; cases?: number; ready?: number; insufficient?: number; high?: number; medium?: number; low?: number; };
}
@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private readonly http = inject(HttpClient);
  get(filters: Record<string, string>) {
    return this.http.get<BusinessIndicators>(`${environment.apiUrl}/kpis`, { params: filters });
  }
}
