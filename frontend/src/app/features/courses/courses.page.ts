import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AcademicCatalog, ApiService, AssessmentComponent, AuthUser, CourseAssignment, CoursePayload } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { ConfirmService } from '../../core/services/confirm.service';

type Course = { id: string; name: string; code: string | null; is_active: boolean };

@Component({
  standalone: true,
  imports: [FormsModule, PageHeaderComponent],
  template: `
    <app-page-header title="Cursos" description="Administra cursos y configura los componentes de nota propios de cada uno." />
    <section class="panel">
      @if (error()) { <p class="feedback error" role="alert">{{ error() }}</p> }
      @if (message()) { <p class="feedback" role="status">{{ message() }}</p> }
      <form (ngSubmit)="saveCourse()">
        <div class="grid"><label>Nombre completo del curso<input name="name" [(ngModel)]="form.name" required placeholder="Ej. Razonamiento Matemático" /></label></div>
        <button type="submit">{{ editingCourseId ? 'Guardar cambios' : 'Crear curso' }}</button>
        @if (editingCourseId) { <button type="button" class="muted" (click)="resetCourse()">Cancelar</button> }
      </form>
    </section>
    <section class="panel table-wrap">
      <table><thead><tr><th>Curso</th><th>Código</th><th>Estado</th><th class="actions-heading">Acciones</th></tr></thead><tbody>
        @for (course of courses(); track course.id) {<tr [class.inactive]="!course.is_active"><td>{{ course.name }}</td><td>{{ course.code ?? '—' }}</td><td>{{ course.is_active ? 'Activo' : 'Inactivo' }}</td><td class="actions-cell"><button class="icon-action" type="button" (click)="editCourse(course)" title="Editar curso" aria-label="Editar curso"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 16.5-.8 4.3 4.3-.8L20 7.5 16.5 4 4 16.5Z"/><path d="m14.8 5.7 3.5 3.5"/></svg></button><button class="icon-action" type="button" (click)="chooseCourse(course)" title="Configurar curso" aria-label="Configurar curso"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.5.9l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.5-.9l-1.7.7-1.4-2.4 1.4-1.1a7 7 0 0 1 0-1.8l-1.4-1.1 1.4-2.4 1.7.7a8 8 0 0 1 1.5-.9l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.5.9l1.7-.7 1.4 2.4-1.4 1.1a7 7 0 0 1 0 1.8Z"/></svg></button><button class="icon-action danger-icon" type="button" (click)="toggleCourse(course)" [title]="course.is_active ? 'Archivar curso' : 'Reactivar curso'" [attr.aria-label]="course.is_active ? 'Archivar curso' : 'Reactivar curso'"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16v13H4zM3 4h18v3H3zM10 11h4"/></svg></button></td></tr>}
      </tbody></table>
    </section>
    @if (selectedCourse()) {
      <section class="panel">
        <h2>Componentes de {{ selectedCourse()!.name }}</h2>
        <form (ngSubmit)="saveComponent()">
          <div class="component-form"><label>Componente<input name="component_name" [(ngModel)]="componentForm.name" placeholder="Actitud ante el área, Cuaderno, Módulo..." required /></label><label>Peso<input name="component_weight" type="number" min="0" max="100" step="0.1" [(ngModel)]="componentForm.weight" required /></label><label class="check"><input name="is_optional" type="checkbox" [(ngModel)]="componentForm.is_optional" /> Opcional para este curso</label></div>
          <button type="submit">Agregar componente</button>
        </form>
        <div class="table-wrap"><table><thead><tr><th>Componente</th><th>Peso</th><th>Opcional</th><th>Estado</th><th class="actions-heading">Acciones</th></tr></thead><tbody>
          @for (component of components(); track component.id) {<tr [class.inactive]="!component.is_active"><td>{{ component.name }}</td><td><input class="weight" type="number" min="0" max="100" step="0.1" [(ngModel)]="component.weight" /></td><td>{{ component.is_optional ? 'Sí' : 'No' }}</td><td>{{ component.is_active ? 'Activo' : 'Inactivo' }}</td><td class="actions-cell"><button class="icon-action" type="button" (click)="updateComponent(component)" title="Guardar peso" aria-label="Guardar peso"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 3h12l4 4v14H3V3h2Z"/><path d="M7 3v6h10V3M7 21v-8h10v8"/></svg></button>@if (component.is_active) {<button class="icon-action danger-icon" type="button" (click)="deactivateComponent(component)" title="Desactivar componente" aria-label="Desactivar componente"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6"/></svg></button>}</td></tr>}
        </tbody></table></div>
      </section>
      <section class="panel">
        <h2>Asignación a grado y sección</h2>
        <div class="component-form"><label>Grado<select [(ngModel)]="assignmentGradeId" (ngModelChange)="assignmentSectionId = ''"><option value="">Seleccionar grado</option>@for (grade of catalog().grades; track grade.id) {<option [value]="grade.id">{{ grade.name }} · {{ grade.level }}</option>}</select></label><label>Sección<select [(ngModel)]="assignmentSectionId" [disabled]="!assignmentGradeId"><option value="">Seleccionar sección</option>@for (section of sectionsForAssignment(); track section.id) {<option [value]="section.id">{{ section.name }}</option>}</select></label><label>Docente del padrón<input [(ngModel)]="assignmentTeacherName" placeholder="Nombre del docente" /></label>@if (isAdmin) {<label>Usuario docente asociado<select [(ngModel)]="assignmentTeacherId"><option value="">Sin cuenta vinculada</option>@for (teacher of teachers(); track teacher.id) {<option [value]="teacher.id">{{ teacher.full_name }}</option>}</select></label>}</div>
        <button type="button" (click)="assignCourse()" [disabled]="!assignmentSectionId">Asignar curso</button>
        <div class="table-wrap"><table><thead><tr><th>Grado</th><th>Sección</th><th>Docente</th><th></th></tr></thead><tbody>        @for (assignment of assignments(); track assignment.id) {<tr><td>{{ gradeName(assignment.grade_id) }}</td><td>{{ sectionName(assignment.section_id) }}</td><td>{{ assignment.teacher_name ?? teacherName(assignment.teacher_id) }}</td><td><button class="icon-action danger-icon" type="button" (click)="removeAssignment(assignment)" title="Quitar asignación" aria-label="Quitar asignación"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6"/></svg></button></td></tr>}</tbody></table></div>
      </section>
    }
  `,
  styles: [`
    .panel{background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;padding:22px;margin-bottom:18px}.grid,.component-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}label{display:grid;gap:7px;color:var(--color-muted-text)}input,select{padding:10px;border:1px solid var(--color-border);border-radius:6px;font:inherit;background:var(--color-surface)}.check{display:flex;align-items:center;gap:8px}.check input{width:18px;height:18px}button{margin:14px 8px 0 0;background:var(--color-primary);color:white;border:0;border-radius:6px;padding:10px 14px;cursor:pointer}.muted{background:var(--color-muted-text)}.danger{background:#b94b3b}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:12px;border-bottom:1px solid var(--color-border);text-align:left;white-space:nowrap}.actions-cell{display:flex;gap:5px}.weight{width:90px}.inactive{opacity:.6}h2{font-size:1.2rem}@media(max-width:700px){.grid,.component-form{grid-template-columns:1fr}}
  `],
})
export class CoursesPage {
  private readonly api = inject(ApiService);
  private readonly confirm = inject(ConfirmService);
  protected readonly courses = signal<Course[]>([]);
  protected readonly components = signal<AssessmentComponent[]>([]);
  protected readonly assignments = signal<CourseAssignment[]>([]);
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] });
  protected readonly teachers = signal<AuthUser[]>([]);
  protected readonly error = signal('');
  protected readonly message = signal('');
  protected readonly selectedCourse = signal<Course | null>(null);
  protected form: CoursePayload = { name: '' };
  protected componentForm = { name: '', weight: 1, is_optional: false };
  protected assignmentGradeId = '';
  protected assignmentSectionId = '';
  protected assignmentTeacherId = '';
  protected assignmentTeacherName = '';
  protected editingCourseId: string | null = null;
  protected readonly isAdmin = (() => { try { return JSON.parse(localStorage.getItem('paideia_user') ?? '{}').role === 'admin'; } catch { return false; } })();

  constructor() {
    this.loadCourses();
    this.api.getAcademicCatalog().subscribe({ next: (data) => this.catalog.set(data) });
    if (this.isAdmin) this.api.listUsers().subscribe({ next: (users) => this.teachers.set(users.filter((user) => user.role === 'teacher')) });
  }
  protected loadCourses(): void { this.api.listCourses().subscribe({ next: (data) => { this.courses.set(data); this.error.set(''); }, error: () => this.error.set('No se pudieron cargar los cursos. Verifica tu conexión e intenta nuevamente.') }); }
  protected editCourse(course: Course): void { this.editingCourseId = course.id; this.form = { name: course.name, code: course.code }; }
  protected resetCourse(): void { this.editingCourseId = null; this.form = { name: '' }; }
  protected saveCourse(): void {
    const request = this.editingCourseId ? this.api.updateCourse(this.editingCourseId, this.form) : this.api.createCourse(this.form);
    request.subscribe({ next: () => { this.resetCourse(); this.message.set('Curso guardado.'); this.error.set(''); this.loadCourses(); }, error: (error: { error?: { detail?: string } }) => this.error.set(error.error?.detail ?? 'No se pudo guardar el curso.') });
  }
  protected async toggleCourse(course: Course): Promise<void> { const action = course.is_active ? 'desactivar' : 'reactivar'; if (await this.confirm.ask(`¿Quieres ${action} ${course.name}?`)) this.api.updateCourse(course.id, { is_active: !course.is_active }).subscribe({ next: () => { this.message.set(`Curso ${course.is_active ? 'archivado' : 'reactivado'}.`); this.loadCourses(); }, error: () => this.error.set('No se pudo actualizar el estado del curso.') }); }
  protected chooseCourse(course: Course): void { this.selectedCourse.set(course); this.componentForm = { name: '', weight: 1, is_optional: false }; this.loadComponents(); this.loadAssignments(); }
  private loadComponents(): void { const course = this.selectedCourse(); if (course) this.api.listAssessmentComponents(course.id).subscribe({ next: (data) => this.components.set(data) }); }
  private loadAssignments(): void { const course = this.selectedCourse(); if (course) this.api.listCourseAssignments(course.id).subscribe({ next: (data) => this.assignments.set(data) }); }
  protected saveComponent(): void { const course = this.selectedCourse(); if (!course) return; this.api.createAssessmentComponent(course.id, this.componentForm).subscribe({ next: () => { this.componentForm = { name: '', weight: 1, is_optional: false }; this.loadComponents(); } }); }
  protected updateComponent(component: AssessmentComponent): void { const course = this.selectedCourse(); if (course) this.api.updateAssessmentComponent(course.id, component.id, { weight: Number(component.weight) }).subscribe({ next: () => this.loadComponents() }); }
  protected async deactivateComponent(component: AssessmentComponent): Promise<void> { const course = this.selectedCourse(); if (course && await this.confirm.ask(`¿Desactivar ${component.name}?`)) this.api.deactivateAssessmentComponent(course.id, component.id).subscribe({ next: () => this.loadComponents(), error: () => this.error.set('No se pudo desactivar el componente.') }); }
  protected sectionsForAssignment() { return this.catalog().sections.filter((section) => section.grade_id === this.assignmentGradeId); }
  protected gradeName(id: string): string { return this.catalog().grades.find((grade) => grade.id === id)?.name ?? id; }
  protected sectionName(id: string): string { return this.catalog().sections.find((section) => section.id === id)?.name ?? id; }
  protected teacherName(id: string | null): string { return this.teachers().find((teacher) => teacher.id === id)?.full_name ?? (id ? 'Docente asignado' : 'Sin asignar'); }
  protected assignCourse(): void {
    const course = this.selectedCourse();
    if (!course || !this.assignmentSectionId) return;
    const payload: { section_id: string; teacher_id?: string; teacher_name?: string } = { section_id: this.assignmentSectionId };
    if (this.assignmentTeacherId) payload.teacher_id = this.assignmentTeacherId;
    if (this.assignmentTeacherName.trim()) payload.teacher_name = this.assignmentTeacherName.trim();
    this.api.createCourseAssignment(course.id, payload).subscribe({ next: () => { this.assignmentSectionId = ''; this.assignmentTeacherId = ''; this.assignmentTeacherName = ''; this.loadAssignments(); } });
  }
  protected async removeAssignment(assignment: CourseAssignment): Promise<void> {
    const course = this.selectedCourse();
    if (course && await this.confirm.ask(`¿Quitar la asignación de ${this.gradeName(assignment.grade_id)} ${this.sectionName(assignment.section_id)}?`)) this.api.deleteCourseAssignment(course.id, assignment.id).subscribe({ next: () => this.loadAssignments(), error: () => this.error.set('No se pudo quitar la asignación.') });
  }
}
