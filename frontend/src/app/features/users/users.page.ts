import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AcademicCatalog, ApiService, AuthUser, Student, UserPayload } from '../../core/services/api.service';
import { ConfirmService } from '../../core/services/confirm.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [FormsModule, PageHeaderComponent],
  template: `
    <app-page-header title="Usuarios" description="Administra las cuentas, sus permisos y los vínculos académicos." />
    <section class="panel">
      <form (ngSubmit)="save()">
        <div class="grid">
          <label>Nombre completo<input name="full_name" [(ngModel)]="form.full_name" required /></label>
          <label>Email<input name="email" type="email" [(ngModel)]="form.email" [disabled]="editingId !== null" required /></label>
          <label>Contraseña<input name="password" type="password" [(ngModel)]="form.password" [required]="editingId === null" [minlength]="editingId === null ? 12 : 8" /></label>
          <label>Rol
            <select name="role_code" [(ngModel)]="form.role_code" (ngModelChange)="changeRole($event)">
              <option value="admin">Administrador</option><option value="teacher">Docente</option>
              <option value="coordinator">Coordinador</option><option value="director">Directivo</option>
              <option value="student">Estudiante</option><option value="parent">Padre / apoderado</option>
            </select>
          </label>
          @if (form.role_code === 'student') {
            <label>Estudiante vinculado
              <select name="student_id" [(ngModel)]="form.student_id" required>
                <option value="">Selecciona un estudiante</option>
                @for (student of availableStudents(); track student.id) { <option [value]="student.id">{{ studentLabel(student) }}</option> }
              </select>
            </label>
          }
          @if (form.role_code === 'parent') {
            <label>Estudiantes a cargo
              <select name="student_ids" multiple [(ngModel)]="form.student_ids" required>
                @for (student of availableStudents(); track student.id) { <option [value]="student.id">{{ studentLabel(student) }}</option> }
              </select>
              <small>Usa Ctrl (Windows) o Cmd (Mac) para seleccionar varios alumnos.</small>
            </label>
          }
        </div>
        @if (error()) { <p class="error" role="alert">{{ error() }}</p> }
        @if (message()) { <p class="message" role="status">{{ message() }}</p> }
        <button type="submit">{{ editingId ? 'Guardar cambios' : 'Crear usuario' }}</button>
        @if (editingId) { <button type="button" class="muted" (click)="reset()">Cancelar</button> }
      </form>
    </section>
    <section class="panel table-wrap">
      <table><thead><tr><th>Nombre</th><th>Email</th><th>Rol</th><th>Vínculos</th><th class="actions-heading">Acciones</th></tr></thead><tbody>
        @for (user of users(); track user.id) {
          <tr>
            <td>{{ user.full_name }}</td><td>{{ user.email }}</td><td>{{ roleName(user.role) }}</td>
            <td>{{ linkedStudents(user) }}</td>
            <td class="actions-cell"><button class="icon-action" type="button" (click)="edit(user)" title="Editar usuario" aria-label="Editar usuario"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 16.5-.8 4.3 4.3-.8L20 7.5 16.5 4 4 16.5Z"/><path d="m14.8 5.7 3.5 3.5"/></svg></button><button class="icon-action danger-icon" type="button" (click)="remove(user)" title="Eliminar usuario" aria-label="Eliminar usuario"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6"/></svg></button></td>
          </tr>
        }
      </tbody></table>
      @if (loadError()) { <p class="error" role="alert">No se pudieron cargar usuarios o estudiantes. Reintenta.</p> }
    </section>
  `,
  styles: [`
    .panel{background:var(--color-surface);border:1px solid var(--color-border);border-radius:10px;padding:22px;margin-bottom:18px}
    .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
    label{display:grid;gap:7px;color:var(--color-muted-text)}input,select{padding:10px;border:1px solid var(--color-border);border-radius:7px;font:inherit;color:var(--color-text)}
    select[multiple]{min-height:150px}small{font-size:.78rem;color:var(--color-muted-text)}
    button{margin:16px 8px 0 0;background:var(--color-primary);color:white;border:0;border-radius:7px;padding:10px 14px;cursor:pointer}
    .muted{background:var(--color-muted-text)}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse}.actions-cell{display:flex;gap:5px}
    th,td{padding:12px;border-bottom:1px solid var(--color-border);text-align:left;white-space:nowrap}
    .small{padding:7px 10px;margin:0 5px 0 0}.danger{background:#b94b3b}.error{color:#a33a32}.message{color:#24704d}
    @media(max-width:700px){.grid{grid-template-columns:1fr}}
  `],
})
export class UsersPage {
  private readonly api = inject(ApiService);
  private readonly confirm = inject(ConfirmService);
  protected readonly users = signal<AuthUser[]>([]);
  protected readonly students = signal<Student[]>([]);
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] });
  protected readonly error = signal('');
  protected readonly message = signal('');
  protected readonly loadError = signal(false);
  protected editingId: string | null = null;
  protected form: UserPayload = { email: '', full_name: '', password: '', role_code: 'teacher', student_id: null, student_ids: [] };

  constructor() { this.load(); }

  private load(): void {
    this.loadError.set(false);
    this.api.listUsers().subscribe({
      next: (data) => this.users.set(data),
      error: () => this.loadError.set(true),
    });
    this.api.getStudents().subscribe({
      next: (data) => this.students.set(data),
      error: () => this.loadError.set(true),
    });
    this.api.getAcademicCatalog().subscribe({
      next: (data) => this.catalog.set(data),
      error: () => this.loadError.set(true),
    });
  }

  protected availableStudents(): Student[] {
    const roleField = this.form.role_code === 'student' ? 'student_user_id' : 'parent_user_id';
    return this.students().filter((student) => !student[roleField] || student[roleField] === this.editingId);
  }

  protected studentLabel(student: Student): string {
    const grade = this.catalog().grades.find((item) => item.id === student.grade_id)?.name ?? '';
    const section = this.catalog().sections.find((item) => item.id === student.section_id)?.name ?? '';
    return `${student.student_code ?? ''} · ${student.last_name}, ${student.first_name} · ${grade} ${section}`.trim();
  }

  protected linkedStudents(user: AuthUser): string {
    if (user.role === 'student') return this.students().find((student) => student.id === user.student_id)?.student_code ?? 'Sin vínculo';
    if (user.role === 'parent') return String(user.student_ids?.length ?? 0);
    return '—';
  }

  protected roleName(role: string): string {
    return ({ admin: 'Administrador', teacher: 'Docente', coordinator: 'Coordinador', director: 'Directivo', student: 'Estudiante', parent: 'Padre / apoderado' } as Record<string, string>)[role] ?? role;
  }

  protected changeRole(role: string): void {
    this.form.role_code = role;
    this.form.student_id = null;
    this.form.student_ids = [];
  }

  protected edit(user: AuthUser): void {
    this.editingId = user.id;
    this.form = {
      email: user.email,
      full_name: user.full_name,
      password: '',
      role_code: user.role,
      student_id: user.student_id ?? null,
      student_ids: [...(user.student_ids ?? [])],
    };
    this.error.set('');
    this.message.set('');
  }

  protected reset(): void {
    this.editingId = null;
    this.form = { email: '', full_name: '', password: '', role_code: 'teacher', student_id: null, student_ids: [] };
  }

  protected save(): void {
    this.error.set('');
    this.message.set('');
    const payload: UserPayload = { ...this.form };
    if (payload.role_code === 'student') payload.student_ids = [];
    else payload.student_id = null;
    const request = this.editingId
      ? this.api.updateUser(this.editingId, { full_name: payload.full_name, password: payload.password || undefined, role_code: payload.role_code, student_id: payload.student_id, student_ids: payload.student_ids })
      : this.api.createUser(payload);
    request.subscribe({
      next: () => { this.message.set('Usuario y vínculos guardados.'); this.reset(); this.load(); },
      error: (response: { error?: { detail?: string | { message?: string } } }) => {
        const detail = response.error?.detail;
        this.error.set(typeof detail === 'string' ? detail : 'No se pudo guardar el usuario o el vínculo seleccionado.');
      },
    });
  }

  protected async remove(user: AuthUser): Promise<void> {
    if (await this.confirm.ask(`¿Eliminar la cuenta de ${user.full_name}? Los registros académicos se conservarán.`)) {
      this.api.deleteUser(user.id).subscribe({
        next: () => { this.message.set('Cuenta eliminada; los registros académicos siguen conservados.'); this.load(); },
        error: () => this.error.set('No se pudo eliminar la cuenta.'),
      });
    }
  }
}
