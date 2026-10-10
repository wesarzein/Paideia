import { Component, ElementRef, ViewChild, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AcademicCatalog, ApiService, GradeImportReview, ImportPreview, InstitutionalContext } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [FormsModule, PageHeaderComponent],
  templateUrl: './imports.page.html',
  styleUrl: './imports.page.css',
})
export class PlaceholderPage {
  @ViewChild('confirmation') set confirmation(element: ElementRef<HTMLDialogElement> | undefined) {
    if (element && !element.nativeElement.open) element.nativeElement.showModal();
  }
  private readonly api = inject(ApiService);
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] });
  protected readonly mode = signal<'students' | 'grades'>('grades');
  protected readonly preview = signal<ImportPreview | null>(null);
  protected readonly fileName = signal('');
  protected readonly message = signal('');
  protected readonly noticeKind = signal<'info' | 'success' | 'error'>('info');
  protected readonly contextLocked = signal(false);
  protected readonly confirmOpen = signal(false);
  protected readonly review = signal<GradeImportReview | null>(null);
  protected readonly busy = signal(false);
  protected readonly isAdmin = (() => { try { return JSON.parse(localStorage.getItem('paideia_user') ?? '{}').role === 'admin'; } catch { return false; } })();
  private reviewedSignature = '';
  protected level = '';
  protected gradeId = '';
  protected sectionId = '';
  protected courseId = '';
  protected periodId = '';
  protected schoolYear: number | null = new Date().getFullYear();
  protected bimestre: number | null = null;
  protected contextConfirmed = false;
  protected correctionsOnly = false;
  protected blocks: Record<string, { evaluation_name: string; assessment_date: string }> = { '1': { evaluation_name: '', assessment_date: '' }, '2': { evaluation_name: '', assessment_date: '' } };
  private selectedFile: File | null = null;

  protected notify(text: string, kind: 'info' | 'success' | 'error' = 'info'): void {
    this.noticeKind.set(kind); this.message.set(text);
  }
  protected sectionName(): string { return this.catalog().sections.find(item => item.id === this.sectionId)?.name ?? ''; }
  protected selectPeriod(): void {
    const period = this.catalog().periods.find(item => item.id === this.periodId);
    if (period?.starts_on) this.schoolYear = Number(period.starts_on.slice(0, 4));
  }
  protected visibleColumns(): string[] {
    return this.preview()?.columns.filter(column => this.mode() === 'students'
      ? ['student_code', 'full_name', 'first_name', 'last_name'].includes(column)
      : ['student_code', 'score', 'evaluation_type', 'qualitative_note'].includes(column)) ?? [];
  }
  protected columnLabel(column: string): string {
    return ({ student_code: 'Código', full_name: 'Nombre del archivo', first_name: 'Nombres', last_name: 'Apellidos', score: 'Nota', evaluation_type: 'Criterio', evaluation_name: 'Evaluación', assessment_date: 'Fecha', qualitative_note: 'Observación' } as Record<string, string>)[column] ?? column;
  }
  protected invalidScore(score: unknown): boolean {
    return score !== null && score !== undefined && score !== '' && (!Number.isFinite(Number(score)) || Number(score) < 0 || Number(score) > 20);
  }
  private setupErrors(): string[] {
    const errors: string[] = [];
    if (!this.gradeId || !this.sectionId) errors.push('Selecciona nivel, grado y sección.');
    if (this.mode() === 'grades') {
      if (!this.courseId || !this.periodId) errors.push('Selecciona curso y periodo.');
      if (!Number.isInteger(this.schoolYear) || Number(this.schoolYear) < 2000 || Number(this.schoolYear) > 2100) errors.push('Ingresa un año escolar válido.');
      if (![1, 2, 3, 4].includes(Number(this.bimestre))) errors.push('Selecciona el bimestre.');

    }
    return errors;
  }
  protected lockContext(): void {
    if (this.busy()) return;
    const errors = this.setupErrors();
    if (errors.length) { this.notify(errors.join(' '), 'error'); return; }
    this.contextLocked.set(true); this.contextConfirmed = true; this.message.set(''); this.loadCatalog();
  }
  protected changeSelection(): void {
    if (this.busy()) return;
    this.replaceFile(); this.contextLocked.set(false); this.contextConfirmed = false;
  }
  protected replaceFile(): void {
    if (this.busy()) return;
    this.preview.set(null); this.invalidateReview(); this.confirmOpen.set(false); this.message.set(''); this.fileName.set(''); this.selectedFile = null;
  }
  protected prepareGradeSave(): void {
    if (this.busy()) return;
    if (!this.preview()?.total) { this.notify('El archivo no contiene notas para guardar.', 'error'); return; }
    const errors = [...this.setupErrors(), ...this.rowErrors()];
    if (errors.length) { this.notify([...new Set(errors)].slice(0, 5).join(' '), 'error'); return; }
    this.reviewGrades(true);
  }
  protected prepareStudentSave(): void {
    if (this.busy()) return;
    if (!this.preview()?.total || this.rowErrors().length || !this.gradeId || !this.sectionId) { this.notify('Revisa los nombres y apellidos antes de guardar alumnos.', 'error'); return; }
    this.confirmOpen.set(true);
  }
  protected confirmationSummary(): string {
    if (this.mode() === 'students') return `Se procesarán ${this.preview()?.total ?? 0} alumnos. Los códigos existentes actualizarán sus nombres.`;
    const rows = this.review()?.rows ?? [];
    const changed = rows.filter(item => item.status === 'different').length;
    const fresh = rows.filter(item => item.status === 'new').length;
    const unchanged = rows.filter(item => item.status === 'identical' || item.status === 'duplicate_in_file').length;
    return `${changed} notas se actualizarán; ${this.correctionsOnly ? 0 : fresh} se crearán; ${unchanged + (this.correctionsOnly ? fresh : 0)} se conservarán u omitirán.`;
  }
  protected confirmSave(): void {
    if (this.busy()) return;
    this.confirmOpen.set(false);
    if (this.mode() === 'grades') this.importGrades(); else this.importStudents();
  }

  protected matrixStudents() { return this.preview()?.institutional?.students ?? []; }
  protected matrixCell(sourceRow: number, block: string, criterion: string) {
    return this.preview()?.rows.find(row => row['source_row'] === sourceRow && row['source_block'] === block && row['evaluation_type'] === criterion);
  }
  protected studentCode(sourceRow: number): string {
    return String(this.preview()?.rows.find(row => row['source_row'] === sourceRow)?.['student_code'] ?? this.matrixStudents().find(student => student.source_row === sourceRow)?.student_code ?? '');
  }
  protected studentConfirmed(sourceRow: number): boolean {
    const rows = this.preview()?.rows.filter(row => row['source_row'] === sourceRow) ?? [];
    return !!rows.length && rows.every(row => row['student_confirmed'] === true);
  }
  protected confirmMatrixStudent(sourceRow: number, confirmed: boolean): void {
    for (const row of this.preview()?.rows ?? []) if (row['source_row'] === sourceRow) row['student_confirmed'] = confirmed;
    this.invalidateReview();
  }
  protected resolveMatrixStudent(sourceRow: number, code: string): void {
    const student = this.matrixStudents().find(item => item.source_row === sourceRow);
    if (student) student.student_code = code;
    for (const row of this.preview()?.rows ?? []) if (row['source_row'] === sourceRow) row['student_code'] = code;
    this.confirmMatrixStudent(sourceRow, true);
  }
  protected editMatrixScore(sourceRow: number, block: string, criterion: string, score: number | null): void {
    const preview = this.preview(); if (!preview) return;
    const cell = this.matrixCell(sourceRow, block, criterion);
    if (score === null || String(score) === '') {
      preview.rows = preview.rows.filter(row => row !== cell);
    } else if (cell) cell['score'] = score;
    else {
      const student = this.matrixStudents().find(item => item.source_row === sourceRow)!;
      preview.rows.push({ student_code: this.studentCode(sourceRow), student_confirmed: this.studentConfirmed(sourceRow),
        source_name: student.name, source_row: sourceRow, source_sheet: preview.institutional!.sheet,
        template: preview.institutional!.template, reference_verified: !preview.institutional!.unsupported_formula_rows.includes(sourceRow),
        source_block: block, evaluation_type: criterion, score, qualitative_note: '', ...this.blocks[block] });
    }
    preview.total = preview.rows.length;
    this.invalidateReview();
  }
  protected cellReview(sourceRow: number, block: string, criterion: string) {
    const cell = this.matrixCell(sourceRow, block, criterion);
    const index = cell ? this.preview()!.rows.indexOf(cell) : -1;
    return this.review()?.rows.find(item => item.row === index + 1);
  }

  protected contextChanged(): void {
    this.contextConfirmed = this.contextLocked();
    const preview = this.preview();
    if (preview?.institutional) {
      for (const row of preview.rows) {
        const block = this.blocks[String(row['source_block'])];
        if (block) { row['evaluation_name'] = `Registro histórico - Bimestre ${this.bimestre} - Bloque ${row['source_block']}`; row['assessment_date'] = null; }
      }
    } else if (preview && this.mode() === 'grades') {
      for (const row of preview.rows) {
        row['assessment_date'] = null;
        row['evaluation_name'] = `Registro histórico - Bimestre ${this.bimestre} - Bloque ${row['evaluation_block'] || 1}`;
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
    return this.mode() === 'grades' ? { historical: true, school_year: this.schoolYear, bimestre: this.bimestre, grade_id: this.gradeId, section_id: this.sectionId, confirmed: this.contextConfirmed, blocks: this.blocks } : undefined;
  }

  constructor() { if (!this.isAdmin) this.mode.set('grades'); this.loadCatalog(); }

  protected levels(): string[] { return [...new Set(this.catalog().grades.map((item) => item.level))]; }
  protected gradesForLevel() { return this.catalog().grades.filter((item) => item.level === this.level); }
  protected sectionsForGrade() { return this.catalog().sections.filter((item) => item.grade_id === this.gradeId); }
  protected gradeName(id: string) { return this.catalog().grades.find((item) => item.id === id)?.name ?? ''; }
  protected loadCatalog(): void { const filters: Record<string, string> = {}; if (this.gradeId) filters['grade_id'] = this.gradeId; if (this.sectionId) filters['section_id'] = this.sectionId; this.api.getAcademicCatalog(filters).subscribe({ next: (catalog) => { this.catalog.set(catalog); this.fillStudentNames(); }, error: () => this.notify('No se pudo cargar el catálogo. Vuelve a seleccionar el grupo o recarga la página.', 'error') }); }
  private fillStudentNames(): void {
    if (this.mode() !== 'students') return;
    const normalize = (value: unknown) => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]/gi, '').toLowerCase();
    for (const row of this.preview()?.rows ?? []) {
      if (row['first_name'] || row['last_name']) continue;
      const saved = this.catalog().students.find(item => item.student_code === row['student_code']);
      if (!saved || normalize(saved.name) !== normalize(row['full_name'])) continue;
      const parts = saved.name.split(',');
      if (parts.length === 2) { row['last_name'] = parts[0].trim(); row['first_name'] = parts[1].trim(); }
    }
  }
  protected rowErrors(): string[] {
    const rows = this.preview()?.rows ?? [];
    const rowErrors = rows.flatMap((row, index) => {
      const errors: string[] = [];
      if (this.mode() === 'students' && (!String(row['student_code'] ?? '').trim() || !String(row['first_name'] ?? '').trim() || !String(row['last_name'] ?? '').trim())) errors.push(`Fila ${index + 2}: código, nombres y apellidos son obligatorios`);
      if (this.mode() === 'grades') { const score = Number(row['score']); if (!String(row['student_code'] ?? '').trim()) errors.push(`Fila ${index + 2}: falta código`); if (!String(row['score'] ?? '').trim() || !Number.isFinite(score) || score < 0 || score > 20) errors.push(`Fila ${index + 2}: nota debe estar entre 0 y 20`); }
      return errors;
    });
    if (this.preview()?.institutional && this.mode() === 'grades') {
      const invalidScores = rows.filter(row => !String(row['score'] ?? '').trim() || !Number.isFinite(Number(row['score'])) || Number(row['score']) < 0 || Number(row['score']) > 20);
      return [...invalidScores.map(row => `Fila Excel ${row['source_row']} · bloque ${row['source_block']} · ${row['evaluation_type']}: nota entre 0 y 20`)];
    }
    return [...rowErrors, ...(this.preview()?.errors ?? []).map((error) => `Fila ${error.row}: ${error.error}`)];
  }

  protected setMode(mode: 'students' | 'grades'): void { if (this.busy() || (mode === 'students' && !this.isAdmin) || mode === this.mode()) return; this.replaceFile(); this.mode.set(mode); this.contextLocked.set(false); this.contextConfirmed = false; }
  protected select(event: Event): void { const file = (event.target as HTMLInputElement).files?.[0]; if (file) this.previewFile(file); }
  protected drop(event: DragEvent): void { event.preventDefault(); const file = event.dataTransfer?.files[0]; if (file) this.previewFile(file); }
  protected importGrades(): void {
    if (this.busy()) return;
    if (!this.reviewReady()) { this.notify('Las notas cambiaron después de la revisión. Pulsa Guardar calificaciones para revisarlas de nuevo.', 'error'); return; }
    const rows = this.preview()!.rows.map((row, index) => {
      const item = this.review()!.rows.find(item => item.row === index + 1)!;
      return { ...row, component_id: item.component_id, decision: item.decision, review_token: item.review_token };
    });
    this.busy.set(true);
    this.api.commitGradeRows(rows, this.courseId, this.periodId, this.academicContext(), this.correctionsOnly).subscribe({
      next: (result) => { this.busy.set(false); this.invalidateReview(); this.notify(`${result.imported} notas nuevas; ${result.updated} actualizadas; ${result.skipped} sin cambios u omitidas; ${result.rejected} rechazadas.${this.correctionsOnly && !result.imported && !result.updated && result.skipped ? ' Elegiste solo correcciones: las notas nuevas no se cargan. Para una carga inicial cambia esa opción antes de seleccionar el archivo.' : ''}`, result.rejected ? 'error' : 'success'); },
      error: (error) => { this.busy.set(false); this.invalidateReview(); this.notify('No se guardaron cambios. ' + this.importError(error), 'error'); },
    });
  }

  protected invalidateReview(): void {
    this.message.set('');
    this.confirmOpen.set(false);
    this.review.set(null); this.reviewedSignature = '';
    if (this.mode() === 'grades' && this.preview()) this.preview.set({ ...this.preview()!, errors: [] });
  }
  private reviewSignature(): string { return JSON.stringify([this.courseId, this.periodId, this.preview()?.rows, this.academicContext(), this.correctionsOnly]); }
  protected reviewReady(): boolean {
    return !!this.review() && this.review()!.rows.length === this.preview()?.rows.length && !this.review()!.errors.length && this.reviewedSignature === this.reviewSignature()
      && this.review()!.rows.every((item) => item.status !== 'different' || item.decision === 'keep' || item.decision === 'update');
  }
  protected statusLabel(status: string): string {
    return ({ new: 'Nueva', identical: 'Ya existe: idéntica', different: 'Diferencia', ambiguous: 'Ambigua', duplicate_in_file: 'Repetida en archivo' } as Record<string, string>)[status] ?? status;
  }
  private importError(error: { error?: { detail?: unknown } }): string {
    const detail = error.error?.detail;
    if (typeof detail === 'string') return detail;
    const missing = (detail as { missing_columns?: string[] } | undefined)?.missing_columns;
    if (missing?.length) return 'Faltan columnas: ' + missing.join(', ') + '. Usa el registro de notas institucional o una tabla con Código, Nombres y Apellidos.';
    const errors = (detail as { errors?: { row: number; error: string }[] } | undefined)?.errors;
    const messages = errors?.map(item => {
      const row = this.preview()?.institutional ? this.preview()?.rows[item.row - 1] : undefined;
      return row ? `Fila Excel ${row['source_row']} · ${row['source_name']}: ${item.error}` : `Fila ${item.row}: ${item.error}`;
    });
    const guidance = errors?.some(item => item.error.startsWith('Estudiante no encontrado')) ? (this.isAdmin ? ' Primero importa esos alumnos desde la pestaña Estudiantes, seleccionando su grado y sección.' : ' Pide al administrador que registre esos alumnos y revise tu asignación de curso, grado y sección.') : '';
    return messages?.length ? [...new Set(messages)].join('; ') + guidance : 'No se pudo completar la importación. Revisa los datos y vuelve a intentar.';
  }
  protected reviewGrades(openConfirmation = false): void {
    if (this.busy() || !this.preview() || !this.courseId || !this.periodId) return;
    this.invalidateReview(); const signature = this.reviewSignature(); this.busy.set(true);
    this.api.reviewGradeRows(this.preview()!.rows, this.courseId, this.periodId, this.academicContext()).subscribe({
      next: (result) => {
        this.busy.set(false); if (signature !== this.reviewSignature()) return;
        if (openConfirmation) for (const item of result.rows) if (item.status === 'different') item.decision = 'update';
        this.review.set(result); this.reviewedSignature = signature;
        if (result.errors.length) this.notify('No se puede guardar todavía. ' + [...new Set(result.errors.map(item => item.error))].slice(0, 5).join(' '), 'error');
        else if (openConfirmation && this.reviewReady()) { this.message.set(''); this.confirmOpen.set(true); }
        else this.notify('Revisión completada; todavía no se guardaron cambios.');
      },
      error: (error) => { this.busy.set(false); this.notify('No se guardaron cambios. ' + this.importError(error), 'error'); },
    });
  }
  protected importStudents(): void {
    if (!this.isAdmin) return;
    if (this.busy() || this.rowErrors().length || !this.preview() || !this.gradeId || !this.sectionId) { this.notify('Selecciona grado y sección, y carga una vista previa válida.', 'error'); return; }
    this.busy.set(true);
    this.api.commitStudentRows(this.preview()!.rows, this.gradeId, this.sectionId).subscribe({ next: (result) => { this.busy.set(false); this.loadCatalog(); this.notify(`${result.imported} nuevos; ${result.updated} actualizados; ${result.skipped} sin cambios; ${result.rejected} rechazados. Ya puedes cargar este mismo Excel en Calificaciones.`, result.rejected ? 'error' : 'success'); }, error: (error) => { this.busy.set(false); this.notify('No se guardaron cambios. ' + this.importError(error), 'error'); } });
  }
  protected courseName(): string { return this.catalog().courses.find((course) => course.id === this.courseId)?.name ?? 'No seleccionado'; }
  protected periodName(): string { return this.catalog().periods.find((period) => period.id === this.periodId)?.name ?? 'No seleccionado'; }
  private previewFile(file: File): void {
    if (this.busy()) return;
    if (!this.contextLocked()) { this.notify('Selecciona el grupo y pulsa Continuar y cargar Excel antes de elegir el archivo.', 'error'); return; }
    this.invalidateReview();
    this.selectedFile = file; this.fileName.set(file.name); this.message.set('');
    if (this.mode() === 'grades' && !this.periodId) { this.preview.set(null); this.notify('Selecciona el periodo antes de cargar el Excel de calificaciones.', 'error'); return; }
    const request = this.mode() === 'grades' ? this.api.previewGradeImport(file, this.periodId) : this.api.previewStudentImport(file);
    this.busy.set(true);
    request.subscribe({ next: (result) => { this.busy.set(false); this.preview.set(result); this.fillStudentNames(); this.contextChanged(); this.notify(`Archivo leído: ${result.total} ${this.mode() === 'grades' ? 'notas' : 'alumnos'}. Revisa la tabla y pulsa Guardar para continuar.`); }, error: (error) => { this.busy.set(false); this.preview.set(null); this.notify(this.importError(error), 'error'); } });
  }
}
