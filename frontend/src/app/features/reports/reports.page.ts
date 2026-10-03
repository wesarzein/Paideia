import { DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AcademicCatalog, ApiService, RiskAlert } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

interface IndividualReport {
  student: { id: string; student_code: string; name: string; grade: string | null; level: string | null; section: string | null };
  grades: { course: string; evaluation: string; component: string; date: string; score: number; literal: string; note: string | null }[];
  attendance: { course: string; date: string; status: string; remarks: string | null }[];
  follow_ups: { date: string | null; category: string; action: string; status: string }[];
}
const emptyCatalog = (): AcademicCatalog => ({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] });

@Component({
  standalone: true,
  imports: [FormsModule, PageHeaderComponent, DecimalPipe],
  template: `
    <app-page-header title="Reportes académicos" description="Vista previa individual y grupal por grado." />
    <section class="panel controls">
      <label>Nivel<select [(ngModel)]="level" (ngModelChange)="gradeId = ''; sectionId = ''; loadCatalog()"><option value="">Seleccionar nivel</option>@for (item of levels(); track item) {<option [value]="item">{{ item }}</option>}</select></label>
      <label>Grado<select [(ngModel)]="gradeId" (ngModelChange)="sectionId = ''; load()" [disabled]="!level"><option value="">Seleccionar grado</option>@for (grade of gradesForLevel(); track grade.id) {<option [value]="grade.id">{{ grade.name }}</option>}</select></label>
      <label>Sección<select [(ngModel)]="sectionId" (ngModelChange)="load()" [disabled]="!gradeId"><option value="">Todas</option>@for (section of sectionsForGrade(); track section.id) {<option [value]="section.id">{{ gradeName() }} · {{ section.name }}</option>}</select></label>
      <label>Periodo<select [(ngModel)]="periodId" (ngModelChange)="load()"><option value="">Todos</option>@for (period of catalog().periods; track period.id) {<option [value]="period.id">{{ period.name }}</option>}</select></label>
      <label>Curso<select [(ngModel)]="courseId" (ngModelChange)="load()"><option value="">Todos</option>@for (course of catalog().courses; track course.id) {<option [value]="course.id">{{ course.name }}</option>}</select></label>
      <label>Mes<input type="month" [(ngModel)]="month" (ngModelChange)="load()" /></label>
      <div class="actions"><button class="no-print" type="button" (click)="print()" [disabled]="!gradeId">Imprimir / PDF</button><button class="no-print" type="button" (click)="exportXlsx()" [disabled]="!gradeId">Exportar Excel</button></div>
    </section>
    @if (!gradeId) { <p class="panel">Selecciona un grado para generar la vista previa grupal.</p> }
    @else if (loading()) { <p class="panel">Preparando vista previa...</p> }
    @else {
      <div class="print-root">
      <p class="period-caption">Reporte mensual @if (month) { · {{ monthLabel() }} · Bimestre {{ bimesterNumber() }} }</p>
      <section class="summary"><article><span>Estudiantes</span><strong>{{ students().length }}</strong></article><article><span>Promedio grupal</span><strong>{{ average() | number:'1.1-2' }}</strong></article><article><span>Asistencia grupal</span><strong>{{ attendance() | number:'1.1-1' }}%</strong></article></section>
      <section class="panel preview">
        <h2>Reporte grupal · {{ gradeName() }} {{ sectionId ? '· ' + sectionName() : '' }}</h2>
        <table><thead><tr><th>Código</th><th>Estudiante</th><th>Promedio</th><th>Asistencia</th><th>Riesgo</th><th class="no-print actions-heading">Detalle</th></tr></thead><tbody>
          @for (item of students(); track item.student_id) {<tr><td>{{ item.student_code }}</td><td>{{ item.student_name }}</td><td>{{ item.average_score | number:'1.1-2' }}</td><td>{{ item.attendance_rate | number:'1.1-1' }}%</td><td>{{ item.risk_level }}</td><td class="no-print actions-cell"><button class="icon-action" type="button" (click)="showIndividual(item)" title="Ver ficha" aria-label="Ver ficha"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></td></tr>}
        </tbody></table>
      </section>
      @if (individual()) {
        <section class="panel preview individual">
          <h2>Reporte individual</h2><p><strong>{{ individual()!.student.name }}</strong> · {{ individual()!.student.student_code }} · {{ individual()!.student.level }} / {{ individual()!.student.grade }} {{ individual()!.student.section }}</p>
          <h3>Calificaciones</h3><table><thead><tr><th>Curso</th><th>Evaluación</th><th>Fecha</th><th>Nota</th><th>Literal</th><th>Observación</th></tr></thead><tbody>@for (grade of individual()!.grades; track $index) {<tr><td>{{ grade.course }}</td><td>{{ grade.evaluation }} · {{ grade.component }}</td><td>{{ grade.date }}</td><td>{{ grade.score }}</td><td>{{ grade.literal }}</td><td>{{ grade.note }}</td></tr>}</tbody></table>
          <h3>Asistencia</h3><table><thead><tr><th>Fecha</th><th>Curso</th><th>Estado</th><th>Observación</th></tr></thead><tbody>@for (record of individual()!.attendance; track $index) {<tr><td>{{ record.date }}</td><td>{{ record.course }}</td><td>{{ record.status }}</td><td>{{ record.remarks }}</td></tr>}</tbody></table>
          <h3>Seguimiento</h3>@for (item of individual()!.follow_ups; track $index) {<p>{{ item.date }} · {{ item.category }} · {{ item.action }}</p>}
        </section>
      }
      </div>
    }
  `,
  styles: [`
    .panel{background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;padding:20px;margin-bottom:16px}.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}label{display:grid;gap:6px;color:var(--color-muted-text)}input,select{padding:9px;border:1px solid var(--color-border);border-radius:7px;font:inherit;background:var(--color-surface)}.actions{display:flex;align-items:end;gap:8px;flex-wrap:wrap}.actions button{background:var(--color-primary);color:white;border:0;border-radius:5px;padding:9px 12px;cursor:pointer}.period-caption{margin:-5px 0 14px;color:var(--color-muted-text)}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}article{background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;padding:16px;display:grid;gap:7px}article span{color:var(--color-muted-text)}article strong{font-size:1.6rem;color:var(--color-primary)}.preview{overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid var(--color-border);text-align:left;white-space:nowrap}h2{font-size:1.2rem}h3{font-size:1rem;margin-top:20px}@media(max-width:700px){.controls{grid-template-columns:1fr 1fr}.summary{grid-template-columns:1fr}}
  `],
})
export class ReportsPage {
  private readonly api = inject(ApiService);
  protected readonly catalog = signal<AcademicCatalog>(emptyCatalog());
  protected readonly students = signal<RiskAlert[]>([]);
  protected readonly individual = signal<IndividualReport | null>(null);
  protected readonly loading = signal(false);
  protected readonly average = signal(0);
  protected readonly attendance = signal(0);
  protected level = '';
  protected gradeId = '';
  protected sectionId = '';
  protected periodId = '';
  protected courseId = '';
  protected month = new Date().toISOString().slice(0, 7);
  protected monthLabel(): string {
    const [year, month] = this.month.split('-').map(Number);
    return new Intl.DateTimeFormat('es-PE', { month: 'long', year: 'numeric' }).format(new Date(year, month - 1, 1));
  }
  protected bimesterNumber(): number {
    const month = Number(this.month.slice(5, 7));
    return month ? Math.ceil(month / 2) : 0;
  }

