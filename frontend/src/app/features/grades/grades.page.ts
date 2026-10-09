import { DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  AcademicCatalog,
  ApiService,
  AssessmentComponent,
  EvaluationRevision,
  GradeRecord,
} from '../../core/services/api.service';
import { ConfirmService } from '../../core/services/confirm.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

const emptyCatalog = (): AcademicCatalog => ({
  grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [],
});

type MatrixCriterion = {
  key: string;
  name: string;
  weight: number;
  componentId: string | null;
  configurable: boolean;
};

@Component({
  standalone: true,
  imports: [DecimalPipe, FormsModule, PageHeaderComponent],
  template: `
    <app-page-header title="Calificaciones"
      description="Registra notas con el bimestre, bloque y evaluación seleccionados explícitamente." />
    <section class="panel filters">
      <label>Nivel<select [(ngModel)]="level" (ngModelChange)="gradeId = ''; sectionId = ''; loadCatalog()"><option value="">Seleccionar nivel</option>@for (item of levels(); track item) {<option [value]="item">{{ item }}</option>}</select></label>
      <label>Grado<select [(ngModel)]="gradeId" (ngModelChange)="sectionId = ''; loadCatalog()" [disabled]="!level"><option value="">Seleccionar grado</option>@for (grade of gradesForLevel(); track grade.id) {<option [value]="grade.id">{{ grade.name }}</option>}</select></label>
      <label>Sección<select [(ngModel)]="sectionId" (ngModelChange)="courseId = ''; loadCatalog()" [disabled]="!gradeId"><option value="">Seleccionar sección</option>@for (section of sectionsForGrade(); track section.id) {<option [value]="section.id">{{ gradeName(section.grade_id) }} · {{ section.name }}</option>}</select></label>
      <label>Curso<select [(ngModel)]="courseId" (ngModelChange)="loadAcademicSetup()" [disabled]="!sectionId"><option value="">Seleccionar curso</option>@for (course of catalog().courses; track course.id) {<option [value]="course.id">{{ course.name }}</option>}</select></label>
      <label>Periodo<select [(ngModel)]="periodId" (ngModelChange)="loadAcademicSetup()" [disabled]="!sectionId"><option value="">Seleccionar periodo</option>@for (period of catalog().periods; track period.id) {<option [value]="period.id">{{ period.name }}</option>}</select></label>
      <label>Bimestre institucional<input type="number" min="1" step="1" [(ngModel)]="academicBimester" placeholder="Seleccionar" /></label>
      <label>Bloque de evaluación<select [(ngModel)]="evaluationBlock" (ngModelChange)="scores = {}"><option [ngValue]="1">Primer bloque · semana 4</option><option [ngValue]="2">Segundo bloque · semana 8</option></select></label>
      <label>Nombre de evaluación<input [(ngModel)]="evaluationName" maxlength="120" placeholder="Nombre confirmado por el docente" /></label>
      <label>Fecha de evaluación<input type="date" [(ngModel)]="assessmentDate" /></label>
      <label>Tipo de evidencia legado<select [(ngModel)]="legacyEvidenceType">@for (type of evidenceTypes; track type) {<option [value]="type">{{ type }}</option>}</select></label>
      <label>Mes de consulta<input type="month" [(ngModel)]="consultationMonth" (ngModelChange)="loadGrades()" /></label>
    </section>

    @if (activeRevision()?.state === 'published') {
      <p class="period-caption">Configuración publicada v{{ activeRevision()!.version }} · bimestre {{ academicBimester || 'sin seleccionar' }} · bloque {{ evaluationBlock }}</p>
    } @else if (courseId && periodId) {
      <p class="period-caption">Sin configuración publicada: se conservan temporalmente los componentes vigentes del curso.</p>
    }
    @if (message()) { <p role="status" class="panel feedback">{{ message() }}</p> }

    @if (!sectionId || !courseId || !periodId) {
      <p class="panel">Selecciona grado, sección, curso y periodo para cargar la matriz del aula.</p>
    } @else if (!matrixCriteria().length) {
      <p class="panel">No existen criterios activos para el bloque seleccionado.</p>
    } @else {
      <section class="panel table-wrap">
        <table>
          <thead><tr><th>Código</th><th>Estudiante</th>@for (criterion of matrixCriteria(); track criterion.key) {<th>{{ criterion.name }}<small>Peso {{ criterion.weight }}</small></th>}<th>Promedio ponderado de referencia</th><th>Literal</th><th>Observación</th></tr></thead>
          <tbody>
            @for (student of catalog().students; track student.id) {
              <tr><td>{{ student.student_code }}</td><td>{{ student.name }}</td>
                @for (criterion of matrixCriteria(); track criterion.key) {
                  <td><input type="number" min="0" max="20" step="0.1" [name]="scoreKey(student.id, criterion.key)" [(ngModel)]="scores[scoreKey(student.id, criterion.key)]" [class.invalid]="invalidScore(scores[scoreKey(student.id, criterion.key)])" aria-label="Nota de criterio" /></td>
                }
                <td>{{ average(student.id) | number:'1.1-2' }}</td><td>{{ literal(student.id) }}</td><td><input [name]="'note-' + student.id" [(ngModel)]="notes[student.id]" placeholder="Opcional" /></td>
              </tr>
            }
          </tbody>
        </table>
        @if (!catalog().students.length) { <p>No hay alumnos cargados para esta sección. Importa el padrón institucional para continuar.</p> }
        <button type="button" (click)="saveAll()" [disabled]="!catalog().students.length">Guardar matriz</button>
      </section>
      <section class="panel table-wrap">
        <h2>Notas registradas del mes consultado</h2>
        <table><thead><tr><th>Estudiante</th><th>Contexto</th><th>Evaluación</th><th>Fecha</th><th>Nota</th><th>Observación</th><th class="actions-heading">Acciones</th></tr></thead><tbody>
          @for (grade of grades(); track grade.id) {<tr><td>{{ studentName(grade.student_id) }}</td><td>{{ grade.academic_bimester ? 'B' + grade.academic_bimester : 'Legado' }}{{ grade.evaluation_block ? ' · bloque ' + grade.evaluation_block : '' }}</td><td>{{ grade.evaluation_name }} · {{ grade.evaluation_type }}</td><td>{{ grade.assessment_date }}</td><td><input type="number" min="0" max="20" step="0.1" [(ngModel)]="grade.score" [class.invalid]="invalidScore(grade.score)" /></td><td><input [(ngModel)]="grade.qualitative_note" /></td><td class="actions-cell"><button class="icon-action" type="button" (click)="update(grade)" title="Guardar calificación" aria-label="Guardar calificación"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 3h12l4 4v14H3V3h2Z"/><path d="M7 3v6h10V3M7 21v-8h10v8"/></svg></button><button class="icon-action danger-icon" type="button" (click)="remove(grade)" title="Eliminar calificación" aria-label="Eliminar calificación"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6"/></svg></button></td></tr>}
        </tbody></table>
      </section>
    }
  `,
  styles: [`
    .panel{background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;padding:20px;margin-bottom:16px}.filters{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}label{display:grid;gap:6px;color:var(--color-muted-text);font-size:.88rem}input,select{min-width:70px;padding:9px;border:1px solid var(--color-border);border-radius:7px;font:inherit;background:var(--color-surface)}.period-caption{margin:-6px 0 14px;color:var(--color-muted-text);font-size:.9rem}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid var(--color-border);text-align:left;white-space:nowrap}th{vertical-align:bottom}small{display:block;color:var(--color-muted-text);font-weight:400}button{margin-top:14px;background:var(--color-primary);color:white;border:0;border-radius:5px;padding:10px 14px;cursor:pointer}.actions-cell{display:flex;gap:5px}.invalid{border-color:#b94b3b;background:#fff2ee}.feedback{color:var(--color-primary)}h2{font-size:1.15rem}@media(max-width:850px){.filters{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:520px){.filters{grid-template-columns:1fr}}
  `],
})
export class GradesPage {
  private readonly api = inject(ApiService);
  private readonly confirm = inject(ConfirmService);
  protected readonly catalog = signal<AcademicCatalog>(emptyCatalog());
  protected readonly components = signal<AssessmentComponent[]>([]);
  protected readonly activeRevision = signal<EvaluationRevision | null>(null);
  protected readonly grades = signal<GradeRecord[]>([]);
  protected readonly message = signal('');
  protected level = '';
  protected gradeId = '';
  protected sectionId = '';
  protected courseId = '';
  protected periodId = '';
  protected academicBimester: number | null = null;
  protected evaluationBlock: 1 | 2 = 1;
  protected evaluationName = '';
  protected legacyEvidenceType = 'Actitud ante el área';
  protected readonly evidenceTypes = [
    'Actitud ante el área', 'Cuaderno', 'Módulo', 'Exposición-Trabajos', 'Evaluación',
  ];
  protected assessmentDate = new Date().toISOString().slice(0, 10);
  protected consultationMonth = new Date().toISOString().slice(0, 7);
  protected scores: Record<string, number | null> = {};
  protected notes: Record<string, string> = {};

