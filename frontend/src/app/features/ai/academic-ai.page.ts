import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AcademicCatalog, ApiService } from '../../core/services/api.service';
import { ForecastRow, PerformanceForecast, PerformanceForecastService } from './performance-forecast.service';
import { RouterLink } from '@angular/router';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [PageHeaderComponent, RouterLink, FormsModule, DatePipe, DecimalPipe],
  templateUrl: './academic-ai.page.html',
  styleUrl: './academic-ai.page.css',

})
export class AcademicAiPage {
  private readonly api = inject(ApiService);
  private readonly forecast = inject(PerformanceForecastService);
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] });
  protected readonly data = signal<PerformanceForecast | null>(null);
  protected readonly loading = signal(false);
  protected readonly catalogLoading = signal(false);
  protected readonly error = signal('');
  protected readonly catalogError = signal(false);
  protected mode = 'classroom';
  protected gradeId = ''; protected sectionId = ''; protected studentId = '';
  protected courseId = ''; protected periodId = ''; protected horizon = 'exam';
  protected throughBimester: number | null = null;
  protected asOf = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date());
  private request = 0;
  private catalogRequest = 0;
  constructor() { this.loadCatalog(); }
  protected invalidate() { ++this.request; this.data.set(null); this.error.set(''); this.loading.set(false); }
  protected changeGrade() { this.sectionId = ''; this.changeSection(); }
  protected changeSection() { this.studentId = ''; this.courseId = ''; this.loadCatalog(); }
  protected changeMode() { this.studentId = ''; this.invalidate(); }
  protected loadCatalog() {
    this.invalidate();
    const request = ++this.catalogRequest;
    this.catalogLoading.set(true); this.catalogError.set(false);
    const params: Record<string, string> = {};
    if (this.gradeId) params['grade_id'] = this.gradeId;
    if (this.sectionId) params['section_id'] = this.sectionId;
    this.api.getAcademicCatalog(params).subscribe({
      next: c => {
        if (request !== this.catalogRequest) return;
        this.catalog.set(c); this.catalogLoading.set(false);
        if (!this.periodId) this.periodId = c.periods.filter(p => (p.starts_on || '') <= this.asOf).at(-1)?.id || '';
      },
      error: () => {
        if (request !== this.catalogRequest) return;
        this.catalogLoading.set(false); this.catalogError.set(true);
      },
    });
  }
  protected canAnalyze() {
    return !this.catalogLoading() && !this.catalogError() && !!this.gradeId && !!this.sectionId &&
      !!this.periodId && !!this.asOf && (this.mode === 'classroom' || !!this.studentId) &&
      (this.horizon !== 'bimester' || (Number.isInteger(this.throughBimester) &&
        this.throughBimester! >= 1 && this.throughBimester! <= 100));
  }
  protected analyze() {
    if (!this.canAnalyze() || this.loading()) return;
    this.invalidate(); const request = ++this.request; this.loading.set(true);
    const params: Record<string, string> = { section_id: this.sectionId, period_id: this.periodId,
      horizon: this.horizon, as_of: this.asOf };
    if (this.mode === 'student') params['student_id'] = this.studentId;
    if (this.courseId) params['course_id'] = this.courseId;
    if (this.horizon === 'bimester') params['through_bimester'] = String(this.throughBimester);
    this.forecast.analyze(params).subscribe({
      next: d => { if (request === this.request) { this.data.set(d); this.loading.set(false); } },
      error: e => { if (request === this.request) {
        this.loading.set(false);
        this.error.set(typeof e.error?.detail === 'string' ? e.error.detail : 'No se pudo realizar el análisis. Reintenta la consulta.');
      } },
    });
  }
  protected trend(row: ForecastRow) {
    return { improving: 'Mejora reciente', declining: 'Descenso reciente', stable: 'Estable' }[row.prediction.trend || 'stable'];
  }
  protected feature(name: string) {
    return ({ last_score: 'Último resultado', trend: 'Cambio reciente', mean_score: 'Promedio histórico',
      variation: 'Variación de notas', history_count: 'Cantidad de observaciones',
      attendance_rate: 'Presencia registrada', attendance_missing: 'Asistencia no disponible' } as Record<string, string>)[name] || name;
  }
  protected points(row: ForecastRow) {
    return row.history.map((h, i) => `${20 + i * 560 / Math.max(1, row.history.length - 1)},${140 - h.score * 6}`).join(' ');
  }
}
