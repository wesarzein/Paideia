import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AcademicCatalog, ApiService, GradeRecord } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [FormsModule, PageHeaderComponent],
  template: `
    <app-page-header title="Calificaciones" description="Registra varias evidencias por estudiante: tareas, prácticas, exámenes y bimestres." />
    <section class="panel filters">
      <label>Curso<select [(ngModel)]="courseId"><option value="">Seleccionar curso</option>@for (course of catalog().courses; track course.id) {<option [value]="course.id">{{ course.name }}</option>}</select></label>
      <label>Periodo<select [(ngModel)]="periodId"><option value="">Seleccionar periodo</option>@for (period of catalog().periods; track period.id) {<option [value]="period.id">{{ period.name }}</option>}</select></label>
      <label>Tipo<select [(ngModel)]="assessmentType"><option>Tarea</option><option>Práctica</option><option>Examen</option><option>Bimestre</option></select></label>
      <label>Frecuencia<select [(ngModel)]="frequency"><option>Diaria</option><option>Semanal</option><option>Mensual</option><option>Bimestral</option></select></label>
      <label>Fecha<input type="date" [(ngModel)]="assessmentDate" /></label>
    </section>
    <section class="panel table-wrap"><table><thead><tr><th>Estudiante</th><th>Nota 0-20</th><th>Observación</th></tr></thead><tbody>@for (student of catalog().students; track student.id) {<tr><td>{{ student.name }}</td><td><input type="number" min="0" max="20" step="0.1" [(ngModel)]="scores[student.id]" /></td><td><input [(ngModel)]="notes[student.id]" placeholder="Opcional" /></td></tr>}</tbody></table><button type="button" (click)="saveAll()">Guardar calificaciones</button>@if (message()) {<p>{{ message() }}</p>}</section>
    <section class="panel table-wrap"><h2>Calificaciones registradas</h2><table><thead><tr><th>Estudiante</th><th>Nota</th><th>Observación</th><th>Acciones</th></tr></thead><tbody>@for (grade of grades(); track grade.id) {<tr><td>{{ studentName(grade.student_id) }}</td><td><input type="number" min="0" max="20" step="0.1" [(ngModel)]="grade.score" /></td><td><input [(ngModel)]="grade.qualitative_note" /></td><td><button class="small" type="button" (click)="update(grade)">Guardar</button><button class="small danger" type="button" (click)="remove(grade)">Eliminar</button></td></tr>}</tbody></table></section>
  `,
  styles: [` .panel { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: 22px; margin-bottom: 18px; } .filters { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; } label { display: grid; gap: 7px; color: var(--color-muted-text); } input, select { border: 1px solid var(--color-border); border-radius: 6px; padding: 10px; font: inherit; } .table-wrap { overflow-x: auto; } table { width: 100%; border-collapse: collapse; } th, td { padding: 12px; border-bottom: 1px solid var(--color-border); text-align: left; } button { margin-top: 18px; background: var(--color-primary); color: white; border: 0; border-radius: 6px; padding: 11px 16px; cursor: pointer; } .small { margin: 0 5px 0 0; padding: 7px 10px; } .danger { background: #b94b3b; } @media (max-width: 800px) { .filters { grid-template-columns: 1fr 1fr; } } @media (max-width: 500px) { .filters { grid-template-columns: 1fr; } } `],
})
export class GradesPage {
  private readonly api = inject(ApiService);
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [] });
  protected readonly message = signal('');
  protected readonly grades = signal<GradeRecord[]>([]);
  protected courseId = ''; protected periodId = ''; protected assessmentType = 'Tarea'; protected frequency = 'Diaria'; protected assessmentDate = new Date().toISOString().slice(0, 10); protected scores: Record<string, number | null> = {}; protected notes: Record<string, string> = {};
  constructor() { this.api.getAcademicCatalog().subscribe({ next: (catalog) => { this.catalog.set(catalog); this.loadGrades(); } }); }
  protected loadGrades(): void { const filters: Record<string, string> = {}; if (this.courseId) filters['course_id'] = this.courseId; if (this.periodId) filters['period_id'] = this.periodId; this.api.listGrades(filters).subscribe({ next: (items) => this.grades.set(items) }); }
  protected saveAll(): void { const pending = this.catalog().students.filter((student) => this.scores[student.id] !== null && this.scores[student.id] !== undefined); if (!this.courseId || !this.periodId || !pending.length) { this.message.set('Selecciona curso, periodo y al menos una nota.'); return; } let saved = 0; pending.forEach((student) => this.api.createGrade({ student_id: student.id, course_id: this.courseId, period_id: this.periodId, score: Number(this.scores[student.id]), qualitative_note: `${this.frequency} · ${this.assessmentType} · ${this.assessmentDate}: ${this.notes[student.id] || ''}` }).subscribe({ next: () => { saved += 1; this.message.set(`${saved} calificaciones guardadas.`); if (saved === pending.length) this.loadGrades(); } })); }
  protected studentName(id: string): string { return this.catalog().students.find((student) => student.id === id)?.name ?? id; }
  protected update(grade: GradeRecord): void { this.api.updateGrade(grade.id, { score: Number(grade.score), qualitative_note: grade.qualitative_note ?? '' }).subscribe({ next: () => this.loadGrades() }); }
  protected remove(grade: GradeRecord): void { if (confirm('¿Eliminar esta calificación?')) this.api.deleteGrade(grade.id).subscribe({ next: () => this.loadGrades() }); }
}
