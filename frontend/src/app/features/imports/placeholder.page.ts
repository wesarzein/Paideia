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
        <label>Curso<select [(ngModel)]="courseId"><option value="">Seleccionar curso</option>@for (course of catalog().courses; track course.id) {<option [value]="course.id">{{ course.code }} · {{ course.name }}</option>}</select></label>
        <label>Periodo<select [(ngModel)]="periodId"><option value="">Seleccionar periodo</option>@for (period of catalog().periods; track period.id) {<option [value]="period.id">{{ period.name }}</option>}</select></label>
      </section>
    }
    <section class="dropzone" (dragover)="$event.preventDefault()" (drop)="drop($event)">
      <img src="assets/logo.png" alt="" /><strong>Arrastra tu archivo aquí</strong><span>o selecciónalo desde tu equipo</span>
      <input type="file" accept=".csv,.xlsx,.xls" (change)="select($event)" />
      @if (fileName()) { <small>{{ fileName() }}</small> }
    </section>
    @if (message()) { <p class="message">{{ message() }}</p> }
    @if (preview()) {
      <section class="panel preview">
        <h2>Vista previa: {{ preview()!.total }} filas</h2>
        @if (mode() === 'grades') { <p class="context"><strong>Curso:</strong> {{ courseName() }} · <strong>Periodo:</strong> {{ periodName() }}</p> }
        @if (preview()!.errors.length) { <p class="error">{{ preview()!.errors.length }} errores encontrados. Corrige el archivo antes de continuar.</p> }
        @if (!preview()!.errors.length && mode() === 'students') { <button type="button" (click)="importStudents()">Confirmar y guardar estudiantes</button> }
        @if (!preview()!.errors.length && mode() === 'grades') { <button type="button" (click)="importGrades()">Confirmar y guardar calificaciones</button> }
        <table><thead><tr>@for (column of preview()!.columns; track column) { <th>{{ column }}</th> }</tr></thead><tbody>@for (row of preview()!.rows; track $index) { <tr>@for (column of preview()!.columns; track column) { <td>{{ row[column] }}</td> }</tr> }</tbody></table>
      </section>
    }
  `,
  styles: [`
    .panel, .dropzone { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: 22px; margin-bottom: 18px; }
    .modes { display: flex; gap: 10px; } .modes button, button { background: var(--color-primary); color: white; border: 0; border-radius: 6px; padding: 11px 16px; cursor: pointer; } .modes button:not(.active) { background: transparent; color: var(--color-primary); border: 1px solid var(--color-primary); }
    .filters { display: grid; grid-template-columns: repeat(2, minmax(180px, 1fr)); gap: 14px; } label { display: grid; gap: 7px; color: var(--color-muted-text); } select { border: 1px solid var(--color-border); border-radius: 6px; padding: 10px; font: inherit; }
    .dropzone { display: grid; justify-items: center; gap: 8px; border: 2px dashed var(--color-accent); } .dropzone img { width: 55px; height: 55px; object-fit: contain; } .dropzone span, small { color: var(--color-muted-text); } input { margin-top: 10px; } .preview { overflow-x: auto; } table { width: 100%; border-collapse: collapse; } th, td { padding: 10px; border-bottom: 1px solid var(--color-border); text-align: left; white-space: nowrap; } .context { color: var(--color-primary); } .error { color: #a33a32; } .message { color: var(--color-primary); } @media(max-width:700px){ .filters { grid-template-columns: 1fr; } }
  `],
})
export class PlaceholderPage {
  private readonly api = inject(ApiService);
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [] });
  protected readonly mode = signal<'students' | 'grades'>('students');
  protected readonly preview = signal<ImportPreview | null>(null);
  protected readonly fileName = signal('');
  protected readonly message = signal('');
  protected courseId = '';
  protected periodId = '';
  private selectedFile: File | null = null;

  constructor() { this.api.getAcademicCatalog().subscribe({ next: (catalog) => this.catalog.set(catalog) }); }

  protected setMode(mode: 'students' | 'grades'): void { this.mode.set(mode); this.preview.set(null); this.message.set(''); this.selectedFile = null; this.fileName.set(''); }
  protected select(event: Event): void { const file = (event.target as HTMLInputElement).files?.[0]; if (file) this.previewFile(file); }
  protected drop(event: DragEvent): void { event.preventDefault(); const file = event.dataTransfer?.files[0]; if (file) this.previewFile(file); }
  protected importGrades(): void {
    if (!this.selectedFile || !this.courseId || !this.periodId) { this.message.set('Selecciona curso y periodo antes de guardar.'); return; }
    this.api.importGrades(this.selectedFile, this.courseId, this.periodId).subscribe({ next: (result) => this.message.set(`${result.imported} calificaciones importadas correctamente.`), error: () => this.message.set('No se pudo importar el archivo.') });
  }
  protected importStudents(): void {
    if (!this.selectedFile) { this.message.set('Selecciona un archivo antes de guardar.'); return; }
    this.api.importStudents(this.selectedFile).subscribe({ next: (result) => this.message.set(`${result.imported} estudiantes importados correctamente.`), error: () => this.message.set('No se pudo importar el archivo.') });
  }
  protected courseName(): string { return this.catalog().courses.find((course) => course.id === this.courseId)?.name ?? 'No seleccionado'; }
  protected periodName(): string { return this.catalog().periods.find((period) => period.id === this.periodId)?.name ?? 'No seleccionado'; }
  private previewFile(file: File): void {
    this.selectedFile = file; this.fileName.set(file.name); this.message.set('');
    const request = this.mode() === 'grades' ? this.api.previewGradeImport(file) : this.api.previewStudentImport(file);
    request.subscribe({ next: (result) => this.preview.set(result), error: () => this.preview.set({ columns: [], rows: [], total: 0, errors: [{ row: 0, error: 'No se pudo procesar el archivo' }] }) });
  }
}