  constructor() { this.loadCatalog(); }
  protected levels(): string[] { return [...new Set(this.catalog().grades.map((item) => item.level))]; }
  protected gradesForLevel() { return this.catalog().grades.filter((item) => item.level === this.level); }
  protected sectionsForGrade() { return this.catalog().sections.filter((item) => item.grade_id === this.gradeId); }
  protected gradeName(id: string) { return this.catalog().grades.find((item) => item.id === id)?.name ?? ''; }

  protected matrixCriteria(): MatrixCriterion[] {
    const revision = this.activeRevision();
    if (revision?.state === 'published') {
      return revision.configuration.criteria
        .filter((criterion) => criterion.is_active && criterion.block === this.evaluationBlock)
        .sort((left, right) => left.position - right.position)
        .map((criterion) => ({
          key: criterion.key,
          name: criterion.name,
          weight: Number(criterion.weight),
          componentId: criterion.legacy_component_id,
          configurable: true,
        }));
    }
    return this.components().filter((item) => item.is_active).map((component) => ({
      key: component.id,
      name: component.name,
      weight: component.weight,
      componentId: component.id,
      configurable: false,
    }));
  }

  protected loadCatalog(): void {
    const filters: Record<string, string> = {};
    if (this.gradeId) filters['grade_id'] = this.gradeId;
    if (this.sectionId) filters['section_id'] = this.sectionId;
    this.api.getAcademicCatalog(filters).subscribe({ next: (catalog) => this.catalog.set(catalog) });
    if (!this.sectionId) {
      this.courseId = '';
      this.periodId = '';
      this.components.set([]);
      this.activeRevision.set(null);
      this.grades.set([]);
    }
  }

