import { Component, EventEmitter, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AcademicPeriod, ApiService, PeriodPayload } from '../../core/services/api.service';

@Component({
  standalone: true,
  selector: 'app-period-manager',
  imports: [FormsModule],
  template: `
    <section class="panel" aria-label="Gestión de periodos">
      <h2>Periodos académicos</h2>
      <p>Define el calendario sin cambiar las identidades ni las notas registradas.</p>
      <form (ngSubmit)="save()">
        <div class="fields">
          <label>Nombre del periodo<input name="period_name" [(ngModel)]="form.name" maxlength="100" required /></label>
          <label>Inicio del periodo<input name="period_start" type="date" [(ngModel)]="form.starts_on" required /></label>
          <label>Fin del periodo<input name="period_end" type="date" [(ngModel)]="form.ends_on" required /></label>
        </div>
        <button type="submit" class="primary" [disabled]="saving()">{{ editingId ? 'Guardar periodo' : 'Crear periodo' }}</button>
        @if (editingId) { <button type="button" class="secondary" [disabled]="saving()" (click)="reset()">Cancelar edición de periodo</button> }
      </form>
      @if (error()) { <p role="alert">{{ error() }}</p> }
      @if (message()) { <p role="status">{{ message() }}</p> }
      @if (loading()) { <p role="status">Cargando periodos...</p> }
      @else if (loadError()) { <p role="alert">No se pudieron cargar los periodos.</p><button type="button" class="primary" (click)="load()">Reintentar periodos</button> }
      @else if (!periods().length) { <p>Aún no hay periodos registrados.</p> }
      @else {
        <div class="table-wrap"><table>
          <thead><tr><th>Periodo</th><th>Inicio</th><th>Fin</th><th>Acciones</th></tr></thead>
          <tbody>@for (period of periods(); track period.id) {
            <tr><td>{{ period.name }}</td><td>{{ period.starts_on }}</td><td>{{ period.ends_on }}</td>
              <td class="actions-cell"><button type="button" class="icon-action" [disabled]="saving()" (click)="edit(period)" [attr.aria-label]="'Editar periodo ' + period.name" title="Editar periodo"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 16.5-.8 4.3 4.3-.8L20 7.5 16.5 4 4 16.5Z"/><path d="m14.8 5.7 3.5 3.5"/></svg></button></td></tr>
          }</tbody>
        </table></div>
      }
    </section>
  `,
  styles: [`
    .panel{background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;padding:22px;margin-bottom:18px}
    .fields{display:grid;grid-template-columns:2fr 1fr 1fr;gap:12px}label{display:grid;gap:6px}
    input{padding:10px;font:inherit;border:1px solid var(--color-border);border-radius:6px;min-width:0}
    button{margin:12px 8px 0 0;padding:9px 12px;cursor:pointer;border:1px solid transparent;border-radius:7px}.primary{background:var(--color-primary);color:white}.primary:hover{background:var(--color-primary-dark)}.secondary{background:var(--color-surface);border-color:var(--color-primary);color:var(--color-primary-dark)}button:disabled{cursor:wait}
    .table-wrap{overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid var(--color-border);text-align:left}
    [role=alert]{color:#a33a32}[role=status]{color:var(--color-primary)}h2{font-size:1.2rem}
    @media(max-width:700px){.fields{grid-template-columns:1fr}}
  `],
})
export class PeriodManagerComponent {
  private readonly api = inject(ApiService);
  @Output() readonly periodsChanged = new EventEmitter<void>();
  protected readonly periods = signal<AcademicPeriod[]>([]);
  protected readonly loading = signal(false);
  protected readonly loadError = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly message = signal('');
  protected editingId: string | null = null;
  protected form: PeriodPayload = { name: '', starts_on: '', ends_on: '' };

  constructor() { this.load(); }
  protected load(): void {
    this.loading.set(true); this.loadError.set(false);
    this.api.listPeriods().subscribe({ next: (periods) => { this.periods.set(periods); this.loading.set(false); }, error: () => { this.loading.set(false); this.loadError.set(true); } });
  }
  protected edit(period: AcademicPeriod): void {
    if (this.saving()) return;
    this.editingId = period.id; this.form = { name: period.name, starts_on: period.starts_on, ends_on: period.ends_on };
    this.error.set(''); this.message.set('');
  }
  protected reset(): void { this.editingId = null; this.form = { name: '', starts_on: '', ends_on: '' }; }
  protected save(): void {
    if (this.saving()) return;
    const payload = { ...this.form, name: this.form.name.trim() };
    this.error.set(''); this.message.set('');
    if (!payload.name || !payload.starts_on || !payload.ends_on || payload.starts_on > payload.ends_on) {
      this.error.set('Completa el nombre y selecciona inicio y fin en orden cronológico.'); return;
    }
    this.saving.set(true);
    const request = this.editingId ? this.api.updatePeriod(this.editingId, payload) : this.api.createPeriod(payload);
    request.subscribe({ next: () => {
      this.saving.set(false); this.reset(); this.message.set('Periodo guardado.'); this.load(); this.periodsChanged.emit();
    }, error: (response: { error?: { detail?: unknown } }) => {
      this.saving.set(false); const detail = response.error?.detail;
      this.error.set(typeof detail === 'string' ? detail : 'No se pudo guardar el periodo. Revisa sus datos.');
    } });
  }
}
