import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { environment } from '../../../environments/environment';

export interface ForecastRow {
  student_id: string; student_name: string; course_id: string; course_name: string;
  history: { label: string; score: number; records: number }[];
  excluded_records: number; attendance_count: number;
  prediction: {
    status: 'experimental' | 'insufficient_history'; score: number | null;
    range: number[] | null; trend: 'improving' | 'declining' | 'stable' | null;
    factors: { feature: string; value: number; association: number }[];
    recommendations: string[];
  };
}
export interface PerformanceForecast {
  mode: string; training_source: string; horizon: string; as_of: string;
  generated_at: string; model_version: string; warning: string; interval_note: string;
  validation: { mae: number; rmse: number; baseline_mae: number; interval_coverage: number };
  training_split: Record<string, { examples: number; students: number; target_indices: number[] }>;
  summary: { students: number; course_cases: number; predicted: number; insufficient: number; projected_average: number | null };
  rows: ForecastRow[];
}
@Injectable({ providedIn: 'root' })
export class PerformanceForecastService {
  private readonly http = inject(HttpClient);
  analyze(params: Record<string, string>) {
    return this.http.get<PerformanceForecast>(`${environment.apiUrl}/academic-ai/forecast`, { params });
  }
}