  protected loadAcademicSetup(): void {
    this.scores = {};
    this.components.set([]);
    this.activeRevision.set(null);
    if (this.courseId) {
      this.api.listAssessmentComponents(this.courseId).subscribe({
        next: (items) => this.components.set(items),
      });
    }
    if (this.courseId && this.periodId) {
      this.api.getActiveEvaluationConfiguration(this.courseId, this.periodId).subscribe({
        next: (revision) => this.activeRevision.set(revision),
        error: () => this.message.set('No se pudo consultar la configuración de evaluación vigente.'),
      });
    }
    this.loadGrades();
  }

  protected scoreKey(studentId: string, criterionKey: string): string {
    return `${studentId}:${criterionKey}`;
  }

  protected invalidScore(value: number | null | undefined): boolean {
    return value !== null && value !== undefined
      && (!Number.isFinite(Number(value)) || Number(value) < 0 || Number(value) > 20);
  }

  protected average(studentId: string): number | null {
    const entries = this.matrixCriteria().map((criterion) => ({
      score: this.scores[this.scoreKey(studentId, criterion.key)], weight: criterion.weight,
    })).filter((item) => item.score !== null && item.score !== undefined
      && !this.invalidScore(item.score) && item.weight > 0);
    const weight = entries.reduce((sum, item) => sum + item.weight, 0);
    return weight
      ? entries.reduce((sum, item) => sum + Number(item.score) * item.weight, 0) / weight
      : null;
  }

