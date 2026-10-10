import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { environment } from '../../../environments/environment';

export interface ModelMetrics { precision: number; recall: number; f1: number; confusion_matrix: number[][]; brier_score: number; }
export interface ModelRun { id: string; mode: string; status: string; configuration: { seed: number; pupils: number; failure_cutoff: number }; created_at: string; finished_at: string | null; approved_at: string | null; error_code: string | null; metrics: ModelMetrics | null; baseline: ModelMetrics | null; split: { train_count: number; test_count: number; student_overlap: number } | null; limitation: string | null; }
export interface ModelStatus { mode: string; institutional_status: string; active_run_id: string | null; deployment_version: number; autorun: boolean; runs: ModelRun[]; }
export interface DemoPrediction { student_id: string; course_id: string; target_period_id: string; status: string; history_periods: number; attendance_count: number; prediction: { status: string; risk: string | null; probability: number | null; factors?: { feature: string; association: number }[] } }
export interface Predictions { status: string; mode: string; run_id?: string; model_date?: string; rows: DemoPrediction[]; }
@Injectable({ providedIn: 'root' })
export class RiskModelService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/risk-models`;
  status() { return this.http.get<ModelStatus>(this.base); }
  predictions() { return this.http.get<Predictions>(`${this.base}/demonstration/predictions`); }
  train(seed: number, pupils: number, failure_cutoff: number, medium_probability = .3, high_probability = .7) { return this.http.post<ModelRun>(`${this.base}/demonstration/train`, { seed, pupils, failure_cutoff, medium_probability, high_probability, acknowledge_synthetic: true }); }
  approve(id: string, reason: string) { return this.http.post<ModelRun>(`${this.base}/${id}/approve`, { reason, acknowledge_synthetic: true }); }
  activate(run_id: string | null, expected_version: number, reason: string) { return this.http.post(`${this.base}/demonstration/activate`, { run_id, expected_version, reason, acknowledge_synthetic: true }); }
}
