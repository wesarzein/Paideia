import { DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [PageHeaderComponent, DecimalPipe],
  template: `<app-page-header title="Analítica" description="Indicadores académicos calculados sobre notas y asistencia." /><section class="metrics"><article><span>Promedio</span><strong>{{ kpis().average_score | number:'1.1-1' }}</strong></article><article><span>Asistencia</span><strong>{{ kpis().attendance_rate | number:'1.1-1' }}%</strong></article><article><span>Notas registradas</span><strong>{{ kpis().grades_count }}</strong></article><article><span>Asistencias</span><strong>{{ kpis().attendance_count }}</strong></article></section>`,
  styles: [` .metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:16px} article{background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;padding:22px;display:grid;gap:10px} span{color:var(--color-muted-text)} strong{font-size:2rem;color:var(--color-primary)} @media(max-width:700px){.metrics{grid-template-columns:1fr 1fr}} `],
})
export class PlaceholderPage {
  private readonly api = inject(ApiService);
  protected readonly kpis = signal({ average_score: 0, attendance_rate: 0, grades_count: 0, attendance_count: 0 });
  constructor() { this.api.getKpis().subscribe({ next: (data) => this.kpis.set(data) }); }
}
