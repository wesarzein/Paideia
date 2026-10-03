import { Component } from '@angular/core';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [PageHeaderComponent],
  template: `
    <app-page-header title="Analítica académica" description="Espacio institucional de consulta y visualización de indicadores." />
    <section class="panel">
      <div class="icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 19V5m0 14h17M8 15l3-4 3 2 5-7" /></svg></div>
      <h2>Disponible en una próxima etapa</h2>
      <p>Los filtros, indicadores comparativos y tendencias aparecerán aquí cuando se habilite el módulo de analítica.</p>
      <span class="status">Interfaz preparada · sin cálculos activos</span>
    </section>
  `,
  styles: [`
    .panel{min-height:300px;display:grid;align-content:center;justify-items:center;gap:10px;padding:36px;text-align:center;background:var(--color-surface);border:1px solid var(--color-border);border-radius:12px}
    .icon{display:grid;place-items:center;width:52px;height:52px;border-radius:12px;background:#fff5e7;color:var(--color-accent)}
    svg{width:26px;height:26px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
    h2{margin:8px 0 0;font-size:1.15rem}p{max-width:480px;color:var(--color-muted-text);line-height:1.6}
    .status{margin-top:8px;padding:6px 10px;border-radius:999px;background:var(--color-muted);color:var(--color-muted-text);font-size:.82rem}
  `],
})
export class PlaceholderPage {}
