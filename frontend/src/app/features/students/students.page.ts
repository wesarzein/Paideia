import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AcademicCatalog, ApiService, Student } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { ConfirmService } from '../../core/services/confirm.service';

@Component({
  standalone: true,
  imports: [DatePipe, FormsModule, PageHeaderComponent],
  template: `
    <app-page-header title="Estudiantes" description="Registro base para el seguimiento académico institucional." />
    <section class="toolbar">
      <label>Buscar estudiante
        <input [(ngModel)]="search" (keyup.enter)="loadStudents()" placeholder="Código o nombre" />
      </label>
      <label>Grado<select [(ngModel)]="gradeId" (ngModelChange)="sectionId = ''; loadStudents()"><option value="">Todos</option>@for (grade of catalog().grades; track grade.id) {<option [value]="grade.id">{{ grade.name }} - {{ grade.level }}</option>}</select></label>
      <label>Sección<select [(ngModel)]="sectionId" (ngModelChange)="loadStudents()" [disabled]="!gradeId"><option value="">Todas</option>@for (section of sectionsForGrade(gradeId); track section.id) {<option [value]="section.id">{{ gradeName(section.grade_id) }} · {{ section.name }}</option>}</select></label>
      <label>Estado<select [(ngModel)]="statusFilter" (ngModelChange)="loadStudents()"><option value="">Todos</option><option value="ACTIVE">Activo</option><option value="INACTIVE">Inactivo</option></select></label>
      <button type="button" (click)="loadStudents()">Buscar</button>
      <button type="button" class="secondary" (click)="showForm.set(!showForm())">{{ showForm() ? 'Cerrar' : 'Nuevo estudiante' }}</button>
    </section>
    @if (showForm()) {
      <form class="form" (ngSubmit)="createStudent()">
        <h2>{{ editingId ? 'Editar estudiante' : 'Registrar estudiante' }}</h2>
        <div class="form-grid">
          <label>Código (generado por grado, sección y orden)<input name="student_code" [(ngModel)]="form.student_code" readonly /></label>
          <label>Nombres<input name="first_name" [(ngModel)]="form.first_name" required /></label>
          <label>Apellidos<input name="last_name" [(ngModel)]="form.last_name" required /></label>
          <label>Fecha de nacimiento<input name="birth_date" type="date" [(ngModel)]="form.birth_date" /></label>
          <label>Grado<select name="grade_id" [(ngModel)]="form.grade_id" (ngModelChange)="form.section_id = ''" required><option value="">Seleccionar</option>@for (grade of catalog().grades; track grade.id) { <option [value]="grade.id">{{ grade.name }} - {{ grade.level }}</option> }</select></label>
          <label>Sección<select name="section_id" [(ngModel)]="form.section_id" required><option value="">Seleccionar</option>@for (section of sectionsForGrade(form.grade_id); track section.id) { <option [value]="section.id">{{ gradeName(section.grade_id) }} · {{ section.name }}</option> }</select></label>
          <label>Estado<select name="status" [(ngModel)]="form.status"><option value="ACTIVE">Activo</option><option value="INACTIVE">Inactivo</option></select></label>
        </div>
        <button type="submit">{{ editingId ? 'Guardar cambios' : 'Guardar estudiante' }}</button>
        @if (formError()) { <p class="error">{{ formError() }}</p> }
      </form>
    }
    @if (loading()) { <p class="state">Cargando estudiantes...</p> }
    @else if (error()) { <p class="state error">No se pudo conectar con la API.</p> }
    @else if (students().length === 0) { <p class="state">No hay estudiantes registrados.</p> }
    @else {
      <div class="table-wrap">
        <table>
          <thead><tr><th>Código</th><th>Estudiante</th><th>Grado</th><th>Sección</th><th>Estado</th><th>Registro</th><th class="actions-heading">Acciones</th></tr></thead>
          <tbody>
            @for (student of students(); track student.id) {
              <tr><td>{{ student.student_code ?? '—' }}</td><td>{{ student.last_name }}, {{ student.first_name }}</td><td>{{ gradeName(student.grade_id) }}</td><td>{{ sectionName(student.section_id) }}</td><td><span class="status" [class.inactive-status]="student.status !== 'ACTIVE'">{{ student.status === 'ACTIVE' ? 'Activo' : 'Inactivo' }}</span></td><td>{{ student.created_at | date:'dd/MM/yyyy' }}</td><td class="actions-cell"><button class="icon-action" type="button" (click)="selectedStudent.set(student)" title="Ver ficha" aria-label="Ver ficha"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button><button class="icon-action" type="button" (click)="edit(student)" title="Editar estudiante" aria-label="Editar estudiante"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 16.5-.8 4.3 4.3-.8L20 7.5 16.5 4 4 16.5Z"/><path d="m14.8 5.7 3.5 3.5"/></svg></button>@if (student.status === 'ACTIVE') {<button class="icon-action danger-icon" type="button" (click)="remove(student)" title="Desactivar estudiante" aria-label="Desactivar estudiante"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6"/></svg></button>}</td></tr>
            }
          </tbody>
        </table>
      </div>
    }
    @if (selectedStudent(); as profile) { <section class="form profile"><button class="close" type="button" (click)="selectedStudent.set(null)" aria-label="Cerrar ficha">×</button><h2>Ficha del estudiante</h2><p><strong>{{ profile.last_name }}, {{ profile.first_name }}</strong></p><dl><dt>Código</dt><dd>{{ profile.student_code }}</dd><dt>Nivel y grado</dt><dd>{{ gradeName(profile.grade_id) }}</dd><dt>Sección</dt><dd>{{ sectionName(profile.section_id) }}</dd><dt>Estado</dt><dd>{{ profile.status }}</dd><dt>Fecha de nacimiento</dt><dd>{{ profile.birth_date ?? 'No registrada' }}</dd></dl></section> }
  `,
  styles: [`
    .toolbar, .form { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: 18px; }
    .toolbar { display: flex; align-items: end; gap: 12px; margin-bottom: 18px; flex-wrap: wrap; }
    label { display: grid; gap: 6px; color: var(--color-muted-text); font-size: .86rem; }
    .toolbar label { flex: 1 1 155px; min-width: 145px; }
    input, select { width: 100%; min-height: 40px; border: 1px solid var(--color-border); border-radius: 7px; padding: 9px 11px; font: inherit; color: var(--color-text); background: var(--color-surface); }
    select:disabled { background: var(--color-muted); color: var(--color-muted-text); cursor: not-allowed; }
    button { border: 0; border-radius: 5px; padding: 10px 14px; color: white; background: var(--color-primary); cursor: pointer; }
    button.secondary { background: var(--color-accent); }
    .form { margin-bottom: 18px; } .profile{position:relative}.profile dl{display:grid;grid-template-columns:max-content 1fr;gap:8px 18px}.profile dt{color:var(--color-muted-text)}.profile dd{margin:0}.close{position:absolute;right:16px;top:16px;background:transparent;color:var(--color-text);font-size:1.4rem;padding:2px 8px}
    h2 { margin: 0 0 16px; font-size: 1.1rem; }
    .form-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
    .table-wrap { overflow-x: auto; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    th, td { padding: 14px 16px; border-bottom: 1px solid var(--color-border); white-space: nowrap; }
    th { color: var(--color-muted-text); font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }
    tr:last-child td { border-bottom: 0; }
    .status { display:inline-flex;align-items:center;border-radius:999px;padding:4px 9px;background:#e8f5ee;color:#226b4d;font-size:.82rem;font-weight:600; } .inactive-status{background:#f1f5f9;color:#64748b}
    .actions-cell{display:flex;gap:5px}.danger { background: #b94b3b; }
    .state { padding: 24px; background: var(--color-surface); border: 1px solid var(--color-border); }
    .error { color: #a33a32; }
    @media (max-width: 800px) { .toolbar { align-items: stretch; } .toolbar label { flex-basis: 200px; } .form-grid { grid-template-columns: 1fr 1fr; } }
    @media (max-width: 500px) { .form-grid { grid-template-columns: 1fr; } }
  `],
})
export class StudentsPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly confirm = inject(ConfirmService);
  protected readonly students = signal<Student[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal(false);
  protected readonly showForm = signal(false);
  protected readonly formError = signal('');
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] });
  protected search = '';
  protected gradeId = '';
  protected sectionId = '';
  protected statusFilter = '';
  protected readonly selectedStudent = signal<Student | null>(null);
  protected form = { student_code: '', first_name: '', last_name: '', birth_date: '', status: 'ACTIVE', grade_id: '', section_id: '' };

  ngOnInit(): void { this.loadStudents(); this.api.getAcademicCatalog().subscribe({ next: (catalog) => this.catalog.set(catalog) }); }

  protected sectionsForGrade(gradeId: string) { return this.catalog().sections.filter((section) => !!gradeId && section.grade_id === gradeId); }

  protected loadStudents(): void {
    this.loading.set(true);
    this.error.set(false);
    const filters: Record<string, string> = {};
    if (this.gradeId) filters['grade_id'] = this.gradeId;
    if (this.sectionId) filters['section_id'] = this.sectionId;
    if (this.statusFilter) filters['status'] = this.statusFilter;
    this.api.getStudents(this.search, filters).subscribe({
      next: (students) => { this.students.set(students); this.loading.set(false); },
      error: () => { this.error.set(true); this.loading.set(false); },
    });
  }

  protected gradeName(id: string | null): string { return this.catalog().grades.find((grade) => grade.id === id)?.name ?? '-'; }
  protected sectionName(id: string | null): string { return this.catalog().sections.find((section) => section.id === id)?.name ?? '-'; }

  protected createStudent(): void {
    this.formError.set('');
    const payload = {
      ...this.form,
      student_code: this.form.student_code.trim() || null,
      birth_date: this.form.birth_date || undefined,
    };
    const request = this.editingId ? this.api.updateStudent(this.editingId, payload) : this.api.createStudent(payload);
    request.subscribe({
      next: () => { this.form = { student_code: '', first_name: '', last_name: '', birth_date: '', status: 'ACTIVE', grade_id: '', section_id: '' }; this.editingId = null; this.showForm.set(false); this.loadStudents(); },
      error: (error: { error?: { detail?: string } }) => this.formError.set(error.error?.detail ?? 'No se pudo registrar el estudiante.'),
    });
  }

  protected edit(student: Student): void { this.form = { student_code: student.student_code ?? '', first_name: student.first_name, last_name: student.last_name, birth_date: student.birth_date ?? '', status: student.status, grade_id: student.grade_id ?? '', section_id: student.section_id ?? '' }; this.editingId = student.id; this.showForm.set(true); }
  protected async remove(student: Student): Promise<void> { if (await this.confirm.ask(`¿Desactivar a ${student.first_name} ${student.last_name}?`)) this.api.deleteStudent(student.id).subscribe({ next: () => this.loadStudents() }); }
  protected editingId: string | null = null;
}