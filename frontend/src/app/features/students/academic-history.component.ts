import { DatePipe } from '@angular/common';
import { Component, Input, OnChanges, inject, signal } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { roleLabels } from '../../core/module-access';

export interface AcademicChange {
  id: string; entity: string; record_id: string; operation: string;
  actor_id: string | null; actor_role: string | null; source: string; created_at: string;
  before: Record<string, unknown> | null; after: Record<string, unknown> | null;
}

@Component({
  selector: 'app-academic-history', standalone: true, imports: [DatePipe],
  template: `
    <h3>Historial de cambios académicos</h3>
    <p>Consulta los cambios registrados en las notas y la asistencia del estudiante.</p>
    @if (loading()) {<p role="status">Cargando historial…</p>}
    @if (error()) {<p role="alert">{{ error() }} <button (click)="load()">Reintentar historial</button></p>}
    @for (change of rows(); track change.id) {
      <article><strong>{{ entityLabel(change.entity) }} · {{ operationLabel(change.operation) }}</strong>
        <p>{{ change.created_at | date:'dd/MM/yyyy HH:mm' }} · {{ roleName(change.actor_role) }}</p>
        <details><summary>Ver cambios</summary><table><thead><tr><th>Dato</th><th>Antes</th><th>Después</th></tr></thead><tbody>@for (field of changedFields(change); track field.key) {<tr><td>{{ field.label }}</td><td>{{ field.before }}</td><td>{{ field.after }}</td></tr>}</tbody></table></details>
      </article>
    } @empty { @if (!loading() && !error()) {<p>No hay cambios registrados en esta página.</p>} }
    <nav aria-label="Paginación de historial"><button (click)="page(-1)" [disabled]="loading() || offset === 0">Anteriores</button><span>Página {{ offset / 50 + 1 }}</span><button (click)="page(1)" [disabled]="loading() || rows().length < 50">Siguientes</button><button (click)="load()" [disabled]="loading()">Actualizar historial</button></nav>
  `,
  styles: [`:host{display:block;margin-top:20px}article{border-top:1px solid var(--color-border);padding:12px 0}details{overflow:auto}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--color-border)}nav{display:flex;gap:10px;align-items:center;flex-wrap:wrap}button{padding:8px 12px;font:inherit;cursor:pointer;border:1px solid var(--color-border);border-radius:7px;background:white;color:var(--color-text)}`],
})
export class AcademicHistoryComponent implements OnChanges {
  @Input({ required: true }) studentId = '';
  private readonly api = inject(ApiService);
  protected readonly rows = signal<AcademicChange[]>([]);
  protected readonly loading = signal(false);
  protected readonly error = signal('');
  protected offset = 0;
  private request = 0;
  ngOnChanges() { this.offset = 0; this.rows.set([]); this.load(); }
  protected load() {
    const request = ++this.request;
    if (!this.studentId) { this.rows.set([]); this.loading.set(false); this.error.set(''); return; }
    this.loading.set(true); this.error.set('');
    this.api.getAcademicHistory<AcademicChange[]>(this.studentId, this.offset).subscribe({
      next: rows => { if (request === this.request) { this.rows.set(rows); this.loading.set(false); } },
      error: () => { if (request === this.request) { this.rows.set([]); this.loading.set(false); this.error.set('No se pudo consultar el historial autorizado.'); } },
    });
  }
  protected page(direction: number) { this.offset = Math.max(0, this.offset + direction * 50); this.load(); }
  protected entityLabel(value: string) { return ({ grade_records: 'Nota', attendance_records: 'Asistencia', follow_ups: 'Seguimiento' } as Record<string,string>)[value] || value; }
  protected operationLabel(value: string) { return ({ INSERT: 'Registro', UPDATE: 'Corrección', DELETE: 'Eliminación' } as Record<string,string>)[value] || value; }
  protected roleName(value: string | null) { return roleLabels[value ?? ''] ?? 'Registro del sistema'; }
  protected changedFields(change: AcademicChange) {
    const labels: Record<string, string> = { score: 'Nota', evaluation_name: 'Evaluación', evaluation_type: 'Criterio', assessment_date: 'Fecha de evaluación', qualitative_note: 'Observación', assessment_weight: 'Peso', attendance_date: 'Fecha de asistencia', status: 'Estado', remarks: 'Observación', category: 'Tipo de seguimiento', action: 'Descripción', academic_bimester: 'Bimestre', evaluation_block: 'Bloque' };
    const values: Record<string, string> = { PRESENT: 'Presente', ABSENT: 'Falta', LATE: 'Tardanza', OPEN: 'Abierto', CLOSED: 'Cerrado', OBSERVATION: 'Observación', PEDAGOGICAL_AGREEMENT: 'Acuerdo pedagógico', MEETING: 'Reunión', ACTION: 'Acción' };
    const display = (value: unknown) => value === null || value === undefined || value === '' ? '—' : values[String(value)] ?? String(value);
    return Object.entries(labels).filter(([key]) => change.before?.[key] !== change.after?.[key])
      .map(([key, label]) => ({ key, label, before: display(change.before?.[key]), after: display(change.after?.[key]) }));
  }
}
