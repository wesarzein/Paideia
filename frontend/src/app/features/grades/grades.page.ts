import { DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { academicNote } from '../../shared/academic-presentation';
import { concatMap, finalize, forkJoin, from, tap } from 'rxjs';

import {
  AcademicCatalog,
  ApiService,
  AssessmentComponent,
  EvaluationRevision,
  GradeRecord,
} from '../../core/services/api.service';
import { ConfirmService } from '../../core/services/confirm.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

const localToday = () => { const now = new Date(); return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10); };

const emptyCatalog = (): AcademicCatalog => ({
  grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [],
});

type MatrixCriterion = {
  key: string;
  name: string;
  weight: number;
  componentId: string | null;
  configurable: boolean;
  competency?: string;
};

@Component({
  standalone: true,
  imports: [DecimalPipe, FormsModule, PageHeaderComponent],
  template: `
    <app-page-header title="Calificaciones"
      description="Registra las evaluaciones de tus aulas y consulta las notas de cada bimestre." />
    <section class="panel filters">
      <label>Nivel<select [(ngModel)]="level" (ngModelChange)="gradeId = ''; sectionId = ''; loadCatalog()"><option value="">Seleccionar nivel</option>@for (item of levels(); track item) {<option [value]="item">{{ item }}</option>}</select></label>
      <label>Grado<select [(ngModel)]="gradeId" (ngModelChange)="sectionId = ''; loadCatalog()" [disabled]="!level"><option value="">Seleccionar grado</option>@for (grade of gradesForLevel(); track grade.id) {<option [value]="grade.id">{{ grade.name }}</option>}</select></label>
      <label>Sección<select [(ngModel)]="sectionId" (ngModelChange)="courseId = ''; loadCatalog()" [disabled]="!gradeId"><option value="">Seleccionar sección</option>@for (section of sectionsForGrade(); track section.id) {<option [value]="section.id">{{ section.name }}</option>}</select></label>
      <label>Curso<select [(ngModel)]="courseId" (ngModelChange)="loadAcademicSetup()" [disabled]="!sectionId"><option value="">Seleccionar curso</option>@for (course of catalog().courses; track course.id) {<option [value]="course.id">{{ course.name }}</option>}</select></label>
      <label>Periodo académico<select aria-label="Periodo académico" [(ngModel)]="periodId" (ngModelChange)="selectedEvaluation = ''; creatingEvaluation = false; loadAcademicSetup()" [disabled]="!sectionId"><option value="">Seleccionar periodo</option>@for (period of catalog().periods; track period.id) {<option [value]="period.id">{{ period.name }}</option>}</select></label>
      <label>Evaluación guardada<select aria-label="Evaluación guardada" [(ngModel)]="selectedEvaluation" (ngModelChange)="selectEvaluation($event)" [disabled]="!grades().length"><option value="">Seleccionar evaluación</option>@for (evaluation of savedEvaluations(); track evaluation.key) { <option [value]="evaluation.key">{{ evaluation.label }}</option> }</select></label>
    </section>
    @if (courseId && periodId) {
      <div class="evaluation-actions"><button type="button" (click)="newEvaluation()">Nueva evaluación</button><button type="button" (click)="loadGrades()">Actualizar notas</button><span>{{ grades().length }} notas guardadas en este periodo</span></div>
    }
    @if (courseId && periodId && activeRevision()?.state === 'published' && !isHistorical()) {
      <section class="panel course-competencies"><strong>Competencias del curso</strong>
        @for (competency of activeRevision()!.configuration.competencies; track competency.key) {
          @if (competency.is_active) { <span>{{ competency.name }}</span> }
        }
        <small>Los criterios y pesos aparecen en la tabla. Puedes dejar pendientes las notas que todavía no has evaluado.</small>
      </section>
    }
    @if (grades().length) {
      <section class="panel table-wrap"><h2>Notas por mes</h2>
        <p>Consulta los promedios mensuales de cada estudiante. Los meses sin registros quedan vacíos.</p>
        <table><thead><tr><th>Estudiante</th>@for (month of historyMonths(); track month) {<th>{{ monthLabel(month) }}</th>}</tr></thead><tbody>
          @for (student of catalog().students; track student.id) {<tr><td>{{ student.name }}</td>@for (month of historyMonths(); track month) {<td>{{ monthlyAverage(student.id, month) | number:'1.1-2' }}</td>}</tr>}
        </tbody></table>
      </section>
      <section class="panel table-wrap"><h2>Seguimiento de notas por bimestre</h2>
        <p>Promedios de referencia de las notas registradas, usando sus pesos originales. Los datos pendientes no se cuentan como cero.</p>
        <table><thead><tr><th>Estudiante</th>@for (bimester of [1,2,3,4]; track bimester) { <th>{{ bimester }}.º bimestre</th> }</tr></thead><tbody>
          @for (student of catalog().students; track student.id) { <tr><td>{{ student.name }}</td>@for (bimester of [1,2,3,4]; track bimester) { <td>{{ bimesterAverage(student.id, bimester) | number:'1.1-2' }}<small>{{ bimesterCount(student.id, bimester) }} notas</small></td> }</tr> }
        </tbody></table>
      </section>
    }
    @if (creatingEvaluation) {
      <section class="panel filters"><label>Bimestre<input aria-label="Bimestre" type="number" min="1" step="1" [(ngModel)]="academicBimester" (ngModelChange)="loadMatrix()" /></label><label>Bloque<select aria-label="Bloque" [(ngModel)]="evaluationBlock" (ngModelChange)="loadMatrix()"><option [ngValue]="1">Primer bloque</option><option [ngValue]="2">Segundo bloque</option></select></label><label>Nombre de evaluación<input aria-label="Nombre de evaluación" [(ngModel)]="evaluationName" (change)="loadMatrix()" maxlength="120" /></label><label>Fecha de evaluación<input aria-label="Fecha de evaluación" type="date" [(ngModel)]="assessmentDate" (ngModelChange)="loadMatrix()" /></label></section>
    }

    @if (isHistorical()) { <p class="period-caption">Historial bimestral sin fechas individuales. Puedes corregir las notas importadas; la configuración actual no cambia sus criterios.</p> } @else if (activeRevision()?.state === 'published') {
      <p class="period-caption">Bimestre {{ academicBimester || 'sin seleccionar' }} · bloque {{ evaluationBlock }}</p>
    } @else if (courseId && periodId) {
      <p class="period-caption">Las notas existentes conservan sus criterios y ponderaciones originales.</p>
    }
    @if (message()) { <p role="status" class="panel feedback">{{ message() }}</p> }

    @if (!sectionId || !courseId || !periodId) {
      <p class="panel">Selecciona grado, sección, curso y periodo para ver las notas del aula.</p>
    } @else if (!selectedEvaluation && !creatingEvaluation) {
      <p class="panel">Registra una nueva evaluación para comenzar. La importación de Excel sirve para cargar bimestres anteriores.</p>
    } @else if (!matrixCriteria().length) {
      <p class="panel">Configura las competencias y criterios en Mis cursos antes de registrar una evaluación nueva.</p>
    } @else {
      <section class="panel table-wrap">
        <table>
          <thead><tr><th>Código</th><th>Estudiante</th>@for (criterion of matrixCriteria(); track criterion.key) {<th>{{ criterion.name }}@if (criterion.competency) { <small>{{ criterion.competency }}</small> }<small>Peso {{ criterion.weight }}</small></th>}@for (competency of competencies(); track competency) { <th>{{ competency }}<small>Promedio de las notas registradas</small></th> }<th>{{ isHistorical() ? 'Promedio de referencia' : 'Promedio de la evaluación' }}</th><th>Literal</th><th>Observación</th></tr></thead>
          <tbody>
            @for (student of catalog().students; track student.id) {
              <tr><td>{{ student.student_code }}</td><td>{{ student.name }}</td>
                @for (criterion of matrixCriteria(); track criterion.key) {
                  <td><input type="number" min="0" max="20" step="0.1" [name]="scoreKey(student.id, criterion.key)" [(ngModel)]="scores[scoreKey(student.id, criterion.key)]" [class.invalid]="invalidScore(scores[scoreKey(student.id, criterion.key)])" [disabled]="isHistorical() && !persistedScore(student.id, criterion.key)" [attr.aria-label]="student.name + ' · ' + criterion.name" /></td>
                }
                @for (competency of competencies(); track competency) { <td>{{ competencyAverage(student.id, competency) | number:'1.1-2' }}</td> }<td>{{ average(student.id) | number:'1.1-2' }}</td><td>{{ literal(student.id) }}</td><td><input [name]="'note-' + student.id" [(ngModel)]="notes[student.id]" placeholder="Opcional" /></td>
              </tr>
            }
          </tbody>
        </table>
        @if (!catalog().students.length) { <p>No hay alumnos registrados en esta sección. Solicita a administración que revise el aula asignada.</p> }
        <p>Los cambios de pesos se aplican a las evaluaciones nuevas.</p>
        @if (matrixLoading()) { <p role="status">Cargando notas de la evaluación...</p> }
        <button type="button" (click)="saveAll()" [disabled]="!catalog().students.length || matrixLoading() || matrixError() || saving()">{{ saving() ? 'Guardando...' : 'Guardar calificaciones' }}</button>
      </section>
    }
  `,
  styles: [`
    .course-competencies{display:flex;gap:12px;flex-wrap:wrap;align-items:center}.course-competencies span{padding:6px 10px;border-radius:20px;background:var(--color-muted)}.course-competencies small{flex-basis:100%}.evaluation-actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 20px}.evaluation-actions button{margin:0}.evaluation-actions span{color:var(--color-muted-text);font-size:.9rem}
    .panel{background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;padding:20px;margin-bottom:16px}.filters{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}label{display:grid;gap:6px;color:var(--color-muted-text);font-size:.88rem}input,select{min-width:70px;padding:9px;border:1px solid var(--color-border);border-radius:7px;font:inherit;background:var(--color-surface)}.period-caption{margin:-6px 0 14px;color:var(--color-muted-text);font-size:.9rem}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid var(--color-border);text-align:left;white-space:nowrap}th{vertical-align:bottom;white-space:normal;min-width:100px;max-width:160px}th small{white-space:normal}.table-wrap input[type=number]{width:84px}.table-wrap section input{max-width:100%}small{display:block;color:var(--color-muted-text);font-weight:400}button{margin-top:14px;background:var(--color-primary);color:white;border:0;border-radius:5px;padding:10px 14px;cursor:pointer}.actions-cell{display:flex;gap:5px}.invalid{border-color:#b94b3b;background:#fff2ee}.feedback{color:var(--color-primary)}h2{font-size:1.15rem}@media(max-width:850px){.filters{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:520px){.filters{grid-template-columns:1fr}}
  `],
})
export class GradesPage {
  protected readonly academicNote = academicNote;
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
  protected assessmentDate = localToday();
  protected consultationMonth = new Date().toISOString().slice(0, 7);
  protected selectedEvaluation = '';
  protected creatingEvaluation = false;
  private gradesRequest = 0;
  protected scores: Record<string, number | null> = {};
  protected notes: Record<string, string> = {};
  protected readonly matrixLoading = signal(false);
  protected readonly matrixError = signal(false);
  protected readonly saving = signal(false);
  private persisted: Record<string, GradeRecord> = {};
  private loadedNotes: Record<string, string> = {};
  private loadedContext = '';
  private matrixRequest = 0;
  private setupRequest = 0;

