import { Component, Input, OnChanges, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';
import { AcademicCatalog, ApiService, Enrollment, Student } from '../../core/services/api.service';

@Component({
  standalone: true,
  selector: 'app-enrollment-manager',
  imports: [FormsModule],
  template: `
    <section aria-label="Matrículas académicas"><h3>Matrículas académicas</h3>
      @if (loading()) { <p role="status">Cargando matrículas…</p> }
      @if (loadError()) { <p role="alert">No se pudieron consultar las matrículas.</p><button type="button" (click)="ngOnChanges()">Reintentar matrículas</button> }
      @if (canCreate) {
        <form (ngSubmit)="save()"><fieldset [disabled]="loading() || saving() || loadError()">
          <label>Curso de matrícula<select name="enrollment_course" [(ngModel)]="courseId" required><option value="">Seleccionar curso</option>@for (course of catalog()?.courses ?? []; track course.id) {<option [value]="course.id">{{ course.name }}</option>}</select></label>
          <label>Periodo de matrícula<select name="enrollment_period" [(ngModel)]="periodId" required><option value="">Seleccionar periodo</option>@for (period of catalog()?.periods ?? []; track period.id) {<option [value]="period.id">{{ period.name }}</option>}</select></label>
          <button type="submit" [disabled]="!courseId || !periodId || exists()">{{ saving() ? 'Registrando…' : 'Registrar matrícula académica' }}</button>
        </fieldset></form>
        @if (exists()) { <p>Ya existe una matrícula para este curso y periodo.</p> }
      }
      @if (error()) { <p role="alert">{{ error() }}</p> }
      @if (message()) { <p role="status">{{ message() }}</p> }
      @if (!loading() && !loadError()) {
        <div class="table-wrap"><table><thead><tr><th>Curso</th><th>Periodo</th><th>Estado</th></tr></thead><tbody>
          @for (record of records(); track record.id) { <tr><td>{{ courseLabel(record.course_id) }}</td><td>{{ periodLabel(record.period_id) }}</td><td>{{ record.status === 'ACTIVE' ? 'Activa' : record.status }}</td></tr> }
          @empty { <tr><td colspan="3">Sin matrículas académicas registradas.</td></tr> }
        </tbody></table></div>
      }
    </section>
  `,
  styles: [`
    section{border-top:1px solid var(--color-border);padding-top:16px;margin-top:18px}fieldset{border:0;padding:0;display:flex;align-items:end;gap:12px;flex-wrap:wrap}
    label{display:grid;gap:6px;flex:1 1 180px}select{padding:10px;font:inherit;border:1px solid var(--color-border);border-radius:6px;min-width:0}
    button{padding:10px 14px;border:0;border-radius:5px;background:var(--color-primary);color:white;cursor:pointer}button:disabled{opacity:.6;cursor:default}
    .table-wrap{overflow:auto;margin-top:16px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--color-border)}
    [role=alert]{color:#a33a32}h3{font-size:1.1rem}
  `],
})
export class EnrollmentManagerComponent implements OnChanges {
  @Input({ required: true }) student!: Student;
  private readonly api = inject(ApiService);
  protected readonly records = signal<Enrollment[]>([]);
  protected readonly catalog = signal<AcademicCatalog | null>(null);
  private courseNames: Record<string, string> = {};
  protected readonly loading = signal(false);
  protected readonly loadError = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly message = signal('');
  protected courseId = ''; protected periodId = '';
  private request = 0;
  protected readonly canCreate = (() => { try { return JSON.parse(localStorage.getItem('paideia_user') ?? '{}').role === 'admin'; } catch { return false; } })();
  ngOnChanges() {
    const request = ++this.request;
    this.courseId = ''; this.periodId = ''; this.records.set([]); this.catalog.set(null);
    this.loading.set(true); this.loadError.set(false); this.error.set(''); this.message.set(''); this.saving.set(false);
    const filters: Record<string, string> = {};
    if (this.student.grade_id) filters['grade_id'] = this.student.grade_id;
    if (this.student.section_id) filters['section_id'] = this.student.section_id;
    forkJoin({ catalog: this.api.getAcademicCatalog(filters), courses: this.api.listCourses(), records: this.api.listEnrollments({ student_id: this.student.id }) }).subscribe({
      next: (result) => { if (request !== this.request) return; this.catalog.set(result.catalog); this.courseNames = Object.fromEntries(result.courses.map(course => [course.id, course.name])); this.records.set(result.records); this.loading.set(false); },
      error: () => { if (request !== this.request) return; this.loading.set(false); this.loadError.set(true); },
    });
  }
  protected exists() { return this.records().some(row => row.course_id === this.courseId && row.period_id === this.periodId); }
  protected courseLabel(id: string) { return this.courseNames[id] ?? 'Curso no disponible'; }
  protected periodLabel(id: string) { return this.catalog()?.periods.find(row => row.id === id)?.name ?? 'Periodo no disponible'; }
  protected save() {
    if (!this.canCreate || this.loading() || this.saving() || this.loadError() || this.exists()) return;
    if (!this.courseId || !this.periodId) { this.error.set('Selecciona curso y periodo.'); return; }
    const request = this.request;
    const payload = { student_id: this.student.id, course_id: this.courseId, period_id: this.periodId };
    this.saving.set(true); this.error.set(''); this.message.set('');
    this.api.createEnrollment(payload).pipe(finalize(() => { if (request === this.request) this.saving.set(false); })).subscribe({
      next: (record) => { if (request !== this.request) return; this.records.update(rows => [record, ...rows]); this.message.set('Matrícula académica registrada.'); },
      error: (failure) => { if (request !== this.request) return; const detail = failure.error?.detail; this.error.set(typeof detail === 'string' ? detail : 'No se pudo registrar la matrícula. Consulta de nuevo antes de reintentar.'); },
    });
  }
}
