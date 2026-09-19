import { Component, OnInit, inject, signal } from '@angular/core';
import { ApiService, DashboardSummary, RiskAlert } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [PageHeaderComponent],
  template: `
    <app-page-header title="Dashboard" description="Vista operativa del avance académico." />
    @if (loading()) {
      <p class="state">Cargando indicadores...</p>
    } @else if (error()) {
      <p class="state error">No se pudieron cargar los indicadores. Verifica que la API esté disponible.</p>
    } @else {
      <section class="metrics" aria-label="Resumen de estudiantes">
        <article><span>Total de estudiantes</span><strong>{{ summary().total_students }}</strong></article>
        <article><span>Promedio general</span><strong>{{ summary().average_score | number:'1.1-1' }}</strong></article>
        <article><span>Asistencia</span><strong>{{ summary().attendance_rate | number:'1.1-1' }}%</strong></article>
      </section>

      <section class="metrics secondary" aria-label="Alertas">
        <article><span>Activos</span><strong>{{ summary().active_students }}</strong></article>
        <article><span>En riesgo</span><strong>{{ summary().at_risk_count }}</strong></article>
        <article><span>Riesgo medio</span><strong>{{ alerts().length }}</strong></article>
      </section>

      <section class="next-step">
        <span class="eyebrow">MVP conectado</span>
        <h2>La base operativa ya está lista</h2>
        <p>La gestión académica consume la API FastAPI y persiste en PostgreSQL. IA y BI quedan preparados para la siguiente iteración.</p>
      </section>

      @if (alerts().length) {
        <section class="alerts">
          <h3>Alertas tempranas</h3>
          <ul>
            @for (alert of alerts(); track alert.student_id) {
              <li>
                <strong>{{ alert.student_name }}</strong>
                <span>{{ alert.risk_level }}</span>
                <em>Promedio {{ alert.average_score | number:'1.1-1' }} · Asistencia {{ alert.attendance_rate | number:'1.1-1' }}%</em>
              </li>
            }
          </ul>
        </section>
      }
    }
  `,
  styles: [`
    .metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
    .secondary { margin-top: 16px; }
    article, .next-step, .alerts { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: 22px; }
    article { display: grid; gap: 12px; }
    article span, .eyebrow { color: var(--color-muted-text); font-size: .82rem; text-transform: uppercase; letter-spacing: .08em; }
    article strong { color: var(--color-primary); font-size: 2.2rem; }
    .next-step { margin-top: 24px; border-left: 4px solid var(--color-accent); }
    h2 { margin: 8px 0; }
    p { color: var(--color-muted-text); line-height: 1.6; }
    .state { padding: 24px; background: var(--color-surface); border: 1px solid var(--color-border); }
    .error { color: #a33a32; }
    .alerts { margin-top: 24px; }
    .alerts ul { list-style: none; margin: 16px 0 0; padding: 0; display: grid; gap: 12px; }
    .alerts li { display: grid; gap: 4px; padding: 14px 16px; border: 1px solid var(--color-border); border-radius: 8px; background: #f8fafc; }
    .alerts span { color: #a33a32; font-weight: 700; }
    .alerts em { font-style: normal; color: var(--color-muted-text); }
    @media (max-width: 700px) { .metrics { grid-template-columns: 1fr; } }
  `],
})
export class DashboardPage implements OnInit {
  private readonly api = inject(ApiService);
  protected readonly summary = signal<DashboardSummary>({
    total_students: 0,
    active_students: 0,
    average_score: 0,
    attendance_rate: 0,
    at_risk_count: 0,
  });
  protected readonly alerts = signal<RiskAlert[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal(false);

  ngOnInit(): void {
    this.api.getDashboardSummary().subscribe({
      next: (summary) => {
        this.summary.set(summary);
        this.loadAlerts();
      },
      error: () => {
        this.error.set(true);
        this.loading.set(false);
      },
    });
  }

  private loadAlerts(): void {
    this.api.getRiskAlerts().subscribe({
      next: (items) => {
        this.alerts.set(items);
        this.loading.set(false);
      },
      error: () => {
        this.alerts.set([]);
        this.loading.set(false);
      },
    });
  }
}