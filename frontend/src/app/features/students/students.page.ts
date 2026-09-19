import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Student } from '../../core/services/api.service';
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
      <button type="button" (click)="loadStudents()">Buscar</button>
      <button type="button" class="secondary" (click)="showForm.set(!showForm())">{{ showForm() ? 'Cerrar' : 'Nuevo estudiante' }}</button>
    </section>
    @if (showForm()) {
      <form class="form" (ngSubmit)="createStudent()">
        <h2>Registrar estudiante</h2>
        <div class="form-grid">
          <label>Código<input name="student_code" [(ngModel)]="form.student_code" required /></label>
          <label>Nombres<input name="first_name" [(ngModel)]="form.first_name" required /></label>
          <label>Apellidos<input name="last_name" [(ngModel)]="form.last_name" required /></label>
          <label>Fecha de nacimiento<input name="birth_date" type="date" [(ngModel)]="form.birth_date" /></label>
        </div>
        <button type="submit">Guardar estudiante</button>
        @if (formError()) { <p class="error">{{ formError() }}</p> }
      </form>
    }
    @if (loading()) { <p class="state">Cargando estudiantes...</p> }
    @else if (error()) { <p class="state error">No se pudo conectar con la API.</p> }
    @else if (students().length === 0) { <p class="state">No hay estudiantes registrados.</p> }
    @else {
      <div class="table-wrap">
        <table>
          <thead><tr><th>Código</th><th>Estudiante</th><th>Estado</th><th>Registro</th></tr></thead>
          <tbody>
            @for (student of students(); track student.id) {
              <tr><td>{{ student.student_code }}</td><td>{{ student.last_name }}, {{ student.first_name }}</td><td><span class="status">{{ student.status }}</span></td><td>{{ student.created_at | date:'dd/MM/yyyy' }}</td></tr>
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
    .status { color: #226b4d; font-size: .82rem; font-weight: 600; }
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
  protected search = '';
  protected form = { student_code: '', first_name: '', last_name: '', birth_date: '', status: 'ACTIVE' };

  ngOnInit(): void { this.loadStudents(); }

  protected loadStudents(): void {
    this.loading.set(true);
    this.error.set(false);
    this.api.getStudents(this.search).subscribe({
      next: (students) => { this.students.set(students); this.loading.set(false); },
      error: () => { this.error.set(true); this.loading.set(false); },
    });
  }

  protected createStudent(): void {
    this.formError.set('');
    this.api.createStudent(this.form).subscribe({
      next: () => { this.form = { student_code: '', first_name: '', last_name: '', birth_date: '', status: 'ACTIVE' }; this.showForm.set(false); this.loadStudents(); },
      error: (error: { error?: { detail?: string } }) => this.formError.set(error.error?.detail ?? 'No se pudo registrar el estudiante.'),
    });
  }
}