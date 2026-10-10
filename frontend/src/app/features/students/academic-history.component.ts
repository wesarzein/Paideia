import { DatePipe, JsonPipe } from '@angular/common';
import { Component, Input, OnChanges, inject, signal } from '@angular/core';
import { ApiService } from '../../core/services/api.service';

export interface AcademicChange {
  id: string; entity: string; record_id: string; operation: string;
  actor_id: string | null; actor_role: string | null; source: string; created_at: string;
  before: Record<string, unknown> | null; after: Record<string, unknown> | null;
}

@Component({
  selector: 'app-academic-history', standalone: true, imports: [DatePipe, JsonPipe],
  template: `
    <h3>Historial de cambios académicos</h3>
    <p>Versiones conservadas desde la habilitación de auditoría. Las notas anteriores mantienen sus snapshots; no se reconstruyen cambios que no fueron registrados.</p>
    @if (loading()) {<p role="status">Cargando historial…</p>}
    @if (error()) {<p role="alert">{{ error() }} <button (click)="load()">Reintentar historial</button></p>}
    @for (change of rows(); track change.id) {
      <article><strong>{{ entityLabel(change.entity) }} · {{ operationLabel(change.operation) }}</strong>
        <p>{{ change.created_at | date:'medium' }} · {{ change.actor_role || 'Proceso de base' }} {{ change.actor_id?.slice(0,8) || 'sin usuario API' }} · Registro {{ change.record_id.slice(0,8) }}</p>
        <details><summary>Valores anteriores y posteriores</summary><h4>Antes</h4><pre>{{ change.before | json }}</pre><h4>Después</h4><pre>{{ change.after | json }}</pre></details>
      </article>
    } @empty { @if (!loading() && !error()) {<p>No hay cambios registrados en esta página.</p>} }
    <nav aria-label="Paginación de historial"><button (click)="page(-1)" [disabled]="loading() || offset === 0">Anteriores</button><span>Página {{ offset / 50 + 1 }}</span><button (click)="page(1)" [disabled]="loading() || rows().length < 50">Siguientes</button><button (click)="load()" [disabled]="loading()">Actualizar historial</button></nav>
  `,
  styles: [`:host{display:block;margin-top:20px}article{border-top:1px solid var(--color-border);padding:12px 0}pre{overflow:auto;max-height:280px;font-size:.8rem}nav{display:flex;gap:10px;align-items:center;flex-wrap:wrap}button{padding:8px;font:inherit;cursor:pointer}`],
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
  protected operationLabel(value: string) { return ({ INSERT: 'Registro', UPDATE: 'Corrección', DELETE: 'Retiro del registro operativo; historia conservada' } as Record<string,string>)[value] || value; }
}