  constructor() { this.loadCatalog(); }
  protected historyMonths() { return [...new Set(this.grades().map(g => g.academic_month || Number(g.assessment_date?.slice(5,7))).filter(m => m > 0))].sort((a,b) => a-b); }
  protected monthLabel(month: number) { return new Intl.DateTimeFormat('es-PE', { month: 'long' }).format(new Date(2026, month - 1, 1)); }
  protected monthlyRows(student: string, month: number) { return this.grades().filter(g => g.student_id === student && (g.academic_month || Number(g.assessment_date?.slice(5,7))) === month); }
  protected monthlyAverage(student: string, month: number) { const rows = this.monthlyRows(student, month); const weight = rows.reduce((s,g) => s + g.assessment_weight, 0); return weight ? rows.reduce((s,g) => s + g.score * g.assessment_weight, 0) / weight : null; }
  protected monthlySynthetic(student: string, month: number) { return this.monthlyRows(student, month).some(g => g.data_origin === 'synthetic'); }
  protected levels(): string[] { return [...new Set(this.catalog().grades.map((item) => item.level))]; }
  protected gradesForLevel() { return this.catalog().grades.filter((item) => item.level === this.level); }
  protected sectionsForGrade() { return this.catalog().sections.filter((item) => item.grade_id === this.gradeId); }
  protected gradeName(id: string) { return this.catalog().grades.find((item) => item.id === id)?.name ?? ''; }