  protected literal(studentId: string): string {
    const score = this.average(studentId);
    if (score === null) return '—';
    for (const threshold of this.catalog().literal_scale) {
      if (score > threshold.greater_than) return threshold.grade;
    }
    return 'C';
  }

  protected loadGrades(): void {
    if (!this.sectionId || !this.courseId || !this.periodId || !this.consultationMonth) {
      this.grades.set([]);
      return;
    }
    const filters = {
      grade_id: this.gradeId,
      section_id: this.sectionId,
      course_id: this.courseId,
      period_id: this.periodId,
      month: String(Number(this.consultationMonth.slice(5, 7))),
    };
    this.api.listGrades(filters).subscribe({ next: (items) => this.grades.set(items) });
  }

  protected saveAll(): void {
    if (!this.academicBimester || !this.evaluationName.trim() || !this.assessmentDate) {
      this.message.set('Selecciona bimestre, bloque, nombre y fecha de la evaluación.');
      return;
    }
    const criteria = this.matrixCriteria();
    const entries = this.catalog().students.flatMap((student) => criteria.flatMap((criterion) => {
      const value = this.scores[this.scoreKey(student.id, criterion.key)];
      return value === null || value === undefined
        ? [] : [{ student, criterion, score: Number(value) }];
    }));
    if (!entries.length) { this.message.set('Ingresa al menos una nota.'); return; }
    if (entries.some((entry) => this.invalidScore(entry.score))) {
      this.message.set('Corrige las notas marcadas: la escala permitida es 0–20.');
      return;
    }
    let saved = 0;
    entries.forEach(({ student, criterion, score }) => this.api.createGrade({
      student_id: student.id,
      course_id: this.courseId,
      period_id: this.periodId,
      component_id: criterion.componentId ?? undefined,
      academic_bimester: this.academicBimester ?? undefined,
      evaluation_block: this.evaluationBlock,
      evaluation_criterion_key: criterion.configurable ? criterion.key : undefined,
      evaluation_name: this.evaluationName.trim(),
      evaluation_type: criterion.configurable ? criterion.name : this.legacyEvidenceType,
      assessment_date: this.assessmentDate,
      score,
      qualitative_note: this.notes[student.id] || undefined,
    }).subscribe({
      next: () => {
        saved += 1;
        this.message.set(`${saved} de ${entries.length} notas guardadas.`);
        if (saved === entries.length) {
          this.consultationMonth = this.assessmentDate.slice(0, 7);
          this.loadGrades();
        }
      },
      error: (error: { error?: { detail?: string } }) => this.message.set(
        error.error?.detail ?? 'No se pudo guardar la matriz; revisa contexto y permisos.',
      ),
    }));
  }

  protected studentName(id: string): string {
    return this.catalog().students.find((student) => student.id === id)?.name ?? id;
  }

  protected update(grade: GradeRecord): void {
    if (this.invalidScore(grade.score)) {
      this.message.set('La nota debe estar entre 0 y 20.');
      return;
    }
    this.api.updateGrade(grade.id, {
      score: Number(grade.score), qualitative_note: grade.qualitative_note ?? '',
    }).subscribe({
      next: () => { this.message.set('Nota actualizada.'); this.loadGrades(); },
    });
  }

  protected async remove(grade: GradeRecord): Promise<void> {
    if (await this.confirm.ask('¿Eliminar esta calificación?')) {
      this.api.deleteGrade(grade.id).subscribe({ next: () => this.loadGrades() });
    }
  }
}
