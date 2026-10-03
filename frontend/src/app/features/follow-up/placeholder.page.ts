import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AcademicCatalog, ApiService } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { ConfirmService } from '../../core/services/confirm.service';

type FollowUp = { id: string; student_id: string; category: string; action: string; status: string };

@Component({
  standalone: true,
  imports: [FormsModule, PageHeaderComponent],
  template: `
    <app-page-header title="Seguimiento académico" description="Registra observaciones, acuerdos y acciones por estudiante." />
    <section class="panel filters">
      <label>Nivel<select [(ngModel)]="level" (ngModelChange)="gradeId = ''; sectionId = ''; loadCatalog()"><option value="">Seleccionar nivel</option>@for (item of levels(); track item) {<option [value]="item">{{ item }}</option>}</select></label>
      <label>Grado<select [(ngModel)]="gradeId" (ngModelChange)="sectionId = ''; loadCatalog()" [disabled]="!level"><option value="">Seleccionar grado</option>@for (grade of gradesForLevel(); track grade.id) {<option [value]="grade.id">{{ grade.name }}</option>}</select></label>
      <label>Sección<select [(ngModel)]="sectionId" (ngModelChange)="studentId = ''; loadCatalog()" [disabled]="!gradeId"><option value="">Seleccionar sección</option>@for (section of sectionsForGrade(); track section.id) {<option [value]="section.id">{{ gradeName(section.grade_id) }} · {{ section.name }}</option>}</select></label>
    </section>
    @if (!sectionId) {
      <p class="panel">Selecciona el grado y la sección para consultar el historial de su grupo.</p>
    } @else {
      <section class="panel">
        <label>Estudiante<select [(ngModel)]="studentId"><option value="">Seleccionar estudiante</option>@for (student of catalog().students; track student.id) {<option [value]="student.id">{{ student.name }}</option>}</select></label>
        <label>Tipo<select [(ngModel)]="category"><option value="OBSERVATION">Observación</option><option value="PEDAGOGICAL_AGREEMENT">Acuerdo pedagógico</option><option value="MEETING">Reunión o interacción</option><option value="ACTION">Acción realizada</option></select></label>
        <label>Descripción<textarea [(ngModel)]="action" placeholder="Describe el hecho, acuerdo o siguiente acción..."></textarea></label>
        <button type="button" (click)="save()">{{ editingId ? 'Guardar cambios' : 'Registrar seguimiento' }}</button>
        @if (editingId) { <button type="button" class="muted" (click)="reset()">Cancelar</button> }
        @if (message()) { <p role="status">{{ message() }}</p> }
      </section>
      <section class="panel">
        <h2>Historial del grupo</h2>
        @if (!items().length) { <p>Aún no hay seguimientos para esta sección.</p> }
        @for (item of items(); track item.id) {
          <article>
            <div><strong>{{ studentName(item.student_id) }}</strong><span>{{ categoryName(item.category) }} · {{ item.status }}</span></div>
            <p>{{ item.action }}</p>
            <footer class="actions-cell"><button type="button" class="icon-action" (click)="edit(item)" title="Editar seguimiento" aria-label="Editar seguimiento"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 16.5-.8 4.3 4.3-.8L20 7.5 16.5 4 4 16.5Z"/><path d="m14.8 5.7 3.5 3.5"/></svg></button><button type="button" class="icon-action danger-icon" (click)="remove(item)" title="Eliminar seguimiento" aria-label="Eliminar seguimiento"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6"/></svg></button></footer>
          </article>
        }
      </section>
    }
  `,
  styles: [`
    .panel{background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;padding:22px;margin-bottom:18px}
    .filters{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
    label{display:grid;gap:7px;color:var(--color-muted-text);margin-bottom:14px}
    select,textarea{padding:10px;border:1px solid var(--color-border);border-radius:6px;font:inherit}
    textarea{min-height:90px;resize:vertical}
    button{background:var(--color-primary);color:white;border:0;border-radius:6px;padding:10px 14px;cursor:pointer;margin-right:7px}footer{display:flex;gap:6px}
    .muted{background:var(--color-muted-text)} article{border-top:1px solid var(--color-border);padding:14px 0}
    article div{display:flex;justify-content:space-between;gap:10px} span{color:var(--color-muted-text)} footer{display:flex;gap:6px}
    .danger{background:#b94b3b}
    @media(max-width:700px){.filters{grid-template-columns:1fr}article div{display:grid}}
  `],
})
export class PlaceholderPage {
  private readonly api = inject(ApiService);
  private readonly confirm = inject(ConfirmService);
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] });
  protected readonly items = signal<FollowUp[]>([]);
  protected readonly message = signal('');
  protected level = '';
  protected gradeId = '';
  protected sectionId = '';
  protected studentId = '';
  protected category = 'OBSERVATION';
  protected action = '';
  protected editingId: string | null = null;

  constructor() { this.loadCatalog(); }
  protected levels(): string[] { return [...new Set(this.catalog().grades.map((item) => item.level))]; }
  protected gradesForLevel() { return this.catalog().grades.filter((item) => item.level === this.level); }
  protected sectionsForGrade() { return this.catalog().sections.filter((item) => item.grade_id === this.gradeId); }
  protected gradeName(id: string) { return this.catalog().grades.find((item) => item.id === id)?.name ?? ''; }

  protected loadCatalog(): void {
    const filters: Record<string, string> = {};
    if (this.gradeId) filters['grade_id'] = this.gradeId;
    if (this.sectionId) filters['section_id'] = this.sectionId;
    this.api.getAcademicCatalog(filters).subscribe({
      next: (catalog) => { this.catalog.set(catalog); if (this.sectionId) this.loadItems(); else this.items.set([]); },
    });
  }

  private loadItems(): void {
    this.api.listFollowUps({ grade_id: this.gradeId, section_id: this.sectionId }).subscribe({ next: (items) => this.items.set(items) });
  }

  protected studentName(id: string): string { return this.catalog().students.find((student) => student.id === id)?.name ?? id; }
  protected categoryName(category: string): string { return ({ OBSERVATION: 'Observación', PEDAGOGICAL_AGREEMENT: 'Acuerdo pedagógico', MEETING: 'Reunión', ACTION: 'Acción realizada' } as Record<string, string>)[category] ?? category; }
  protected edit(item: FollowUp): void { this.editingId = item.id; this.studentId = item.student_id; this.category = item.category; this.action = item.action; }
  protected reset(): void { this.editingId = null; this.studentId = ''; this.category = 'OBSERVATION'; this.action = ''; }

  protected save(): void {
    if (!this.sectionId || !this.studentId || this.action.trim().length < 3) { this.message.set('Selecciona un estudiante e ingresa una descripción de al menos 3 caracteres.'); return; }
    const payload = { student_id: this.studentId, category: this.category, action: this.action.trim(), status: 'OPEN' };
    const request = this.editingId ? this.api.updateFollowUp(this.editingId, payload) : this.api.createFollowUp(payload);
    request.subscribe({ next: () => { this.message.set('Seguimiento guardado.'); this.reset(); this.loadItems(); } });
  }

  protected async remove(item: FollowUp): Promise<void> {
    if (await this.confirm.ask('¿Eliminar este registro de seguimiento?')) this.api.deleteFollowUp(item.id).subscribe({ next: () => this.loadItems() });
  }
}