  protected matrixCriteria(): MatrixCriterion[] {
    const revision = this.activeRevision();
    const selected = this.grades().filter(record => record.evaluation_name === this.evaluationName && (record.assessment_date ?? '') === this.assessmentDate);
    const usesCurrent = !selected.length || selected.every(record => record.evaluation_revision_id === revision?.id);
    if (!this.isHistorical() && usesCurrent && revision?.state === 'published') {
      return revision.configuration.criteria
        .filter((criterion) => criterion.is_active && criterion.block === this.evaluationBlock)
        .sort((left, right) => left.position - right.position)
        .map((criterion) => ({
          key: criterion.key,
          name: criterion.name,
          weight: Number(criterion.weight),
          componentId: criterion.legacy_component_id,
          configurable: true,
          competency: (revision.configuration.competencies ?? []).find(item => item.key === criterion.competency_key)?.name,
        }));
    }
    const criteria: MatrixCriterion[] = (this.isHistorical() || (revision?.state === "published" && !usesCurrent) ? [] : this.components()).filter((item) => item.is_active).map((component) => ({
      key: component.id,
      name: component.name,
      weight: component.weight,
      componentId: component.id,
      configurable: false,
    }));
    for (const record of this.grades()) {
      if (record.evaluation_name !== this.evaluationName || (record.assessment_date ?? '') !== this.assessmentDate) continue;
      if (criteria.some(item => item.componentId ? item.componentId === record.component_id : item.name === record.evaluation_type)) continue;
      criteria.push({ key: record.evaluation_criterion_key ?? record.component_id ?? `saved:${record.evaluation_type}`, name: record.evaluation_type, weight: record.assessment_weight, componentId: record.component_id, configurable: !!record.evaluation_criterion_key });
    }
    return criteria;
  }

