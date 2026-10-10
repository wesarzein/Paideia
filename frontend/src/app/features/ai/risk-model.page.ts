import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Observable, Subscription } from 'rxjs';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { ModelRun, ModelStatus, Predictions, RiskModelService } from './risk-model.service';

@Component({
  standalone: true,
  imports: [FormsModule, DatePipe, DecimalPipe, PageHeaderComponent],
  template: `
    <app-page-header title="IA experimental local" description="Apoyo demostrativo para revisión pedagógica; sin decisiones automáticas." />
    <section class="banner"><h2>DEMOSTRACIÓN · Datos completamente ficticios</h2><p>Los resultados y métricas sintéticos no acreditan eficacia institucional. IA institucional INACTIVA: requiere historia autorizada, política confirmada, evaluación y aprobación. Riesgo de deserción no habilitado.</p></section>
    @if (error()) {<p role="alert">{{ error() }} <button (click)="load()">Reintentar</button></p>}
    @if (loading()) {<p role="status">Consultando modelos…</p>}
    @if (status(); as s) {
      <section class="panel"><h2>Estado del modelo demostrativo</h2><p>{{ s.active_run_id ? 'Modelo aprobado activo para demostración' : 'Sin modelo activo' }} · Versión de activación {{ s.deployment_version }}</p><button (click)="load()" [disabled]="busy()">Actualizar estado</button>
        @if (admin) {<form (ngSubmit)="train()"><h3>Entrenamiento bajo demanda</h3><div class="controls"><label>Semilla<input name="seed" type="number" min="0" [(ngModel)]="seed" /></label><label>Estudiantes ficticios<input name="pupils" type="number" min="80" max="200" [(ngModel)]="pupils" /></label><label>Corte experimental de desaprobación ≤<input name="cutoff" type="number" min="0" max="20" step="0.1" [(ngModel)]="cutoff" /></label></div><p>Objetivo: promedio de referencia del periodo siguiente. Predictores solo de periodos previos; umbrales 0,3/0,7 exclusivamente demostrativos.</p><label class="ack"><input name="ack" type="checkbox" [(ngModel)]="ack" /> Reconozco que son datos ficticios y resultados experimentales sin uso institucional.</label><button [disabled]="busy() || !ack || pending()">Solicitar entrenamiento demostrativo</button></form>
          @if (!s.autorun) {<p>Procesamiento automático deshabilitado. Un operador debe ejecutar el worker bajo demanda; la solicitud queda en cola.</p>}
          <label>Motivo de revisión / activación<input maxlength="500" [(ngModel)]="reason" placeholder="Revisión experimental de métricas y limitaciones" /></label>
          @if (s.active_run_id) {<button (click)="activate(null)" [disabled]="busy() || !ack || reason.trim().length < 5">Desactivar demostración</button>}
        }
      </section>
      <section class="panel"><h2>Historial de entrenamiento y comparación</h2>@if (!s.runs.length) {<p>No se han entrenado modelos. No hay predicciones disponibles.</p>}
        @for (r of s.runs; track r.id) {<article><h3>Modelo {{ r.id.slice(0,8) }} · {{ r.status }}</h3><p>Solicitado {{ r.created_at | date:'short' }} · Semilla {{ r.configuration.seed }} · {{ r.configuration.pupils }} estudiantes ficticios</p>
          @if (r.error_code) {<p role="alert">Entrenamiento fallido: {{ r.error_code }}. El conjunto aislado se conserva para diagnóstico.</p>}
          @if (r.metrics; as m) {<p>Precisión {{ m.precision | number:'1.2-3' }} · Recall {{ m.recall | number:'1.2-3' }} · F1 {{ m.f1 | number:'1.2-3' }} · Brier {{ m.brier_score | number:'1.2-3' }}</p><p>Baseline F1: {{ r.baseline?.f1 | number:'1.2-3' }} · Entrenamiento {{ r.split?.train_count }}, evaluación {{ r.split?.test_count }} · Sin alumnos compartidos.</p><p>Matriz de confusión [real 0/1 × predicho 0/1]: {{ m.confusion_matrix[0] }} / {{ m.confusion_matrix[1] }}</p><p>Limitación: etiquetas ficticias generadas por reglas; no validación institucional.</p>}
          @if (admin && r.status === 'candidate') {<button (click)="approve(r)" [disabled]="busy() || !ack || reason.trim().length < 5">Aprobar solo para demostración</button>}
          @if (admin && r.status === 'approved' && r.id !== s.active_run_id) {<button (click)="activate(r.id)" [disabled]="busy() || !ack || reason.trim().length < 5">Activar / restaurar esta versión</button>}
        </article>}
      </section>
      <section class="panel"><h2>Predicciones ficticias</h2><button (click)="infer()" [disabled]="busy() || !s.active_run_id">Consultar demostración</button>
        @if (predictions(); as p) {<p>Modelo {{ p.run_id?.slice(0,8) }} · {{ p.model_date | date:'short' }} · {{ readyCount() }} de {{ p.rows.length }} casos con historia suficiente.</p><p>Alto/medio/bajo se refieren a probabilidades experimentales. Factores: asociaciones del modelo, no causas demostradas. Periodo objetivo y cobertura se identifican por caso.</p>
          <div class="table"><table><thead><tr><th>Alumno ficticio / curso</th><th>Periodo objetivo</th><th>Historia</th><th>Estado / riesgo</th><th>Probabilidad</th><th>Asociaciones</th></tr></thead><tbody>@for (r of p.rows; track r.student_id + r.course_id) {<tr><td>{{ r.student_id.slice(0,8) }} / {{ r.course_id.slice(0,8) }}</td><td>{{ r.target_period_id.slice(0,8) }}</td><td>{{ r.history_periods }} periodos, {{ r.attendance_count }} asistencias</td><td>{{ r.prediction.risk === null ? 'Historia insuficiente' : riskLabel(r.prediction.risk) }}</td><td>{{ r.prediction.probability === null ? 'No disponible' : (r.prediction.probability * 100 | number:'1.0-1') + '%' }}</td><td>@for (f of r.prediction.factors || []; track f.feature) {<div>{{ f.feature }}: {{ f.association | number:'1.2-2' }}</div>}</td></tr>}</tbody></table></div>}
      </section>
    }
  `,
  styles: [`
    .panel,.banner{background:var(--color-surface);padding:20px;border:1px solid var(--color-border);border-radius:12px;margin-bottom:16px}.banner{border-left:4px solid var(--color-accent)}h2{font-size:1.15rem}h3{font-size:1rem}article{border-top:1px solid var(--color-border);margin-top:16px;padding-top:12px;overflow-wrap:anywhere}.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}label{display:grid;gap:6px;margin:12px 0}.ack{display:flex;align-items:center}button,input{font:inherit;padding:8px;border:1px solid var(--color-border);border-radius:6px;background:var(--color-surface);color:var(--color-text)}button{cursor:pointer;margin-right:8px}button:disabled{opacity:.5;cursor:default}.table{overflow:auto}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--color-border);font-size:.85rem}@media(max-width:700px){.controls{grid-template-columns:1fr}}
  `],
})
export class RiskModelPage {
  private readonly api = inject(RiskModelService);
  private readonly destroy = inject(DestroyRef);
  protected readonly status = signal<ModelStatus | null>(null);
  protected readonly predictions = signal<Predictions | null>(null);
  protected readonly error = signal(''); protected readonly loading = signal(false); protected readonly busy = signal(false);
  protected readonly admin = this.isAdmin();
  protected seed = 42; protected pupils = 80; protected cutoff = 10.4; protected ack = false; protected reason = '';
  private timer: ReturnType<typeof setTimeout> | undefined; private request = 0; private subscription?: Subscription;
  constructor() { this.load(); this.destroy.onDestroy(() => { clearTimeout(this.timer); this.subscription?.unsubscribe(); ++this.request; }); }
  private isAdmin() { try { return JSON.parse(localStorage.getItem('paideia_user') || '{}').role === 'admin'; } catch { return false; } }
  protected pending() { return this.status()?.runs.some(r => ['queued','running'].includes(r.status)) ?? false; }
  protected load() {
    const request = ++this.request; this.loading.set(true); this.error.set(''); clearTimeout(this.timer);
    this.subscription?.unsubscribe();
    this.subscription = this.api.status().subscribe({ next: s => { if (request !== this.request) return; if (s.active_run_id !== this.status()?.active_run_id) this.predictions.set(null); this.status.set(s); this.loading.set(false); if (this.pending()) this.timer = setTimeout(() => this.load(), 4000); }, error: () => { if (request === this.request) { this.loading.set(false); this.error.set('No se pudo consultar el estado de IA.'); } } });
  }
  private action(request: Observable<unknown>) {
    if (this.busy()) return; this.busy.set(true); this.error.set(''); this.predictions.set(null);
    request.subscribe({ next: () => { this.busy.set(false); this.load(); }, error: e => { this.busy.set(false); this.error.set(e.error?.detail || 'No se pudo completar la operación.'); } });
  }
  protected train() { if (!this.admin || !this.ack || this.pending() || this.busy()) return; this.action(this.api.train(this.seed, this.pupils, this.cutoff)); }
  protected approve(run: ModelRun) { if (this.admin && this.ack && this.reason.trim().length >= 5) this.action(this.api.approve(run.id, this.reason.trim())); }
  protected activate(id: string | null) { const state = this.status(); if (state && this.admin && this.ack && this.reason.trim().length >= 5) this.action(this.api.activate(id, state.deployment_version, this.reason.trim())); }
  protected infer() { if (this.busy() || !this.status()?.active_run_id) return; this.busy.set(true); this.error.set(''); this.api.predictions().subscribe({ next: p => { this.predictions.set(p); this.busy.set(false); }, error: () => { this.busy.set(false); this.error.set('Predicciones demostrativas no disponibles.'); } }); }
  protected readyCount() { return this.predictions()?.rows.filter(r => r.prediction.probability !== null).length || 0; }
  protected riskLabel(risk: string) { return ({ high: 'Alto', medium: 'Medio', low: 'Bajo' } as Record<string, string>)[risk] || 'No disponible'; }
}
