import { Component, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AcademicCatalog, ApiService, FollowUp } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { ConfirmService } from '../../core/services/confirm.service';

@Component({
  standalone: true,
  imports: [DatePipe, FormsModule, PageHeaderComponent],
  template: `
    <app-page-header title="Seguimiento académico" description="Registra observaciones, acuerdos y acciones por estudiante." />
    <fieldset class="panel filters" [disabled]="saving()">
      <label>Nivel<select [(ngModel)]="level" (ngModelChange)="gradeId = ''; sectionId = ''; loadCatalog()"><option value="">Seleccionar nivel</option>@for (item of levels(); track item) {<option [value]="item">{{ item }}</option>}</select></label>
      <label>Grado<select [(ngModel)]="gradeId" (ngModelChange)="sectionId = ''; loadCatalog()" [disabled]="!level"><option value="">Seleccionar grado</option>@for (grade of gradesForLevel(); track grade.id) {<option [value]="grade.id">{{ grade.name }}</option>}</select></label>
      <label>Sección<select [(ngModel)]="sectionId" (ngModelChange)="studentId = ''; loadCatalog()" [disabled]="!gradeId"><option value="">Seleccionar sección</option>@for (section of sectionsForGrade(); track section.id) {<option [value]="section.id">{{ gradeName(section.grade_id) }} · {{ section.name }}</option>}</select></label>
    </fieldset>
    @if (!sectionId) {
      <p class="panel">Selecciona el grado y la sección para consultar el historial de su grupo.</p>
    } @else {
      <section class="panel">
        <label>Estudiante<select [(ngModel)]="studentId" [disabled]="!!editingId || saving() || loading()"><option value="">Seleccionar estudiante</option>@for (student of catalog().students; track student.id) {<option [value]="student.id">{{ student.name }}</option>}</select></label>
        <label>Tipo<select [(ngModel)]="category" [disabled]="saving()"><option value="OBSERVATION">Observación</option><option value="PEDAGOGICAL_AGREEMENT">Acuerdo pedagógico</option><option value="MEETING">Reunión o interacción</option><option value="ACTION">Acción realizada</option></select></label>
        <label>Descripción<textarea [(ngModel)]="action" [disabled]="saving()" placeholder="Describe el hecho, acuerdo o siguiente acción..."></textarea></label>
        <button type="button" (click)="save()" [disabled]="saving() || loading() || loadError()">{{ editingId ? 'Guardar cambios' : 'Registrar seguimiento' }}</button>
        @if (editingId) { <button type="button" class="muted" (click)="reset()">Cancelar</button> }
        @if (message()) { <p role="status">{{ message() }}</p> }
        @if (error()) { <p class="error" role="alert">{{ error() }}</p> }
      </section>
      <section class="panel">
        <h2>Historial del grupo</h2>
        @if (loading()) { <p role="status">Cargando historial…</p> }
        @else if (loadError()) { <p class="error" role="alert">No se pudo consultar el historial.</p><button type="button" (click)="loadCatalog()">Reintentar historial</button> }
        @else if (!items().length) { <p>Aún no hay seguimientos para esta sección.</p> }
        @for (item of items(); track item.id) {
          <article>
            <div><strong>{{ studentName(item.student_id) }}</strong><span>{{ categoryName(item.category) }} · {{ item.status === 'CLOSED' ? 'Cerrado' : item.status === 'OPEN' ? 'Abierto' : item.status }}</span></div>
            <p class="metadata"><time [attr.datetime]="item.created_at">{{ item.created_at ? (item.created_at | date:'dd/MM/yyyy HH:mm') : 'Fecha no registrada' }}</time> · {{ item.recorded_by_name ?? 'Autor no registrado' }}</p>
            <p>{{ item.action }}</p>
            @if (canEdit) { <footer class="actions-cell"><button type="button" class="icon-action" [disabled]="saving()" (click)="edit(item)" title="Editar seguimiento" aria-label="Editar seguimiento"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 16.5-.8 4.3 4.3-.8L20 7.5 16.5 4 4 16.5Z"/><path d="m14.8 5.7 3.5 3.5"/></svg></button><button type="button" class="icon-action danger-icon" [disabled]="saving()" (click)="remove(item)" title="Eliminar seguimiento" aria-label="Eliminar seguimiento"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6"/></svg></button></footer> }
          </article>
        }
      </section>
    }
  `,
  styles: [`
    .panel{background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;padding:22px;margin:0 0 18px;min-width:0}
    .filters{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
    label{display:grid;gap:7px;color:var(--color-muted-text);margin-bottom:14px}
    select,textarea{padding:10px;border:1px solid var(--color-border);border-radius:6px;font:inherit}
    textarea{min-height:90px;resize:vertical}
    button{background:var(--color-primary);color:white;border:0;border-radius:6px;padding:10px 14px;cursor:pointer;margin-right:7px}footer{display:flex;gap:6px}
    .muted{background:var(--color-muted-text)} article{border-top:1px solid var(--color-border);padding:14px 0}
    article div{display:flex;justify-content:space-between;gap:10px} span{color:var(--color-muted-text)} footer{display:flex;gap:6px}
    .danger{background:#b94b3b}.metadata{font-size:.88rem;color:var(--color-muted-text)}.error{color:#a33a32}
    @media(max-width:700px){.filters{grid-template-columns:1fr}article div{display:grid}}
  `],
})
export class PlaceholderPage {
  private readonly api = inject(ApiService);
  private readonly confirm = inject(ConfirmService);
  protected readonly catalog = signal<AcademicCatalog>({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] });
  protected readonly items = signal<FollowUp[]>([]);
  protected readonly message = signal('');
  protected readonly error = signal('');
  protected readonly loading = signal(false);
  protected readonly loadError = signal(false);
  protected readonly saving = signal(false);
  protected readonly canEdit = (() => { try { return ['coordinator', 'director'].includes(JSON.parse(localStorage.getItem('paideia_user') ?? '{}').role); } catch { return false; } })();
  protected level = '';
  protected gradeId = '';
  protected sectionId = '';
  protected studentId = '';
  protected category = 'OBSERVATION';
  protected action = '';
  protected editingId: string | null = null;
  private editingStatus = 'OPEN';
  private catalogRequest = 0;
  private itemsRequest = 0;
  private groupKey = '';

  constructor() { this.loadCatalog(); }
  protected levels(): string[] { return [...new Set(this.catalog().grades.map((item) => item.level))]; }
  protected gradesForLevel() { return this.catalog().grades.filter((item) => item.level === this.level); }
  protected sectionsForGrade() { return this.catalog().sections.filter((item) => item.grade_id === this.gradeId); }
  protected gradeName(id: string) { return this.catalog().grades.find((item) => item.id === id)?.name ?? ''; }

  protected loadCatalog(): void {
    const key = this.gradeId + ':' + this.sectionId;
    if (key !== this.groupKey) { this.groupKey = key; this.reset(); this.items.set([]); this.message.set(''); this.error.set(''); }
    const request = ++this.catalogRequest;
    ++this.itemsRequest;
    this.loading.set(true); this.loadError.set(false);
    const filters: Record<string, string> = {};
    if (this.gradeId) filters['grade_id'] = this.gradeId;
    if (this.sectionId) filters['section_id'] = this.sectionId;
    this.api.getAcademicCatalog(filters).subscribe({
      next: (catalog) => {
        if (request !== this.catalogRequest) return;
        this.catalog.set(catalog);
        if (this.sectionId) this.loadItems(); else { this.items.set([]); this.loading.set(false); }
      },
      error: () => { if (request === this.catalogRequest) { this.loading.set(false); this.loadError.set(true); } },
    });
  }

  private loadItems(): void {
    const request = ++this.itemsRequest;
    this.loading.set(true); this.loadError.set(false); this.items.set([]);
    this.api.listFollowUps({ grade_id: this.gradeId, section_id: this.sectionId }).subscribe({
      next: (items) => { if (request === this.itemsRequest) { this.items.set(items); this.loading.set(false); } },
      error: () => { if (request === this.itemsRequest) { this.loading.set(false); this.loadError.set(true); } },
    });
  }

  protected studentName(id: string): string { return this.catalog().students.find((student) => student.id === id)?.name ?? id; }
  protected categoryName(category: string): string { return ({ OBSERVATION: 'Observación', PEDAGOGICAL_AGREEMENT: 'Acuerdo pedagógico', MEETING: 'Reunión', ACTION: 'Acción realizada' } as Record<string, string>)[category] ?? category; }
  protected edit(item: FollowUp): void { if (!this.canEdit || this.saving()) return; this.editingId = item.id; this.editingStatus = item.status; this.studentId = item.student_id; this.category = item.category; this.action = item.action; }
  protected reset(): void { this.editingId = null; this.editingStatus = 'OPEN'; this.studentId = ''; this.category = 'OBSERVATION'; this.action = ''; }

  protected save(): void {
    if (this.saving() || this.loading() || this.loadError()) return;
    if (!this.sectionId || !this.studentId || this.action.trim().length < 3) { this.message.set('Selecciona un estudiante e ingresa una descripción de al menos 3 caracteres.'); return; }
    const payload = { student_id: this.studentId, category: this.category, action: this.action.trim(), status: this.editingId ? this.editingStatus : 'OPEN' };
    const request = this.editingId ? this.api.updateFollowUp(this.editingId, payload) : this.api.createFollowUp(payload);
    this.saving.set(true); this.error.set('');
    request.subscribe({ next: () => { this.saving.set(false); this.message.set('Seguimiento guardado.'); this.reset(); this.loadItems(); }, error: (failure) => { this.saving.set(false); const detail = failure.error?.detail; this.error.set(typeof detail === 'string' ? detail : 'No se pudo guardar el seguimiento.'); } });
  }

  protected async remove(item: FollowUp): Promise<void> {
    if (!this.canEdit || this.saving()) return;
    if (await this.confirm.ask('¿Eliminar este registro de seguimiento?')) this.api.deleteFollowUp(item.id).subscribe({ next: () => this.loadItems() });
  }
}
