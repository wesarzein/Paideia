import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AcademicCatalog, ApiService, ImportPreview } from '../../core/services/api.service';
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
        <label>Curso<select [(ngModel)]="courseId"><option value="">Seleccionar curso</option>@for (course of catalog().courses; track course.id) {<option [value]="course.id">{{ course.name }}</option>}</select></label>
        <label>Periodo<select [(ngModel)]="periodId"><option value="">Seleccionar periodo</option>@for (period of catalog().periods; track period.id) {<option [value]="period.id">{{ period.name }}</option>}</select></label>
      </section>
    } @else {
      <section class="panel filters">
        <label>Nivel<select [(ngModel)]="level" (ngModelChange)="gradeId = ''; sectionId = ''; loadCatalog()"><option value="">Seleccionar nivel</option>@for (item of levels(); track item) {<option [value]="item">{{ item }}</option>}</select></label>
        <label>Grado<select [(ngModel)]="gradeId" (ngModelChange)="sectionId = ''; loadCatalog()" [disabled]="!level"><option value="">Seleccionar grado</option>@for (grade of gradesForLevel(); track grade.id) {<option [value]="grade.id">{{ grade.name }}</option>}</select></label>
        <label>Sección<select [(ngModel)]="sectionId" (ngModelChange)="loadCatalog()" [disabled]="!gradeId"><option value="">Seleccionar sección</option>@for (section of sectionsForGrade(); track section.id) {<option [value]="section.id">{{ gradeName(section.grade_id) }} · {{ section.name }}</option>}</select></label>
      </section>
    }
    @if (mode() === 'grades') { <p class="format-hint">Las calificaciones se registran por mes. Cada dos meses conforman un bimestre. Evidencias permitidas: Actitud ante el área, Cuaderno, Módulo, Exposición-Trabajos y Evaluación.</p> }
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
        @if (rowErrors().length) { <p class="error">{{ rowErrors().length }} filas tienen errores; edita las celdas antes de confirmar.</p> }
        @if (!rowErrors().length && mode() === 'students') { <p>El código del archivo se usa como referencia; Paideia genera el código institucional según el grado, sección y orden de importación.</p><button type="button" (click)="importStudents()" [disabled]="!gradeId || !sectionId">Confirmar e importar padrón</button> }
        @if (!rowErrors().length && mode() === 'grades') { <button type="button" (click)="importGrades()" [disabled]="!courseId || !periodId">Confirmar e importar calificaciones</button> }
        <table><thead><tr>@for (column of preview()!.columns; track column) { <th>{{ column }}</th> }</tr></thead><tbody>@for (row of preview()!.rows; track $index) { <tr>@for (column of preview()!.columns; track column) { <td><input [type]="column === 'assessment_date' ? 'date' : 'text'" [(ngModel)]="$any(row)[column]" [name]="'import-' + $index + '-' + column" /></td> }</tr> }</tbody></table>
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
  protected level = '';
  protected gradeId = '';
  protected sectionId = '';
  protected courseId = '';
  protected periodId = '';
  private selectedFile: File | null = null;

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
      if (this.mode() === 'grades') { const score = Number(row['score']); if (!String(row['student_code'] ?? '').trim()) errors.push(`Fila ${index + 2}: falta código`); if (!Number.isFinite(score) || score < 0 || score > 20) errors.push(`Fila ${index + 2}: nota debe estar entre 0 y 20`); if (!String(row['assessment_date'] ?? '').trim()) errors.push(`Fila ${index + 2}: asigna una fecha de evaluación`); }
      return errors;
    });
    return [...rowErrors, ...(this.preview()?.errors ?? []).map((error) => `Fila ${error.row}: ${error.error}`)];
  }

  protected setMode(mode: 'students' | 'grades'): void { this.mode.set(mode); this.preview.set(null); this.message.set(''); this.selectedFile = null; this.fileName.set(''); }
  protected select(event: Event): void { const file = (event.target as HTMLInputElement).files?.[0]; if (file) this.previewFile(file); }
  protected drop(event: DragEvent): void { event.preventDefault(); const file = event.dataTransfer?.files[0]; if (file) this.previewFile(file); }
  protected importGrades(): void {
    if (!this.preview() || !this.courseId || !this.periodId) { this.message.set('Selecciona curso y periodo y carga una vista previa válida.'); return; }
    this.api.commitGradeRows(this.preview()!.rows, this.courseId, this.periodId).subscribe({ next: (result) => this.message.set(`${result.imported} de ${result.processed} calificaciones importadas; ${result.rejected} rechazadas.`), error: (error: { error?: { detail?: unknown } }) => this.message.set(typeof error.error?.detail === 'string' ? error.error.detail : 'Importación revertida: corrige los errores indicados por la API.') });
  }
  protected importStudents(): void {
    if (!this.preview() || !this.gradeId || !this.sectionId) { this.message.set('Selecciona grado y sección, y carga una vista previa válida.'); return; }
    this.api.commitStudentRows(this.preview()!.rows, this.gradeId, this.sectionId).subscribe({ next: (result) => this.message.set(`${result.imported} de ${result.processed} estudiantes importados; ${result.rejected} rechazados.`), error: (error: { error?: { detail?: unknown } }) => this.message.set(typeof error.error?.detail === 'string' ? error.error.detail : 'Importación revertida: corrige duplicados o datos inválidos.') });
  }
  protected courseName(): string { return this.catalog().courses.find((course) => course.id === this.courseId)?.name ?? 'No seleccionado'; }
  protected periodName(): string { return this.catalog().periods.find((period) => period.id === this.periodId)?.name ?? 'No seleccionado'; }
  private previewFile(file: File): void {
    this.selectedFile = file; this.fileName.set(file.name); this.message.set('');
    if (this.mode() === 'grades' && !this.periodId) { this.preview.set(null); this.message.set('Selecciona el periodo antes de cargar el Excel de calificaciones.'); return; }
    const request = this.mode() === 'grades' ? this.api.previewGradeImport(file, this.periodId) : this.api.previewStudentImport(file);
    request.subscribe({ next: (result) => this.preview.set(result), error: () => this.preview.set({ columns: [], rows: [], total: 0, errors: [{ row: 0, error: 'No se pudo procesar el archivo' }] }) });
  }
}