  protected bimesterCount(studentId: string, bimester: number): number {
    return this.grades().filter(record => record.student_id === studentId && record.academic_bimester === bimester).length;
  }
  protected bimesterAverage(studentId: string, bimester: number): number | null {
    const records = this.grades().filter(record => record.student_id === studentId && record.academic_bimester === bimester && record.assessment_weight > 0);
    const weight = records.reduce((sum, record) => sum + record.assessment_weight, 0);
    return weight ? records.reduce((sum, record) => sum + record.score * record.assessment_weight, 0) / weight : null;
  }
  protected persistedScore(studentId: string, criterionKey: string): boolean { return !!this.persisted[this.scoreKey(studentId, criterionKey)]; }
  protected isHistorical(): boolean {
    return !this.creatingEvaluation && this.grades().some(record => record.record_kind === 'historical_bimester'
      && record.evaluation_name === this.evaluationName && (record.assessment_date ?? '') === this.assessmentDate);
  }
  protected competencies(): string[] {
    return [...new Set(this.matrixCriteria().map(item => item.competency).filter((name): name is string => !!name))];
  }
  protected competencyAverage(studentId: string, name: string): number | null {
    const entries = this.matrixCriteria().filter(item => item.competency === name).map(item => ({
      score: this.scores[this.scoreKey(studentId, item.key)], weight: this.persisted[this.scoreKey(studentId, item.key)]?.assessment_weight ?? item.weight,
    })).filter(item => item.score != null && !this.invalidScore(item.score) && item.weight > 0);
    const weight = entries.reduce((sum, item) => sum + item.weight, 0);
    return weight ? entries.reduce((sum, item) => sum + Number(item.score) * item.weight, 0) / weight : null;
  }

