import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AcademicCatalog, ApiService, GradeImportReview, ImportPreview, InstitutionalContext } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [FormsModule, PageHeaderComponent],
  template: `
    <app-page-header title="Importación" description="Carga estudiantes o calificaciones desde CSV o Excel, revisa errores y valida antes de guardar." />
    <section class="panel modes">
      <button type="button" [class.active]="mode() === 'students'" (click)="setMode('students')">Estudiantes</button>
      <button type="button" [class.active]="mode() === 'grades'" (click)="setMode('grades')">Calificaciones</button>
    </section>
    @if (mode() === 'grades') {
      <section class="panel filters">
        <label>Curso<select [(ngModel)]="courseId" (ngModelChange)="contextChanged()" [disabled]="busy()"><option value="">Seleccionar curso</option>@for (course of catalog().courses; track course.id) {<option [value]="course.id">{{ course.name }}</option>}</select></label>
        <label>Periodo<select [(ngModel)]="periodId" (ngModelChange)="contextChanged()" [disabled]="busy()"><option value="">Seleccionar periodo</option>@for (period of catalog().periods; track period.id) {<option [value]="period.id">{{ period.name }}</option>}</select></label>
      </section>
    } @else {
      <section class="panel filters">
        <label>Nivel<select [(ngModel)]="level" (ngModelChange)="gradeId = ''; sectionId = ''; loadCatalog()"><option value="">Seleccionar nivel</option>@for (item of levels(); track item) {<option [value]="item">{{ item }}</option>}</select></label>
        <label>Grado<select [(ngModel)]="gradeId" (ngModelChange)="sectionId = ''; loadCatalog()" [disabled]="!level"><option value="">Seleccionar grado</option>@for (grade of gradesForLevel(); track grade.id) {<option [value]="grade.id">{{ grade.name }}</option>}</select></label>
        <label>Sección<select [(ngModel)]="sectionId" (ngModelChange)="loadCatalog()" [disabled]="!gradeId"><option value="">Seleccionar sección</option>@for (section of sectionsForGrade(); track section.id) {<option [value]="section.id">{{ gradeName(section.grade_id) }} · {{ section.name }}</option>}</select></label>
      </section>
    }
    @if (mode() === 'grades') { <p class="format-hint">Las evaluaciones se organizan en bloques de cuatro semanas y bimestres de ocho semanas. Los rótulos 1 MES y 2 MES no indican enero y febrero; confirma las fechas del calendario académico. Evidencias permitidas: Actitud ante el área, Cuaderno, Módulo, Exposición-Trabajos y Evaluación.</p> }
    <section class="dropzone" (dragover)="$event.preventDefault()" (drop)="drop($event)">
      <svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 31V8m-8 8 8-8 8 8M8 29v11h32V29" /></svg><strong>Arrastra tu archivo aquí</strong><span>CSV o Excel (.xlsx, .xls)</span>
      <input #fileInput type="file" accept=".csv,.xlsx,.xls" (change)="select($event)" />
      <button type="button" class="file-button" (click)="fileInput.click()">Seleccionar archivo</button>
      @if (fileName()) { <small class="file-name">{{ fileName() }}</small> }
    </section>
    @if (message()) { <p class="message">{{ message() }}</p> }
    @if (preview()) {
      <section class="panel preview">
        <h2>Vista previa: {{ preview()!.total }} filas</h2>
        @if (mode() === 'grades') { <p class="context"><strong>Curso:</strong> {{ courseName() }} · <strong>Periodo:</strong> {{ periodName() }}</p> }
        @if (preview()!.institutional) {
          <p>{{ preview()!.institutional!.warning }} {{ preview()!.institutional!.blank_inputs }} entradas vacías omitidas.</p>
          <details><summary>Estudiantes del archivo, incluidos los que no tienen notas</summary>@for (student of preview()!.institutional!.students; track student.source_row) { <p>Fila {{ student.source_row }}: {{ student.student_code }} · {{ student.name }}</p> }</details>
          @if (preview()!.institutional!.unsupported_formula_rows.length) { <p class="error">Hay fórmulas no reconocidas en las filas {{ preview()!.institutional!.unsupported_formula_rows.join(', ') }}. No se ejecutan ni se calculan sus resultados de referencia; verifica la plantilla.</p> }
          <section class="filters" aria-label="Contexto institucional">
            <label>Año académico<input type="number" [(ngModel)]="schoolYear" (ngModelChange)="contextChanged()" [disabled]="busy()" /></label>
            <label>Bimestre<input type="number" min="1" [(ngModel)]="bimestre" (ngModelChange)="contextChanged()" [disabled]="busy()" /></label>
            <label>Grado institucional<select [(ngModel)]="gradeId" (ngModelChange)="sectionId = ''; loadCatalog(); contextChanged()" [disabled]="busy()"><option value="">Seleccionar grado</option>@for (grade of catalog().grades; track grade.id) {<option [value]="grade.id">{{ grade.level }} · {{ grade.name }}</option>}</select></label>
            <label>Sección institucional<select [(ngModel)]="sectionId" (ngModelChange)="loadCatalog(); contextChanged()" [disabled]="busy() || !gradeId"><option value="">Seleccionar sección</option>@for (section of sectionsForGrade(); track section.id) {<option [value]="section.id">{{ section.name }}</option>}</select></label>
            @for (block of preview()!.institutional!.blocks; track block.block) {
              <label>Evaluación {{ block.label }}<input [(ngModel)]="blocks[block.block].evaluation_name" (ngModelChange)="contextChanged()" [disabled]="busy()" /></label>
              <label>Fecha {{ block.label }}<input type="date" [(ngModel)]="blocks[block.block].assessment_date" (ngModelChange)="contextChanged()" [disabled]="busy()" /></label>
              <p>{{ block.label }}: @for (criterion of block.criteria; track criterion.name) { {{ criterion.header }}; }</p>
            }
          </section>
          <label><input type="checkbox" [(ngModel)]="contextConfirmed" (ngModelChange)="invalidateReview()" [disabled]="busy()" />Confirmo curso, periodo, año, grado, sección, bimestre y calendario de ambos bloques.</label>
          <details><summary>Fórmulas y cachés de referencia del archivo (no se guardan como notas)</summary>@for (cell of preview()!.institutional!.derived; track cell.cell) { <p>{{ cell.cell }}: {{ cell.formula }} · caché: {{ cell.cached }}</p> }</details>
        }
        @if (rowErrors().length) { <p class="error">{{ rowErrors().length }} filas tienen errores; edita las celdas antes de confirmar.</p> }
        @if (!rowErrors().length && mode() === 'students') { <p>El código del archivo se usa como referencia; Paideia genera el código institucional según el grado, sección y orden de importación.</p><button type="button" (click)="importStudents()" [disabled]="!gradeId || !sectionId">Confirmar e importar padrón</button> }
        @if (mode() === 'grades') {
          <button type="button" (click)="reviewGrades()" [disabled]="busy() || !courseId || !periodId || !preview()!.total">Revisar registros existentes</button>
          <button type="button" (click)="importGrades()" [disabled]="busy() || !reviewReady()">Confirmar e importar calificaciones</button>
          @if (review()) {
            @for (result of review()!.reference_results ?? []; track result.source_row) { <p>Fila Excel {{ result.source_row }} · Referencia institucional: bloque 1 {{ result.monthly['1'] ?? 'incompleto/no reconocido' }} · bloque 2 {{ result.monthly['2'] ?? 'incompleto/no reconocido' }} · final {{ result.final ?? '—' }} · literal {{ result.literal ?? '—' }}. Vista de referencia; no reemplaza el cálculo histórico del curso.</p> }
            <p>Las coincidencias idénticas se omiten. Para cada diferencia decide si conservas la nota guardada o confirmas su actualización.</p>
            @for (error of review()!.errors; track $index) { <p class="error">Fila {{ error.row }}: {{ error.error }}</p> }
            <table aria-label="Comparación de calificaciones"><thead><tr><th>Fila</th><th>Estado</th><th>Guardado</th><th>Archivo</th><th>Decisión</th></tr></thead><tbody>
              @for (item of review()!.rows; track item.row) {
                <tr><td>{{ item.row }}</td><td>{{ statusLabel(item.status) }}</td><td>{{ item.existing?.score ?? '—' }} · {{ item.existing?.qualitative_note ?? '' }}</td><td>{{ preview()!.rows[item.row - 1]['score'] }} · {{ preview()!.rows[item.row - 1]['qualitative_note'] ?? '' }}</td><td>
                  @if (item.status === 'different') { <select [(ngModel)]="item.decision" [disabled]="busy()" [attr.aria-label]="'Decisión fila ' + item.row"><option value="">Seleccionar decisión</option><option value="keep">Conservar nota existente</option><option value="update">Confirmar actualización</option></select> }
                </td></tr>
              }
            </tbody></table>
          }
        }
        <table><thead><tr>@for (column of preview()!.columns; track column) { <th>{{ column }}</th> }</tr></thead><tbody>@for (row of preview()!.rows; track $index; let rowIndex = $index) { <tr>@for (column of preview()!.columns; track column) { <td>@if (preview()!.institutional && column === 'student_code') {
          <select [ngModel]="row['student_code']" (ngModelChange)="resolveStudent(row, $event)" [disabled]="busy()" [attr.aria-label]="'Estudiante fila ' + (rowIndex + 1)"><option [value]="row['student_code']">{{ row['student_code'] }} · referencia del archivo</option>@for (student of catalog().students; track student.id) {<option [value]="student.student_code">{{ student.student_code }} · {{ student.name }}</option>}</select>
          <label><input type="checkbox" [(ngModel)]="$any(row)['student_confirmed']" (ngModelChange)="invalidateReview()" [disabled]="busy()" />Confirmar correspondencia</label>
        } @else {<input [attr.aria-label]="column + ' fila ' + (rowIndex + 1)" [readonly]="!!preview()!.institutional && ['source_name', 'source_block', 'evaluation_type', 'evaluation_name', 'assessment_date'].includes(column)" [type]="column === 'assessment_date' ? 'date' : 'text'" [(ngModel)]="$any(row)[column]" (ngModelChange)="invalidateReview()" [disabled]="busy()" [name]="'import-' + rowIndex + '-' + column" />} </td> }</tr> }</tbody></table>
      </section>
    }
  `,
  styles: [`
    .panel, .dropzone { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: 22px; margin-bottom: 18px; }
    .modes { display: flex; gap: 10px; } .modes button, button { background: var(--color-primary); color: white; border: 0; border-radius: 6px; padding: 11px 16px; cursor: pointer; } .modes button:not(.active) { background: transparent; color: var(--color-primary); border: 1px solid var(--color-primary); }
    .filters { display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 14px; } label { display: grid; gap: 7px; color: var(--color-muted-text); } select { border: 1px solid var(--color-border); border-radius: 6px; padding: 10px; font: inherit; background:var(--color-surface) }
    .format-hint{margin:0 0 14px;padding:12px 14px;border:1px solid var(--color-border);border-radius:8px;background:#f8fafc;color:var(--color-muted-text);font-size:.9rem;line-height:1.5}
    .dropzone { display: grid; justify-items: center; gap: 8px; border: 2px dashed #cbd5e1; text-align:center; transition:background .15s,border-color .15s } .dropzone:hover{border-color:var(--color-accent);background:#fffaf2}.dropzone svg{width:42px;height:42px;fill:none;stroke:var(--color-primary);stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}.dropzone span, small { color: var(--color-muted-text); } .dropzone input { position:absolute;width:1px;height:1px;opacity:0;pointer-events:none }.dropzone .file-button{margin-top:6px;background:#fff;color:var(--color-primary);border:1px solid var(--color-border);border-radius:7px;padding:9px 14px;font:inherit;font-weight:600}.dropzone .file-button:hover{border-color:var(--color-primary);background:#f8fafc}.file-name{max-width:100%;overflow-wrap:anywhere}
    .preview { overflow-x: auto; } table { width: 100%; border-collapse: collapse; } th, td { padding: 7px; border-bottom: 1px solid var(--color-border); text-align: left; white-space: nowrap; } td input { width:100%; min-width:120px; border:1px solid var(--color-border); border-radius:4px; padding:8px; font:inherit; } .context { color: var(--color-primary); } .error { color: #a33a32; } .message { color: var(--color-primary); } @media(max-width:700px){ .filters { grid-template-columns: 1fr; } }
  `],
})
export class PlaceholderPage {
  private readonly api = inject(ApiService);
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] });
  protected readonly mode = signal<'students' | 'grades'>('students');
  protected readonly preview = signal<ImportPreview | null>(null);
  protected readonly fileName = signal('');
  protected readonly message = signal('');
  protected readonly review = signal<GradeImportReview | null>(null);
  protected readonly busy = signal(false);
  private reviewedSignature = '';
  protected level = '';
  protected gradeId = '';
  protected sectionId = '';
  protected courseId = '';
  protected periodId = '';
  protected schoolYear: number | null = null;
  protected bimestre: number | null = null;
  protected contextConfirmed = false;
  protected blocks: Record<string, { evaluation_name: string; assessment_date: string }> = { '1': { evaluation_name: '', assessment_date: '' }, '2': { evaluation_name: '', assessment_date: '' } };
  private selectedFile: File | null = null;

  protected contextChanged(): void {
    this.contextConfirmed = false;
    const preview = this.preview();
    if (preview?.institutional) {
      for (const row of preview.rows) {
        const block = this.blocks[String(row['source_block'])];
        if (block) { row['evaluation_name'] = block.evaluation_name; row['assessment_date'] = block.assessment_date; }
      }
    }
    this.invalidateReview();
  }
  protected resolveStudent(row: Record<string, unknown>, code: string): void {
    for (const related of this.preview()?.rows ?? []) {
      if (related['source_row'] === row['source_row'] && related['source_sheet'] === row['source_sheet']) {
        related['student_code'] = code; related['student_confirmed'] = true;
      }
    }
    this.invalidateReview();
  }
  private academicContext(): InstitutionalContext | undefined {
    return this.preview()?.institutional ? { school_year: this.schoolYear, bimestre: this.bimestre, grade_id: this.gradeId, section_id: this.sectionId, confirmed: this.contextConfirmed, blocks: this.blocks } : undefined;
  }

  constructor() { this.loadCatalog(); }

  protected levels(): string[] { return [...new Set(this.catalog().grades.map((item) => item.level))]; }
  protected gradesForLevel() { return this.catalog().grades.filter((item) => item.level === this.level); }
  protected sectionsForGrade() { return this.catalog().sections.filter((item) => item.grade_id === this.gradeId); }
  protected gradeName(id: string) { return this.catalog().grades.find((item) => item.id === id)?.name ?? ''; }
  protected loadCatalog(): void { const filters: Record<string, string> = {}; if (this.gradeId) filters['grade_id'] = this.gradeId; if (this.sectionId) filters['section_id'] = this.sectionId; this.api.getAcademicCatalog(filters).subscribe({ next: (catalog) => this.catalog.set(catalog) }); }
  protected rowErrors(): string[] {
    const rows = this.preview()?.rows ?? [];
    const rowErrors = rows.flatMap((row, index) => {
      const errors: string[] = [];
      if (this.mode() === 'students' && (!String(row['student_code'] ?? '').trim() || !String(row['first_name'] ?? '').trim() || !String(row['last_name'] ?? '').trim())) errors.push(`Fila ${index + 2}: código, nombres y apellidos son obligatorios`);
      if (this.mode() === 'grades') { const score = Number(row['score']); if (!String(row['student_code'] ?? '').trim()) errors.push(`Fila ${index + 2}: falta código`); if (!String(row['score'] ?? '').trim() || !Number.isFinite(score) || score < 0 || score > 20) errors.push(`Fila ${index + 2}: nota debe estar entre 0 y 20`); if (!String(row['assessment_date'] ?? '').trim()) errors.push(`Fila ${index + 2}: asigna una fecha de evaluación`); }
      return errors;
    });
    return [...rowErrors, ...(this.preview()?.errors ?? []).map((error) => `Fila ${error.row}: ${error.error}`)];
  }

  protected setMode(mode: 'students' | 'grades'): void { if (this.busy()) return; this.mode.set(mode); this.preview.set(null); this.invalidateReview(); this.message.set(''); this.selectedFile = null; this.fileName.set(''); }
  protected select(event: Event): void { const file = (event.target as HTMLInputElement).files?.[0]; if (file) this.previewFile(file); }
  protected drop(event: DragEvent): void { event.preventDefault(); const file = event.dataTransfer?.files[0]; if (file) this.previewFile(file); }
  protected importGrades(): void {
    if (this.busy() || !this.reviewReady()) { this.message.set('Revisa los registros y decide sobre las diferencias antes de confirmar.'); return; }
    const rows = this.preview()!.rows.map((row, index) => {
      const item = this.review()!.rows[index];
      return { ...row, component_id: item.component_id, decision: item.decision, review_token: item.review_token };
    });
    this.busy.set(true);
    this.api.commitGradeRows(rows, this.courseId, this.periodId, this.academicContext()).subscribe({
      next: (result) => { this.busy.set(false); this.invalidateReview(); this.message.set(`${result.imported} nuevas; ${result.updated} actualizadas; ${result.skipped} omitidas; ${result.rejected} rechazadas.`); },
      error: (error) => { this.busy.set(false); this.invalidateReview(); this.message.set(this.importError(error)); },
    });
  }

  protected invalidateReview(): void {
    this.review.set(null); this.reviewedSignature = '';
    if (this.mode() === 'grades' && this.preview()) this.preview.set({ ...this.preview()!, errors: [] });
  }
  private reviewSignature(): string { return JSON.stringify([this.courseId, this.periodId, this.preview()?.rows, this.academicContext()]); }
  protected reviewReady(): boolean {
    return !!this.review() && !this.review()!.errors.length && this.reviewedSignature === this.reviewSignature()
      && this.review()!.rows.every((item) => item.status !== 'different' || item.decision === 'keep' || item.decision === 'update');
  }
  protected statusLabel(status: string): string {
    return ({ new: 'Nueva', identical: 'Ya existe: idéntica', different: 'Diferencia', ambiguous: 'Ambigua', duplicate_in_file: 'Repetida en archivo' } as Record<string, string>)[status] ?? status;
  }
  private importError(error: { error?: { detail?: unknown } }): string {
    const detail = error.error?.detail;
    if (typeof detail === 'string') return detail;
    const errors = (detail as { errors?: { row: number; error: string }[] } | undefined)?.errors;
    return errors?.map((item) => `Fila ${item.row}: ${item.error}`).join('; ') || 'Importación revertida. Revisa nuevamente las notas y las diferencias.';
  }
  protected reviewGrades(): void {
    if (this.busy() || !this.preview() || !this.courseId || !this.periodId) return;
    this.invalidateReview(); const signature = this.reviewSignature(); this.busy.set(true);
    this.api.reviewGradeRows(this.preview()!.rows, this.courseId, this.periodId, this.academicContext()).subscribe({
      next: (result) => { this.busy.set(false); if (signature !== this.reviewSignature()) return; this.review.set(result); this.reviewedSignature = signature; this.message.set('Revisión completada; todavía no se guardaron cambios.'); },
      error: (error) => { this.busy.set(false); this.message.set(this.importError(error)); },
    });
  }
  protected importStudents(): void {
    if (!this.preview() || !this.gradeId || !this.sectionId) { this.message.set('Selecciona grado y sección, y carga una vista previa válida.'); return; }
    this.api.commitStudentRows(this.preview()!.rows, this.gradeId, this.sectionId).subscribe({ next: (result) => this.message.set(`${result.imported} de ${result.processed} estudiantes importados; ${result.rejected} rechazados.`), error: (error: { error?: { detail?: unknown } }) => this.message.set(typeof error.error?.detail === 'string' ? error.error.detail : 'Importación revertida: corrige duplicados o datos inválidos.') });
  }
  protected courseName(): string { return this.catalog().courses.find((course) => course.id === this.courseId)?.name ?? 'No seleccionado'; }
  protected periodName(): string { return this.catalog().periods.find((period) => period.id === this.periodId)?.name ?? 'No seleccionado'; }
  private previewFile(file: File): void {
    if (this.busy()) return;
    this.invalidateReview();
    this.selectedFile = file; this.fileName.set(file.name); this.message.set('');
    if (this.mode() === 'grades' && !this.periodId) { this.preview.set(null); this.message.set('Selecciona el periodo antes de cargar el Excel de calificaciones.'); return; }
    const request = this.mode() === 'grades' ? this.api.previewGradeImport(file, this.periodId) : this.api.previewStudentImport(file);
    this.busy.set(true);
    request.subscribe({ next: (result) => { this.busy.set(false); this.preview.set(result); this.contextChanged(); }, error: () => { this.busy.set(false); this.preview.set({ columns: [], rows: [], total: 0, errors: [{ row: 0, error: 'No se pudo procesar el archivo; revisa la hoja y los encabezados' }] }); } });
  }
}
