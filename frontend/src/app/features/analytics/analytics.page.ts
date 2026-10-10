import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AcademicCatalog, ApiService } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { AnalyticsService, BusinessIndicators } from './analytics.service';

@Component({
  standalone: true,
  imports: [FormsModule, PageHeaderComponent, DecimalPipe, DatePipe, RouterLink],
  template: `
    <app-page-header title="Analítica académica" description="Indicadores de referencia sobre evidencia autorizada. No sustituyen fórmulas oficiales." />
    <section class="panel filters" aria-label="Filtros de analítica">
      <label>Nivel<select [(ngModel)]="level" (ngModelChange)="gradeId = ''; sectionId = ''; load()"><option value="">Todos</option>@for (name of levels(); track name) {<option [value]="name">{{ name }}</option>}</select></label>
      <label>Grado<select [(ngModel)]="gradeId" (ngModelChange)="sectionId = ''; load()"><option value="">Todos</option>@for (g of catalog().grades; track g.id) {@if (!level || g.level === level) {<option [value]="g.id">{{ g.name }}</option>}}</select></label>
      <label>Sección<select [(ngModel)]="sectionId" (ngModelChange)="load()"><option value="">Todas</option>@for (s of catalog().sections; track s.id) {@if (!gradeId || s.grade_id === gradeId) {<option [value]="s.id">{{ s.name }}</option>}}</select></label>
      <label>Periodo<select [(ngModel)]="periodId" (ngModelChange)="load()"><option value="">Todos</option>@for (p of catalog().periods; track p.id) {<option [value]="p.id">{{ p.name }}</option>}</select></label>
      <label>Curso<select [(ngModel)]="courseId" (ngModelChange)="load()"><option value="">Todos</option>@for (c of catalog().courses; track c.id) {<option [value]="c.id">{{ c.name }}</option>}</select></label>
      <label>Bimestre (solo notas)<input type="number" min="1" max="100" [(ngModel)]="bimester" (change)="load()" /></label>
      <button type="button" (click)="refresh()" [disabled]="loading()">Actualizar</button>
    </section>
    @if (loading()) {<p role="status">Consultando indicadores…</p>}
    @if (error()) {<p role="alert">No se pudo consultar la analítica. <button (click)="refresh()">Reintentar</button></p>}
    @if (data(); as d) {
      <p>{{ d.scope === 'single_course' ? 'Alcance: un solo curso; no representa toda la institución.' : 'Alcance: evidencia de los cursos autorizados.' }} Actualizado: {{ d.generated_at | date:'short' }}</p>
      @if (!d.grade_count) {<p role="status">Sin calificaciones para estos filtros. Ausencia de evidencia no equivale a cero.</p>}
      <section class="cards" aria-label="Indicadores">
        <article><span>Promedio de referencia / 20</span><strong>{{ d.average === null ? 'No calculable' : (d.average | number:'1.1-2') }}</strong><small>Pesos capturados; {{ d.grade_count }} notas, {{ d.zero_scores }} ceros reales</small></article>
        <article><span>Cobertura de matrículas activas</span><strong>{{ d.coverage.percent === null ? 'Sin denominador' : (d.coverage.percent | number:'1.0-1') + '%' }}</strong><small>{{ d.coverage.with_grades }} con notas / {{ d.coverage.active_enrollments }}; {{ d.coverage.without_grades }} sin evaluar</small></article>
        <article><span>Presencia registrada</span><strong>{{ d.attendance.present_percent === null ? 'Sin registros' : (d.attendance.present_percent | number:'1.0-1') + '%' }}</strong><small>{{ d.attendance.count }} registros del periodo; no filtrados por bimestre</small></article>
      </section>
      <section class="charts">
        <article class="panel"><h2>Distribución literal de notas</h2><p>Regla de la plantilla: &gt;16,4 AD; &gt;13,4 A; &gt;10,4 B; resto C.</p>
          @for (label of ['AD','A','B','C']; track label) {<div class="bar"><span>{{ label }}</span><meter [value]="d.literal_distribution[label]" min="0" [max]="d.grade_count || 1" [attr.aria-label]="label + ': ' + d.literal_distribution[label]"></meter><strong>{{ d.literal_distribution[label] }}</strong></div>}
        </article>
        <article class="panel"><h2>Evolución mensual</h2>
          @if (d.months.length) {<svg viewBox="0 0 600 160" role="img" aria-label="Promedios mensuales de cero a veinte"><line x1="20" y1="140" x2="580" y2="140" stroke="currentColor"/><polyline [attr.points]="points(d)" fill="none" stroke="var(--color-primary)" stroke-width="3"/></svg>}
          <table><thead><tr><th>Mes</th><th>Notas</th><th>Promedio</th></tr></thead><tbody>@for (m of d.months; track m.id) {<tr><td>{{ m.name }}</td><td>{{ m.count }}</td><td>{{ m.average === null ? 'No calculable' : (m.average | number:'1.1-2') }}</td></tr>}</tbody></table>
        </article>
      </section>
      <section class="panel"><h2>Comparación por periodo</h2><table><thead><tr><th>Periodo</th><th>Notas</th><th>Promedio</th></tr></thead><tbody>@for (p of d.periods; track p.id) {<tr><td>{{ p.name }}</td><td>{{ p.count }}</td><td>{{ p.average === null ? 'No calculable' : (p.average | number:'1.1-2') }}</td></tr>}</tbody></table></section>
      <section class="panel"><h2>Asistencia y cobertura</h2><p>Presentes: {{ d.attendance.present }} · Ausencias: {{ d.attendance.absent }} ({{ d.attendance.absent_percent === null ? 'sin registros' : (d.attendance.absent_percent | number:'1.0-1') + '%' }}) · Tardanzas: {{ d.attendance.late }}.</p><p>{{ d.attendance.students_with_repeated_absences }} estudiantes con más de una ausencia registrada; conteo descriptivo, sin umbral de alerta institucional.</p><p>Contextos registrados con criterios obligatorios: {{ d.evaluation_coverage.required_complete }} completos, {{ d.evaluation_coverage.required_incomplete }} incompletos. Opcionales ausentes: {{ d.evaluation_coverage.optional_missing }} contextos; política oficial pendiente. {{ d.evaluation_coverage.legacy_records_unknown }} notas legadas sin completitud determinable.</p><p>Las evaluaciones sin registros no se reconstruyen sin un calendario esperado. {{ d.students_with_grades }} de {{ d.students_in_scope }} estudiantes del ámbito tienen notas. IA institucional inactiva.</p><table><thead><tr><th>Mes</th><th>Presentes</th><th>Ausentes</th><th>Tardanzas</th></tr></thead><tbody>@for (m of d.attendance_months; track m.month) {<tr><td>{{ m.month }}</td><td>{{ m.present }}</td><td>{{ m.absent }}</td><td>{{ m.late }}</td></tr>}</tbody></table></section>
      <section class="panel"><h2>Distribución numérica / 20</h2>@for (label of ['0–5','>5–10','>10–15','>15–20']; track label) {<div class="bar"><span>{{ label }}</span><meter [value]="d.numeric_distribution[label]" min="0" [max]="d.grade_count || 1" [attr.aria-label]="label + ': ' + d.numeric_distribution[label]"></meter><strong>{{ d.numeric_distribution[label] }}</strong></div>}</section>
      <section class="panel"><h2>Detalle por curso</h2><table><thead><tr><th>Curso</th><th>Notas</th><th>Promedio</th></tr></thead><tbody>@for (c of d.courses; track c.id) {<tr><td>{{ c.name }}</td><td>{{ c.count }}</td><td>{{ c.average === null ? 'No calculable' : (c.average | number:'1.1-2') }}</td></tr>}</tbody></table></section>
      <section class="panel"><h2>Detalle autorizado por estudiante</h2><table><thead><tr><th>Código</th><th>Notas</th><th>Promedio</th></tr></thead><tbody>@for (s of d.students; track s.id) {<tr><td>{{ s.name }}</td><td>{{ s.count }}</td><td>{{ s.average === null ? 'Sin evidencia' : (s.average | number:'1.1-2') }}</td></tr>}</tbody></table></section>
      <section class="panel"><h2>IA · Demostración independiente</h2><p>IA institucional inactiva. Estos conteos ficticios no se mezclan con los indicadores académicos anteriores.</p>@if (d.ai.status === 'demonstration_only') {<p>Modelo {{ d.ai.run_id?.slice(0,8) }} · {{ d.ai.model_date | date:'short' }}</p><p>{{ d.ai.ready }} de {{ d.ai.cases }} casos ficticios con historia suficiente; {{ d.ai.insufficient }} insuficientes. Riesgo experimental: {{ d.ai.high }} alto, {{ d.ai.medium }} medio, {{ d.ai.low }} bajo.</p>} @else {<p>Sin demostración aprobada disponible.</p>}<a routerLink="/ia">Abrir panel experimental</a></section>
    }
  `,
  styles: [`
    .panel,article{background:var(--color-surface);border:1px solid var(--color-border);border-radius:12px;padding:20px;margin-bottom:16px}.filters,.cards,.charts{display:grid;gap:16px}.filters{grid-template-columns:repeat(auto-fit,minmax(150px,1fr));align-items:end}.cards{grid-template-columns:repeat(3,1fr)}.charts{grid-template-columns:1fr 1fr}label{display:grid;gap:6px}select,input,button{font:inherit;padding:8px;border:1px solid var(--color-border);border-radius:6px;background:var(--color-surface);color:var(--color-text)}strong{display:block;font-size:1.5rem}small{display:block;margin-top:8px}h2{font-size:1.1rem}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:8px;border-bottom:1px solid var(--color-border)}svg{width:100%;max-height:160px}.bar{display:flex;gap:12px;align-items:center;margin:14px 0}.bar meter{flex:1;width:100%;height:24px}.bar strong{font-size:1rem}.panel{overflow:auto}@media(max-width:700px){.cards,.charts{grid-template-columns:1fr}}
  `],
})
export class AnalyticsPage {
  private readonly api = inject(ApiService);
  private readonly analytics = inject(AnalyticsService);
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] });
  protected readonly data = signal<BusinessIndicators | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal(false);
  protected level = ''; protected gradeId = ''; protected sectionId = ''; protected periodId = ''; protected courseId = ''; protected bimester: number | null = null;
  private request = 0;
  constructor() { this.refresh(); }
  protected levels() { return [...new Set(this.catalog().grades.map(g => g.level))]; }
  protected refresh() {
    this.api.getAcademicCatalog().subscribe({ next: c => { this.catalog.set(c); this.load(); }, error: () => { this.data.set(null); this.error.set(true); this.loading.set(false); } });
  }
  protected load() {
    const request = ++this.request;
    this.loading.set(true); this.error.set(false); this.data.set(null);
    const filters: Record<string, string> = {};
    for (const [key, value] of Object.entries({ level: this.level, grade_id: this.gradeId, section_id: this.sectionId, period_id: this.periodId, course_id: this.courseId, bimester: this.bimester })) { if (value !== '' && value !== null) filters[key] = String(value); }
    this.analytics.get(filters).subscribe({ next: d => { if (request === this.request) { this.data.set(d); this.loading.set(false); } }, error: () => { if (request === this.request) { this.error.set(true); this.loading.set(false); } } });
  }
  protected points(d: BusinessIndicators) {
    return d.months.map((m, i) => m.average === null ? '' : `${20 + i * 560 / Math.max(1, d.months.length - 1)},${140 - m.average * 6}`).filter(Boolean).join(' ');
  }
}