  protected savedEvaluations() {
    const evaluations = new Map<string, { key: string; label: string; record: GradeRecord }>();
    for (const record of this.grades()) {
      const key = JSON.stringify([record.evaluation_name, record.assessment_date, record.academic_bimester, record.evaluation_block]);
      evaluations.set(key, { key, record, label: record.record_kind === 'historical_bimester' ? `Historial ${record.academic_month ? this.monthLabel(record.academic_month) : ""} · Bimestre ${record.academic_bimester} · Bloque ${record.evaluation_block}` : `${record.evaluation_name}${record.assessment_date ? ' · ' + record.assessment_date : ''}${record.academic_bimester ? ' · Bimestre ' + record.academic_bimester : ''}${record.evaluation_block ? ' · Bloque ' + record.evaluation_block : ''}` });
    }
    return [...evaluations.values()].sort((a, b) => (b.record.assessment_date ?? '').localeCompare(a.record.assessment_date ?? ''));
  }
  protected selectEvaluation(key: string): void {
    const record = this.savedEvaluations().find(item => item.key === key)?.record;
    if (!record) return;
    this.creatingEvaluation = false; this.selectedEvaluation = key;
    this.evaluationName = record.evaluation_name; this.assessmentDate = record.assessment_date ?? '';
    this.academicBimester = record.academic_bimester; this.evaluationBlock = record.evaluation_block ?? 1;
    this.loadMatrix();
  }
  protected newEvaluation(): void {
    this.creatingEvaluation = true; this.selectedEvaluation = ''; this.evaluationName = '';
    this.academicBimester = null; this.evaluationBlock = 1;
    this.assessmentDate = localToday(); this.loadMatrix();
  }

  protected loadCatalog(): void {
    ++this.gradesRequest;
    const filters: Record<string, string> = {};
    if (this.gradeId) filters['grade_id'] = this.gradeId;
    if (this.sectionId) filters['section_id'] = this.sectionId;
    this.api.getAcademicCatalog(filters).subscribe({ next: (catalog) => this.catalog.set(catalog) });
    if (!this.sectionId) {
      ++this.setupRequest;
      this.courseId = '';
      this.periodId = '';
      this.components.set([]);
      this.activeRevision.set(null);
      this.grades.set([]);
      this.loadMatrix();
    }
  }

  protected loadAcademicSetup(): void {
    const request = ++this.setupRequest;
    ++this.gradesRequest; ++this.matrixRequest;
    this.grades.set([]);
    this.scores = {};
    this.components.set([]);
    this.activeRevision.set(null);
    this.matrixLoading.set(true);
    if (this.courseId && this.periodId) {
      forkJoin({ components: this.api.listAssessmentComponents(this.courseId), revision: this.api.getActiveEvaluationConfiguration(this.courseId, this.periodId) }).subscribe({
        next: ({ components, revision }) => {
          if (request !== this.setupRequest) return;
          this.components.set(components);
          this.activeRevision.set(revision);
          this.loadGrades();
        },
        error: () => {
          if (request !== this.setupRequest) return;
          this.matrixLoading.set(false); this.matrixError.set(true);
          this.message.set('No se pudo consultar la configuración de evaluación vigente.');
        },
      });
    } else {
      this.grades.set([]);
      this.loadMatrix();
    }
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
      score: this.scores[this.scoreKey(studentId, criterion.key)], weight: this.persisted[this.scoreKey(studentId, criterion.key)]?.assessment_weight ?? criterion.weight,
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
    const request = ++this.gradesRequest;
    if (!this.sectionId || !this.courseId || !this.periodId) {
      this.grades.set([]);
      return;
    }
    const filters = {
      grade_id: this.gradeId,
      section_id: this.sectionId,
      course_id: this.courseId,
      period_id: this.periodId,
    };
    this.api.listGrades(filters).subscribe({ next: (items) => {
      if (request !== this.gradesRequest) return;
      this.grades.set(items);
      if (!this.creatingEvaluation && !this.savedEvaluations().some(item => item.key === this.selectedEvaluation)) this.selectedEvaluation = this.savedEvaluations()[0]?.key ?? '';
      if (this.selectedEvaluation) this.selectEvaluation(this.selectedEvaluation); else this.loadMatrix();
    }, error: () => { if (request === this.gradesRequest) { this.matrixError.set(true); this.matrixLoading.set(false); this.message.set('No se pudieron cargar las notas guardadas. Pulsa Actualizar notas para reintentar.'); } } });
  }

