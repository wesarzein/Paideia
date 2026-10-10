import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { concatMap, finalize, from } from 'rxjs';
import { AcademicCatalog, ApiService, AttendanceRecord } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [FormsModule, PageHeaderComponent],
  template: `
    <app-page-header title="Asistencia" description="Registra y corrige la asistencia del aula para una fecha." />
    <fieldset class="panel filters" [disabled]="saving()">
      <label>Nivel<select [(ngModel)]="level" (ngModelChange)="gradeId = ''; sectionId = ''; courseId = ''; loadCatalog()"><option value="">Seleccionar nivel</option>@for (item of levels(); track item) {<option [value]="item">{{ item }}</option>}</select></label>
      <label>Grado<select [(ngModel)]="gradeId" (ngModelChange)="sectionId = ''; courseId = ''; loadCatalog()" [disabled]="!level"><option value="">Seleccionar grado</option>@for (grade of gradesForLevel(); track grade.id) {<option [value]="grade.id">{{ grade.name }}</option>}</select></label>
      <label>Sección<select [(ngModel)]="sectionId" (ngModelChange)="courseId = ''; loadCatalog()" [disabled]="!gradeId"><option value="">Seleccionar sección</option>@for (section of sectionsForGrade(); track section.id) {<option [value]="section.id">{{ gradeName(section.grade_id) }} · {{ section.name }}</option>}</select></label>
      <label>Curso<select [(ngModel)]="courseId" (ngModelChange)="loadRecords()" [disabled]="!sectionId || catalogLoading()"><option value="">Seleccionar curso</option>@for (course of catalog().courses; track course.id) {<option [value]="course.id">{{ course.name }}</option>}</select></label>
      <label>Periodo<select [(ngModel)]="periodId" (ngModelChange)="loadRecords()" [disabled]="!sectionId"><option value="">Seleccionar periodo</option>@for (period of catalog().periods; track period.id) {<option [value]="period.id">{{ period.name }}</option>}</select></label>
      <label>Fecha<input type="date" [(ngModel)]="attendanceDate" (ngModelChange)="loadRecords()" /></label>
    </fieldset>
    @if (catalogLoading() || loading()) { <p role="status">Cargando asistencia…</p> }
    @if (loadError()) { <p class="panel error" role="alert">{{ loadError() }} <button type="button" (click)="loadCatalog()" [disabled]="saving()">Reintentar carga</button></p> }
    @if (!sectionId || !courseId || !periodId || !attendanceDate) {
      <p class="panel">Selecciona grado, sección, curso, periodo y fecha para cargar la lista del aula.</p>
    } @else {
      <section class="summary"><span>Presentes: {{ count('PRESENT') }}</span><span>Faltas: {{ count('ABSENT') }}</span><span>Tardanzas: {{ count('LATE') }}</span></section>
      <section class="panel">
        @if (!canWrite) { <p>Consulta de asistencia. El registro corresponde al docente asignado o al administrador.</p> }
        @if (canWrite) { <div class="quick"><button type="button" (click)="markAll('PRESENT')" [disabled]="busy()">Todos presentes</button><button type="button" class="outline" (click)="markAll('ABSENT')" [disabled]="busy()">Todos ausentes</button></div> }
        <div class="table-scroll"><table><thead><tr><th>Estudiante</th><th>Estado</th></tr></thead><tbody>
          @for (student of catalog().students; track student.id) { <tr><td>{{ student.name }}</td><td><select [attr.aria-label]="'Asistencia de ' + student.name" [(ngModel)]="status[student.id]" [disabled]="!canWrite || busy()"><option value="" disabled>Sin registro</option><option value="PRESENT">Presente</option><option value="ABSENT">Falta</option><option value="LATE">Tardanza</option></select></td></tr> }
          @empty { <tr><td colspan="2">No hay estudiantes disponibles para esta sección.</td></tr> }
        </tbody></table></div>
        @if (canWrite) { <button type="button" (click)="saveAll()" [disabled]="busy() || !catalog().students.length">{{ saving() ? 'Guardando…' : 'Guardar asistencia del día' }}</button> }
        @if (error()) { <p class="error" role="alert">{{ error() }}</p> }
        @if (message()) { <p role="status">{{ message() }}</p> }
      </section>
    }
  `,
  styles: [`
    .panel { background:var(--color-surface); border:1px solid var(--color-border); border-radius:8px; padding:22px; margin:0 0 18px; min-width:0; }
    .filters { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }
    label { display:grid; gap:7px; color:var(--color-muted-text); }
    input,select { border:1px solid var(--color-border); border-radius:6px; padding:10px; font:inherit; min-width:0; }
    .table-scroll { overflow-x:auto; } table { width:100%; border-collapse:collapse; }
    th,td { padding:11px; border-bottom:1px solid var(--color-border); text-align:left; }
    button { margin:16px 10px 0 0; background:var(--color-primary); color:white; border:0; border-radius:6px; padding:11px 16px; cursor:pointer; }
    button.outline { background:var(--color-surface); color:var(--color-primary); border:1px solid var(--color-primary); }
    button:disabled { opacity:.6; cursor:default; } .error { color:var(--color-danger,#b42318); }
    .summary { display:flex; gap:12px; margin-bottom:14px; flex-wrap:wrap; }
    .summary span { background:var(--color-surface); border:1px solid var(--color-border); border-radius:6px; padding:10px 14px; }
    @media(max-width:700px) { .filters { grid-template-columns:1fr; } }
  `],
})
export class AttendancePage {
  private readonly api = inject(ApiService);
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] });
  protected readonly records = signal<AttendanceRecord[]>([]);
  protected readonly message = signal('');
  protected readonly error = signal('');
  protected readonly loadError = signal('');
  protected readonly saving = signal(false);
  protected readonly loading = signal(false);
  protected readonly catalogLoading = signal(false);
  protected readonly canWrite = (() => {
    try { return ['admin', 'teacher'].includes(JSON.parse(localStorage.getItem('paideia_user') ?? '{}').role); }
    catch { return false; }
  })();
  protected level = '';
  protected gradeId = '';
  protected sectionId = '';
  protected courseId = '';
  protected periodId = '';
  protected attendanceDate = new Date().toISOString().slice(0, 10);
  protected status: Record<string, string> = {};
  private contextKey = '';
  private persistedStatus: Record<string, string> = {};
  private catalogRequest = 0;
  private recordsRequest = 0;

  constructor() { this.loadCatalog(); }
  protected levels(): string[] { return [...new Set(this.catalog().grades.map((item) => item.level))]; }
  protected gradesForLevel() { return this.catalog().grades.filter((item) => item.level === this.level); }
  protected sectionsForGrade() { return this.catalog().sections.filter((item) => item.grade_id === this.gradeId); }
  protected gradeName(id: string) { return this.catalog().grades.find((item) => item.id === id)?.name ?? ''; }
  protected busy() { return this.loading() || this.catalogLoading() || this.saving() || !!this.loadError(); }
  private context() { return { grade_id: this.gradeId, section_id: this.sectionId, course_id: this.courseId, period_id: this.periodId, attendance_date: this.attendanceDate }; }
  protected loadCatalog(): void {
    const request = ++this.catalogRequest;
    ++this.recordsRequest;
    this.loading.set(false);
    this.catalogLoading.set(true);
    this.loadError.set('');
    const filters: Record<string, string> = {};
    if (this.gradeId) filters['grade_id'] = this.gradeId;
    if (this.sectionId) filters['section_id'] = this.sectionId;
    this.api.getAcademicCatalog(filters).subscribe({
      next: (catalog) => {
        if (request !== this.catalogRequest) return;
        this.catalog.set(catalog);
        this.catalogLoading.set(false);
        this.loadRecords();
      },
      error: () => {
        if (request !== this.catalogRequest) return;
        this.catalogLoading.set(false);
        this.loadError.set('No se pudo cargar el aula. Reintenta antes de guardar.');
      },
    });
  }
  protected loadRecords(): void {
    const context = this.context();
    const key = JSON.stringify(context);
    const request = ++this.recordsRequest;
    const changed = key !== this.contextKey;
    const edits = changed ? {} : Object.fromEntries(Object.entries(this.status).filter(([id, value]) => value !== this.persistedStatus[id]));
    if (changed) {
      this.contextKey = key;
      this.records.set([]);
      this.status = {};
      this.persistedStatus = {};
      this.message.set('');
      this.error.set('');
    }
    this.loading.set(false);
    if (this.catalogLoading() || !this.sectionId || !this.courseId || !this.periodId || !this.attendanceDate) return;
    this.loadError.set('');
    this.loading.set(true);
    this.api.listAttendance(context).subscribe({
      next: (records) => {
        if (request !== this.recordsRequest || key !== JSON.stringify(this.context())) return;
        this.records.set(records);
        const saved = new Map(records.map((record) => [record.student_id, record.status]));
        this.persistedStatus = Object.fromEntries(this.catalog().students.map((student) => [student.id, saved.get(student.id) ?? (this.canWrite ? 'PRESENT' : '')]));
        this.status = { ...this.persistedStatus, ...edits };
        this.loading.set(false);
      },
      error: () => {
        if (request !== this.recordsRequest || key !== JSON.stringify(this.context())) return;
        this.loading.set(false);
        this.loadError.set('No se pudo consultar la asistencia de esta fecha. Reintenta antes de guardar.');
      },
    });
  }
  protected count(value: string): number { return this.catalog().students.filter((student) => this.status[student.id] === value).length; }
  protected markAll(value: string): void {
    if (!this.canWrite || this.busy()) return;
    this.catalog().students.forEach((student) => this.status[student.id] = value);
  }
  protected saveAll(): void {
    if (!this.canWrite || this.busy()) return;
    if (!this.sectionId || !this.courseId || !this.periodId || !this.attendanceDate || !this.catalog().students.length) {
      this.error.set('Selecciona sección, curso, periodo y fecha con alumnos disponibles.');
      return;
    }
    const context = this.context();
    const entries = this.catalog().students.map((student) => ({ student_id: student.id, course_id: context.course_id, period_id: context.period_id, attendance_date: context.attendance_date, status: this.status[student.id] ?? 'PRESENT' }));
    let saved = 0;
    this.error.set(''); this.message.set(''); this.saving.set(true);
    from(entries).pipe(concatMap((entry) => this.api.createAttendance(entry)), finalize(() => this.saving.set(false))).subscribe({
      next: (record) => {
        saved++;
        this.persistedStatus[record.student_id] = record.status;
        this.message.set(`${saved} de ${entries.length} asistencias guardadas.`);
      },
      error: (failure) => {
        const detail = failure.error?.detail;
        this.error.set(`${typeof detail === 'string' ? detail : 'No se pudo guardar la asistencia.'} ${saved} de ${entries.length} guardadas; puedes reintentar sin duplicar registros.`);
      },
      complete: () => this.loadRecords(),
    });
  }
}
