import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AcademicCatalog, ApiService, Student } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

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
      <label>Sección<select [(ngModel)]="sectionId" (ngModelChange)="loadStudents()"><option value="">Todas</option>@for (section of availableSections(); track section.id) {<option [value]="section.id">{{ section.name }}</option>}</select></label>
      <button type="button" (click)="loadStudents()">Buscar</button>
      <button type="button" class="secondary" (click)="showForm.set(!showForm())">{{ showForm() ? 'Cerrar' : 'Nuevo estudiante' }}</button>
    </section>
    @if (showForm()) {
      <form class="form" (ngSubmit)="createStudent()">
        <h2>{{ editingId ? 'Editar estudiante' : 'Registrar estudiante' }}</h2>
        <div class="form-grid">
          <label>Código<input name="student_code" [(ngModel)]="form.student_code" required /></label>
          <label>Nombres<input name="first_name" [(ngModel)]="form.first_name" required /></label>
          <label>Apellidos<input name="last_name" [(ngModel)]="form.last_name" required /></label>
          <label>Fecha de nacimiento<input name="birth_date" type="date" [(ngModel)]="form.birth_date" /></label>
          <label>Grado<select name="grade_id" [(ngModel)]="form.grade_id" (ngModelChange)="form.section_id = ''" required><option value="">Seleccionar</option>@for (grade of catalog().grades; track grade.id) { <option [value]="grade.id">{{ grade.name }} - {{ grade.level }}</option> }</select></label>
          <label>Sección<select name="section_id" [(ngModel)]="form.section_id" required><option value="">Seleccionar</option>@for (section of availableSections(); track section.id) { <option [value]="section.id">{{ section.name }}</option> }</select></label>
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
          <thead><tr><th>Código</th><th>Estudiante</th><th>Grado</th><th>Sección</th><th>Estado</th><th>Registro</th><th>Acciones</th></tr></thead>
          <tbody>
            @for (student of students(); track student.id) {
              <tr><td>{{ student.student_code }}</td><td>{{ student.last_name }}, {{ student.first_name }}</td><td>{{ gradeName(student.grade_id) }}</td><td>{{ sectionName(student.section_id) }}</td><td><span class="status">{{ student.status }}</span></td><td>{{ student.created_at | date:'dd/MM/yyyy' }}</td><td><button class="small" type="button" (click)="edit(student)">Editar</button><button class="small danger" type="button" (click)="remove(student)">Eliminar</button></td></tr>
            }
          </tbody>
        </table>
      </div>
    }
  `,
  styles: [`
    .toolbar, .form { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: 18px; }
    .toolbar { display: flex; align-items: end; gap: 12px; margin-bottom: 18px; }
    label { display: grid; gap: 6px; color: var(--color-muted-text); font-size: .86rem; }
    .toolbar label { flex: 1; }
    input { border: 1px solid var(--color-border); border-radius: 5px; padding: 10px 12px; font: inherit; color: var(--color-text); }
    button { border: 0; border-radius: 5px; padding: 10px 14px; color: white; background: var(--color-primary); cursor: pointer; }
    button.secondary { background: var(--color-accent); }
    .form { margin-bottom: 18px; }
    h2 { margin: 0 0 16px; font-size: 1.1rem; }
    .form-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
    .table-wrap { overflow-x: auto; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    th, td { padding: 14px 16px; border-bottom: 1px solid var(--color-border); white-space: nowrap; }
    th { color: var(--color-muted-text); font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }
    tr:last-child td { border-bottom: 0; }
    .status { color: #226b4d; font-size: .82rem; font-weight: 600; } .small { padding: 7px 10px; margin: 0 5px 0 0; } .danger { background: #b94b3b; }
    .state { padding: 24px; background: var(--color-surface); border: 1px solid var(--color-border); }
    .error { color: #a33a32; }
    @media (max-width: 800px) { .toolbar { align-items: stretch; flex-wrap: wrap; } .toolbar label { flex-basis: 100%; } .form-grid { grid-template-columns: 1fr 1fr; } }
    @media (max-width: 500px) { .form-grid { grid-template-columns: 1fr; } }
  `],
})
export class StudentsPage implements OnInit {
  private readonly api = inject(ApiService);
  protected readonly students = signal<Student[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal(false);
  protected readonly showForm = signal(false);
  protected readonly formError = signal('');
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [] });
  protected search = '';
  protected gradeId = '';
  protected sectionId = '';
  protected form = { student_code: '', first_name: '', last_name: '', birth_date: '', status: 'ACTIVE', grade_id: '', section_id: '' };

  ngOnInit(): void { this.loadStudents(); this.api.getAcademicCatalog().subscribe({ next: (catalog) => this.catalog.set(catalog) }); }

  protected availableSections() { return this.catalog().sections.filter((section) => section.grade_id === this.form.grade_id); }

  protected loadStudents(): void {
    this.loading.set(true);
    this.error.set(false);
    const filters: Record<string, string> = {};
    if (this.gradeId) filters['grade_id'] = this.gradeId;
    if (this.sectionId) filters['section_id'] = this.sectionId;
    this.api.getStudents(this.search, filters).subscribe({
      next: (students) => { this.students.set(students); this.loading.set(false); },
      error: () => { this.error.set(true); this.loading.set(false); },
    });
  }

  protected gradeName(id: string | null): string { return this.catalog().grades.find((grade) => grade.id === id)?.name ?? '-'; }
  protected sectionName(id: string | null): string { return this.catalog().sections.find((section) => section.id === id)?.name ?? '-'; }

  protected createStudent(): void {
    this.formError.set('');
    const request = this.editingId ? this.api.updateStudent(this.editingId, this.form) : this.api.createStudent(this.form);
    request.subscribe({
      next: () => { this.form = { student_code: '', first_name: '', last_name: '', birth_date: '', status: 'ACTIVE', grade_id: '', section_id: '' }; this.editingId = null; this.showForm.set(false); this.loadStudents(); },
      error: (error: { error?: { detail?: string } }) => this.formError.set(error.error?.detail ?? 'No se pudo registrar el estudiante.'),
    });
  }

  protected edit(student: Student): void { this.form = { student_code: student.student_code, first_name: student.first_name, last_name: student.last_name, birth_date: student.birth_date ?? '', status: student.status, grade_id: student.grade_id ?? '', section_id: student.section_id ?? '' }; this.editingId = student.id; this.showForm.set(true); }
  protected remove(student: Student): void { if (confirm(`¿Eliminar a ${student.first_name} ${student.last_name}?`)) this.api.deleteStudent(student.id).subscribe({ next: () => this.loadStudents() }); }
  protected editingId: string | null = null;
}