  private matrixContext(): string {
    return JSON.stringify([this.gradeId, this.sectionId, this.courseId, this.periodId,
      this.academicBimester, this.evaluationBlock, this.evaluationName.trim(), this.assessmentDate,
      this.activeRevision()?.id, this.legacyEvidenceType]);
  }

  protected loadMatrix(): void {
    const request = ++this.matrixRequest;
    const context = this.matrixContext();
    if (context !== this.loadedContext) {
      this.scores = {}; this.notes = {}; this.persisted = {}; this.loadedNotes = {};
      this.loadedContext = context;
    }
    this.matrixError.set(false);
    if (!this.sectionId || !this.courseId || !this.periodId || !this.evaluationName.trim() || (!this.assessmentDate && !this.isHistorical())) {
      this.matrixLoading.set(false);
      return;
    }
    this.matrixLoading.set(true);
    const filters: Record<string, string> = {
      grade_id: this.gradeId, section_id: this.sectionId, course_id: this.courseId,
      period_id: this.periodId, evaluation_name: this.evaluationName.trim(),
      ...(this.assessmentDate ? { assessment_date: this.assessmentDate } : {}),
    };
    if (this.academicBimester) { filters['academic_bimester'] = String(this.academicBimester); filters['evaluation_block'] = String(this.evaluationBlock); }
    this.api.listGrades(filters).subscribe({ next: (records) => {
      if (request !== this.matrixRequest || context !== this.matrixContext()) return;
      const persisted: Record<string, GradeRecord> = {};
      const loadedNotes: Record<string, string> = {};
      for (const record of records) {
        if (this.isHistorical() !== (record.record_kind === "historical_bimester")) continue;
        const criterion = this.matrixCriteria().find((item) => item.configurable
          ? item.key === record.evaluation_criterion_key : item.componentId ? item.componentId === record.component_id : item.name === record.evaluation_type);
        if (!criterion) continue;
        const key = this.scoreKey(record.student_id, criterion.key);
        if (persisted[key]) {
          this.matrixError.set(true); this.matrixLoading.set(false);
          this.message.set('Hay notas ambiguas para este contexto; revisa la consulta antes de guardar.');
          return;
        }
        persisted[key] = record;
        if (!(key in this.scores) || this.scores[key] === this.persisted[key]?.score) this.scores[key] = record.score;
        if (!(record.student_id in loadedNotes)) {
          loadedNotes[record.student_id] = academicNote(record.qualitative_note, record.data_origin);
          if (!(record.student_id in this.notes) || this.notes[record.student_id] === this.loadedNotes[record.student_id]) this.notes[record.student_id] = loadedNotes[record.student_id];
        }
      }
      for (const key of Object.keys(this.persisted)) {
        if (!(key in persisted)) {
          if (this.scores[key] !== this.persisted[key].score) {
            this.matrixError.set(true); this.matrixLoading.set(false);
            this.message.set('Una nota editada ya no existe en este contexto; vuelve a seleccionar la evaluación.');
            return;
          }
          delete this.scores[key];
        }
      }
      this.persisted = persisted;
      this.loadedNotes = loadedNotes;
      this.matrixLoading.set(false);
    }, error: () => {
      if (request !== this.matrixRequest) return;
      this.matrixError.set(true); this.matrixLoading.set(false);
      this.message.set('No se pudo cargar la evaluación; reintenta antes de guardar.');
    } });
  }

