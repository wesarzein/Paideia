import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, AuthUser, UserPayload } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [FormsModule, PageHeaderComponent],
  template: `<app-page-header title="Usuarios" description="Administra el equipo académico y sus permisos dentro del colegio." /><section class="panel"><form (ngSubmit)="save()"><div class="grid"><label>Nombre completo<input name="full_name" [(ngModel)]="form.full_name" required /></label><label>Email<input name="email" type="email" [(ngModel)]="form.email" [disabled]="editingId !== null" required /></label><label>Contraseña<input name="password" type="password" [(ngModel)]="form.password" [required]="editingId === null" /></label><label>Rol<select name="role_code" [(ngModel)]="form.role_code"><option value="admin">Administrador</option><option value="teacher">Docente</option><option value="coordinator">Coordinador</option><option value="director">Directivo</option></select></label></div><button type="submit">{{ editingId ? 'Guardar cambios' : 'Crear usuario' }}</button>@if (editingId) {<button type="button" class="muted" (click)="reset()">Cancelar</button>}</form></section><section class="panel table-wrap"><table><thead><tr><th>Nombre</th><th>Email</th><th>Rol</th><th>Acciones</th></tr></thead><tbody>@for (user of users(); track user.id) {<tr><td>{{ user.full_name }}</td><td>{{ user.email }}</td><td>{{ user.role }}</td><td><button class="small" type="button" (click)="edit(user)">Editar</button><button class="danger small" type="button" (click)="remove(user)">Eliminar</button></td></tr>}</tbody></table></section>`,
  styles: [` .panel{background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;padding:22px;margin-bottom:18px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}label{display:grid;gap:7px;color:var(--color-muted-text)}input,select{padding:10px;border:1px solid var(--color-border);border-radius:6px;font:inherit}button{margin:16px 8px 0 0;background:var(--color-primary);color:white;border:0;border-radius:6px;padding:10px 14px;cursor:pointer}.muted{background:var(--color-muted-text)}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:12px;border-bottom:1px solid var(--color-border);text-align:left;white-space:nowrap}.small{padding:7px 10px;margin:0 5px 0 0}.danger{background:#b94b3b}@media(max-width:700px){.grid{grid-template-columns:1fr}} `],
})
export class UsersPage {
  private readonly api = inject(ApiService); protected readonly users = signal<AuthUser[]>([]); protected editingId: string | null = null; protected form: UserPayload = { email: '', full_name: '', password: '', role_code: 'teacher' };
  constructor() { this.load(); }
  private load() { this.api.listUsers().subscribe({ next: (data) => this.users.set(data) }); }
  protected edit(user: AuthUser) { this.editingId = user.id; this.form = { email: user.email, full_name: user.full_name, password: '', role_code: user.role }; }
  protected reset() { this.editingId = null; this.form = { email: '', full_name: '', password: '', role_code: 'teacher' }; }
  protected save() { const request = this.editingId ? this.api.updateUser(this.editingId, { full_name: this.form.full_name, password: this.form.password || undefined, role_code: this.form.role_code }) : this.api.createUser(this.form); request.subscribe({ next: () => { this.reset(); this.load(); } }); }
  protected remove(user: AuthUser) { if (confirm(`¿Eliminar a ${user.full_name}?`)) this.api.deleteUser(user.id).subscribe({ next: () => this.load() }); }
}
