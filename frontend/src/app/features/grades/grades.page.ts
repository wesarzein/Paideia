import { DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
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
      <label>Bimestre institucional<input type="number" min="1" step="1" [(ngModel)]="academicBimester" (ngModelChange)="loadMatrix()" placeholder="Seleccionar" /></label>
      <label>Bloque de evaluación<select [(ngModel)]="evaluationBlock" (ngModelChange)="loadMatrix()"><option [ngValue]="1">Primer bloque · semana 4</option><option [ngValue]="2">Segundo bloque · semana 8</option></select></label>
      <label>Nombre de evaluación<input [(ngModel)]="evaluationName" (change)="loadMatrix()" maxlength="120" placeholder="Nombre confirmado por el docente" /></label>
      <label>Fecha de evaluación<input type="date" [(ngModel)]="assessmentDate" (ngModelChange)="loadMatrix()" /></label>
      <label>Tipo de evidencia legado<select [(ngModel)]="legacyEvidenceType" (ngModelChange)="loadMatrix()">@for (type of evidenceTypes; track type) {<option [value]="type">{{ type }}</option>}</select></label>
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
        <p>Al corregir notas registradas se conserva su versión y peso histórico.</p>
        @if (matrixLoading()) { <p role="status">Cargando notas de la evaluación...</p> }
        <button type="button" (click)="saveAll()" [disabled]="!catalog().students.length || matrixLoading() || matrixError() || saving()">{{ saving() ? 'Guardando...' : 'Guardar matriz' }}</button>
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
  protected readonly matrixLoading = signal(false);
  protected readonly matrixError = signal(false);
  protected readonly saving = signal(false);
  private persisted: Record<string, GradeRecord> = {};
  private loadedNotes: Record<string, string> = {};
  private loadedContext = '';
  private matrixRequest = 0;
  private setupRequest = 0;

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
          this.loadMatrix();
        },
        error: () => {
          if (request !== this.setupRequest) return;
          this.matrixLoading.set(false); this.matrixError.set(true);
          this.message.set('No se pudo consultar la configuración de evaluación vigente.');
        },
      });
    } else {
      this.loadMatrix();
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
    if (!this.sectionId || !this.courseId || !this.periodId || !this.academicBimester || !this.evaluationName.trim() || !this.assessmentDate) {
      this.matrixLoading.set(false);
      return;
    }
    this.matrixLoading.set(true);
    const filters: Record<string, string> = {
      grade_id: this.gradeId, section_id: this.sectionId, course_id: this.courseId,
      period_id: this.periodId, academic_bimester: String(this.academicBimester),
      evaluation_block: String(this.evaluationBlock), evaluation_name: this.evaluationName.trim(),
      assessment_date: this.assessmentDate,
    };
    if (this.activeRevision()?.state !== 'published') filters['evaluation_type'] = this.legacyEvidenceType;
    this.api.listGrades(filters).subscribe({ next: (records) => {
      if (request !== this.matrixRequest || context !== this.matrixContext()) return;
      const persisted: Record<string, GradeRecord> = {};
      const loadedNotes: Record<string, string> = {};
      for (const record of records) {
        const criterion = this.matrixCriteria().find((item) => item.configurable
          ? item.key === record.evaluation_criterion_key : item.componentId === record.component_id);
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
          loadedNotes[record.student_id] = record.qualitative_note ?? '';
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
    const context = this.matrixContext();
    const common = { course_id: this.courseId, period_id: this.periodId,
      academic_bimester: this.academicBimester, evaluation_block: this.evaluationBlock,
      evaluation_name: this.evaluationName.trim(), assessment_date: this.assessmentDate };
    const writes = entries.map(({ student, criterion, score }) => {
      const key = this.scoreKey(student.id, criterion.key);
      const existing = this.persisted[key];
      const noteChanged = this.notes[student.id] !== this.loadedNotes[student.id];
      const note = noteChanged ? this.notes[student.id] || '' : existing?.qualitative_note ?? '';
      return { key, existing, score, note, noteChanged, payload: { ...common, student_id: student.id,
        component_id: criterion.componentId ?? undefined,
        evaluation_criterion_key: criterion.configurable ? criterion.key : undefined,
        evaluation_type: criterion.configurable ? criterion.name : this.legacyEvidenceType,
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
        if (context === this.matrixContext()) this.consultationMonth = common.assessment_date.slice(0, 7);
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
    });
  }

  protected async remove(grade: GradeRecord): Promise<void> {
    if (await this.confirm.ask('¿Eliminar esta calificación?')) {
      this.api.deleteGrade(grade.id).subscribe({ next: () => { this.loadGrades(); this.loadMatrix(); } });
    }
  }
}