  constructor() { this.loadCatalog(); }
  protected levels(): string[] { return [...new Set(this.catalog().grades.map((item) => item.level))]; }
  protected gradesForLevel() { return this.catalog().grades.filter((item) => item.level === this.level); }
  protected sectionsForGrade() { return this.catalog().sections.filter((item) => item.grade_id === this.gradeId); }
  protected loadCatalog(): void { this.api.getAcademicCatalog().subscribe({ next: (catalog) => this.catalog.set(catalog) }); }
  protected gradeName(): string { return this.catalog().grades.find((item) => item.id === this.gradeId)?.name ?? ''; }
  protected sectionName(): string { return this.catalog().sections.find((item) => item.id === this.sectionId)?.name ?? ''; }

  protected load(): void {
    if (!this.gradeId) { this.students.set([]); this.individual.set(null); return; }
    this.loading.set(true);
    const filters: Record<string, string> = { grade_id: this.gradeId };
    if (this.sectionId) filters['section_id'] = this.sectionId;
    if (this.periodId) filters['period_id'] = this.periodId;
    if (this.courseId) filters['course_id'] = this.courseId;
    if (this.month) filters['month'] = String(Number(this.month.slice(5, 7)));
    this.api.getStudentReports(filters).subscribe({ next: (items) => { this.students.set(items); this.average.set(items.length ? items.reduce((sum, item) => sum + item.average_score, 0) / items.length : 0); this.attendance.set(items.length ? items.reduce((sum, item) => sum + item.attendance_rate, 0) / items.length : 0); this.loading.set(false); }, error: () => this.loading.set(false) });
  }
  protected showIndividual(item: RiskAlert): void { const filters: Record<string, string> = {}; if (this.periodId) filters['period_id'] = this.periodId; this.api.getIndividualReport(item.student_id, filters).subscribe({ next: (report) => this.individual.set(report as unknown as IndividualReport) }); }
  protected print(): void { window.print(); }
  protected exportXlsx(): void {
    const filters: Record<string, string> = { grade_id: this.gradeId };
    if (this.sectionId) filters['section_id'] = this.sectionId;
    if (this.periodId) filters['period_id'] = this.periodId;
    if (this.courseId) filters['course_id'] = this.courseId;
    if (this.month) filters['month'] = String(Number(this.month.slice(5, 7)));
    this.api.exportGroupReport(filters).subscribe({ next: (blob) => { const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'paideia-reporte-grupal.xlsx'; anchor.click(); URL.revokeObjectURL(url); } });
  }
}
