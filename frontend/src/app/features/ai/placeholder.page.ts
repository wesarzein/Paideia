import { Component } from '@angular/core';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [PageHeaderComponent],
  template: `
    <app-page-header title="IA" description="Espacio para futuras alertas tempranas y recomendaciones explicables." />
    <section class="panel">
      <div class="icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 3v2m0 14v2m9-9h-2M5 12H3m13-5a4 4 0 1 1-8 0 4 4 0 0 1 8 0Zm2 10H7" /></svg></div>
      <h2>Módulo en preparación</h2>
      <p>La interfaz está lista para la siguiente etapa. No se generan predicciones ni alertas automáticas por ahora.</p>
      <span>Interfaz preparada · sin modelos activos</span>
    </section>
  `,
  styles: [`
    .panel{min-height:300px;display:grid;align-content:center;justify-items:center;gap:10px;padding:36px;text-align:center;background:var(--color-surface);border:1px solid var(--color-border);border-radius:12px}
    .icon{display:grid;place-items:center;width:52px;height:52px;border-radius:12px;background:#fff5e7;color:var(--color-accent)}
    svg{width:26px;height:26px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
    h2{margin:8px 0 0;font-size:1.15rem}p{max-width:480px;color:var(--color-muted-text);line-height:1.6}
    span{padding:6px 10px;border-radius:999px;background:var(--color-muted);color:var(--color-muted-text);font-size:.82rem}
  `],
})
export class PlaceholderPage {}
