import { Component, OnInit, inject, signal } from '@angular/core';
import { ApiService, StudentSummary } from '../../core/services/api.service';
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
        <article><span>Total de estudiantes</span><strong>{{ summary().total }}</strong></article>
        <article><span>Estudiantes activos</span><strong>{{ summary().active }}</strong></article>
        <article><span>Inactivos</span><strong>{{ summary().inactive }}</strong></article>
      </section>
      <section class="next-step">
        <span class="eyebrow">MVP conectado</span>
        <h2>La base operativa ya está lista</h2>
        <p>La gestión de estudiantes consume la API FastAPI y persiste en PostgreSQL. IA y BI quedan preparados para una siguiente iteración.</p>
      </section>
    }
  `,
  styles: [`
    .metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
    article, .next-step { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: 22px; }
    article { display: grid; gap: 12px; }
    article span, .eyebrow { color: var(--color-muted-text); font-size: .82rem; text-transform: uppercase; letter-spacing: .08em; }
    article strong { color: var(--color-primary); font-size: 2.4rem; }
    .next-step { margin-top: 24px; border-left: 4px solid var(--color-accent); }
    h2 { margin: 8px 0; }
    p { color: var(--color-muted-text); line-height: 1.6; }
    .state { padding: 24px; background: var(--color-surface); border: 1px solid var(--color-border); }
    .error { color: #a33a32; }
    @media (max-width: 700px) { .metrics { grid-template-columns: 1fr; } }
  `],
})
export class DashboardPage implements OnInit {
  private readonly api = inject(ApiService);
  protected readonly summary = signal<StudentSummary>({ total: 0, active: 0, inactive: 0 });
  protected readonly loading = signal(true);
  protected readonly error = signal(false);

  ngOnInit(): void {
    this.api.getStudentSummary().subscribe({
      next: (summary) => { this.summary.set(summary); this.loading.set(false); },
      error: () => { this.error.set(true); this.loading.set(false); },
    });
  }
}