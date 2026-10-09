import { Component, EventEmitter, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, forkJoin, Observable } from 'rxjs';
import { AcademicGrade, AcademicSection, ApiService } from '../../core/services/api.service';

@Component({
  standalone: true,
  selector: 'app-cohort-manager',
  imports: [FormsModule],
  template: `
    <details class="panel"><summary>Grados y secciones</summary>
      <p>Los cambios de etiqueta conservan los códigos escolares. Crea un grado o una sección nuevos para una identidad diferente.</p>
      @if (loading()) { <p role="status">Cargando catálogo…</p> }
      @if (loadError()) { <p role="alert">No se pudo cargar el catálogo.</p><button (click)="load()" type="button">Reintentar catálogo</button> }
      <fieldset [disabled]="saving() || loading() || loadError()">
        <form (ngSubmit)="saveGrade()"><h2>{{ gradeId ? 'Editar etiqueta de grado' : 'Nuevo grado' }}</h2>
          <div class="fields"><label>Nombre del grado<input name="grade_name" [(ngModel)]="gradeName" maxlength="80" required /></label>
            <label>Nivel del grado<select name="grade_level" [(ngModel)]="gradeLevel" [disabled]="!!gradeId"><option value="Primaria">Primaria</option><option value="Secundaria">Secundaria</option></select></label></div>
          <button type="submit">{{ gradeId ? 'Guardar etiqueta de grado' : 'Crear grado' }}</button>
          @if (gradeId) { <button type="button" (click)="resetGrade()">Cancelar grado</button> }
        </form>
        <form (ngSubmit)="saveSection()"><h2>{{ sectionId ? 'Editar etiqueta de sección' : 'Nueva sección' }}</h2>
          <div class="fields"><label>Grado de la sección<select name="section_grade" [(ngModel)]="sectionGrade" [disabled]="!!sectionId" required><option value="">Seleccionar grado</option>@for (grade of grades(); track grade.id) {@if (grade.is_active) {<option [value]="grade.id">{{ grade.name }} · {{ grade.level }}</option>}}</select></label>
            <label>Nombre de la sección<input name="section_name" [(ngModel)]="sectionName" maxlength="20" required /></label></div>
          <button type="submit">{{ sectionId ? 'Guardar etiqueta de sección' : 'Crear sección' }}</button>
          @if (sectionId) { <button type="button" (click)="resetSection()">Cancelar sección</button> }
        </form>
        <div class="table-wrap"><table><thead><tr><th>Grado</th><th>Nivel</th><th>Acciones</th></tr></thead><tbody>
          @for (grade of grades(); track grade.id) { <tr><td>{{ grade.name }}</td><td>{{ grade.level }}</td><td><button type="button" (click)="editGrade(grade)" [attr.aria-label]="'Editar grado ' + grade.name + ' ' + grade.level">Editar grado</button></td></tr> }
          @empty { <tr><td colspan="3">Sin grados registrados.</td></tr> }
        </tbody></table></div>
        <div class="table-wrap"><table><thead><tr><th>Sección</th><th>Grado</th><th>Acciones</th></tr></thead><tbody>
          @for (section of sections(); track section.id) { <tr><td>{{ section.name }}</td><td>{{ gradeLabel(section.grade_id) }}</td><td><button type="button" (click)="editSection(section)" [attr.aria-label]="'Editar sección ' + section.name + ' ' + gradeLabel(section.grade_id)">Editar sección</button></td></tr> }
          @empty { <tr><td colspan="3">Sin secciones registradas.</td></tr> }
        </tbody></table></div>
      </fieldset>
      @if (error()) { <p role="alert">{{ error() }}</p> }
      @if (message()) { <p role="status">{{ message() }}</p> }
    </details>
  `,
  styles: [`
    .panel{display:block;background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;padding:22px;margin-bottom:18px}
    summary{cursor:pointer;font-weight:600}fieldset{border:0;padding:0;min-width:0}.fields{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    label{display:grid;gap:6px}input,select{min-width:0;padding:10px;font:inherit;border:1px solid var(--color-border);border-radius:6px}
    button{margin:12px 8px 8px 0;padding:9px 12px;cursor:pointer}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse}
    th,td{padding:10px;border-bottom:1px solid var(--color-border);text-align:left}[role=alert]{color:#a33a32}h2{font-size:1.1rem}
    @media(max-width:700px){.fields{grid-template-columns:1fr}}
  `],
})
export class CohortManagerComponent {
  private readonly api = inject(ApiService);
  @Output() readonly catalogChanged = new EventEmitter<void>();
  protected readonly grades = signal<AcademicGrade[]>([]);
  protected readonly sections = signal<AcademicSection[]>([]);
  protected readonly loading = signal(false);
  protected readonly loadError = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly message = signal('');
  protected gradeId = ''; protected gradeName = ''; protected gradeLevel = 'Primaria';
  protected sectionId = ''; protected sectionName = ''; protected sectionGrade = '';
  constructor() { this.load(); }
  protected load() {
    this.loading.set(true); this.loadError.set(false);
    forkJoin({ grades: this.api.listAcademicGrades(), sections: this.api.listAcademicSections() }).subscribe({
      next: (catalog) => { this.grades.set(catalog.grades); this.sections.set(catalog.sections); this.loading.set(false); },
      error: () => { this.loading.set(false); this.loadError.set(true); },
    });
  }
  protected gradeLabel(id: string) { const grade = this.grades().find(item => item.id === id); return grade ? `${grade.name} · ${grade.level}` : ''; }
  protected editGrade(grade: AcademicGrade) { this.gradeId = grade.id; this.gradeName = grade.name; this.gradeLevel = grade.level; this.error.set(''); this.message.set(''); }
  protected editSection(section: AcademicSection) { this.sectionId = section.id; this.sectionName = section.name; this.sectionGrade = section.grade_id; this.error.set(''); this.message.set(''); }
  protected resetGrade() { this.gradeId = ''; this.gradeName = ''; this.gradeLevel = 'Primaria'; }
  protected resetSection() { this.sectionId = ''; this.sectionName = ''; this.sectionGrade = ''; }
  protected saveGrade() {
    if (this.saving() || this.loading() || this.loadError()) return;
    const name = this.gradeName.trim();
    if (!name) { this.error.set('Completa el nombre del grado.'); return; }
    const request = this.gradeId ? this.api.updateAcademicGrade(this.gradeId, name) : this.api.createAcademicGrade({ name, level: this.gradeLevel });
    this.submit(request, () => this.resetGrade());
  }
  protected saveSection() {
    if (this.saving() || this.loading() || this.loadError()) return;
    const name = this.sectionName.trim();
    if (!name || !this.sectionGrade) { this.error.set('Completa el grado y nombre de la sección.'); return; }
    const request = this.sectionId ? this.api.updateAcademicSection(this.sectionId, name) : this.api.createAcademicSection({ name, grade_id: this.sectionGrade });
    this.submit(request, () => this.resetSection());
  }
  private submit(request: Observable<unknown>, reset: () => void) {
    this.error.set(''); this.message.set(''); this.saving.set(true);
    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: () => { reset(); this.message.set('Catálogo guardado.'); this.load(); this.catalogChanged.emit(); },
      error: (failure) => { const detail = failure.error?.detail; this.error.set(typeof detail === 'string' ? detail : 'No se pudo guardar. Revisa los datos del catálogo.'); },
    });
  }
}