  protected saveAll(): void {
    if (this.saving() || this.matrixLoading() || this.matrixError()) return;
    if ((!this.academicBimester && (this.creatingEvaluation || this.activeRevision()?.state === 'published')) || !this.evaluationName.trim() || (!this.assessmentDate && !this.isHistorical())) {
      this.message.set('Selecciona bimestre, bloque, nombre y fecha de la evaluación.');
      return;
    }
    const criteria = this.matrixCriteria();
    const entries = this.catalog().students.flatMap((student) => criteria.flatMap((criterion) => {
      const value = this.scores[this.scoreKey(student.id, criterion.key)];
      return value === null || value === undefined
        ? [] : this.isHistorical() && !this.persisted[this.scoreKey(student.id, criterion.key)] ? [] : [{ student, criterion, score: Number(value) }];
    }));
    if (!entries.length) { this.message.set('Ingresa al menos una nota.'); return; }
    if (entries.some((entry) => this.invalidScore(entry.score))) {
      this.message.set('Corrige las notas marcadas: la escala permitida es 0–20.');
      return;
    }
    const context = this.matrixContext();
    const common = { course_id: this.courseId, period_id: this.periodId,
      academic_bimester: this.academicBimester ?? undefined, evaluation_block: this.academicBimester ? this.evaluationBlock : undefined,
      evaluation_name: this.evaluationName.trim(), assessment_date: this.assessmentDate };
    const writes = entries.map(({ student, criterion, score }) => {
      const key = this.scoreKey(student.id, criterion.key);
      const existing = this.persisted[key];
      const noteChanged = this.notes[student.id] !== this.loadedNotes[student.id];
      const note = noteChanged ? this.notes[student.id] || '' : existing?.qualitative_note ?? '';
      return { key, existing, score, note, noteChanged, payload: { ...common, student_id: student.id,
        component_id: criterion.componentId ?? undefined,
        evaluation_criterion_key: criterion.configurable ? criterion.key : undefined,
        evaluation_type: criterion.name,
        score, qualitative_note: this.notes[student.id] || undefined } };
    }).filter((entry) => !entry.existing || entry.score !== entry.existing.score || entry.note !== (entry.existing.qualitative_note ?? ''));
    if (!writes.length) { this.message.set('Sin cambios: las notas registradas ya coinciden.'); return; }
    this.saving.set(true);
    let saved = 0;
    from(writes).pipe(concatMap((entry) => (entry.existing
      ? this.api.updateGrade(entry.existing.id, { score: entry.score, qualitative_note: entry.noteChanged ? entry.note : undefined })
      : this.api.createGrade(entry.payload)).pipe(tap((record) => {
        saved += 1;
        if (context === this.matrixContext()) this.persisted[entry.key] = record;
      }))), finalize(() => this.saving.set(false))).subscribe({
      complete: () => {
        this.message.set(`${saved} de ${writes.length} notas guardadas.`);
        if (context === this.matrixContext() && common.assessment_date) this.consultationMonth = common.assessment_date.slice(0, 7);
        this.loadGrades(); this.loadMatrix();
      },
      error: (error: { error?: { detail?: string } }) => {
        this.message.set(`${saved} de ${writes.length} notas guardadas. ${error.error?.detail ?? 'No se pudo completar el guardado; reintenta las restantes.'}`);
      },
    });
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
      next: () => { this.message.set('Nota actualizada.'); this.loadGrades(); this.loadMatrix(); },
      error: (error) => this.message.set(typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo guardar la calificación. Reintenta la operación.'),
    });
  }

  protected async remove(grade: GradeRecord): Promise<void> {
    if (await this.confirm.ask('¿Eliminar esta calificación?')) {
      this.api.deleteGrade(grade.id).subscribe({ next: () => { this.loadGrades(); this.loadMatrix(); }, error: () => this.message.set('No se pudo eliminar la calificación. Reintenta la operación.') });
    }
  }
}
