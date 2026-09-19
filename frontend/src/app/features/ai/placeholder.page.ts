import { DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { ApiService, RiskAlert } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [PageHeaderComponent, DecimalPipe],
  template: `<app-page-header title="IA" description="Alertas tempranas para priorizar la atención docente." /><section class="panel"><h2>Estudiantes que requieren atención</h2>@if (!alerts().length) {<p>No hay alertas activas.</p>} @for (alert of alerts(); track alert.student_id) {<article><strong>{{ alert.student_name }}</strong><span>{{ alert.risk_level }} · Promedio {{ alert.average_score | number:'1.1-1' }} · Asistencia {{ alert.attendance_rate | number:'1.1-1' }}%</span><p>{{ recommendation(alert) }}</p></article>}</section>`,
  styles: [` .panel,article{background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;padding:22px} article{margin-top:12px;display:grid;gap:6px} span,p{color:var(--color-muted-text)} `],
})
export class PlaceholderPage {
  private readonly api = inject(ApiService);
  protected readonly alerts = signal<RiskAlert[]>([]);
  constructor() { this.api.getRiskAlerts().subscribe({ next: (data) => this.alerts.set(data) }); }
  protected recommendation(alert: RiskAlert) { return alert.average_score < 12 ? 'Programar refuerzo académico y revisar evidencias recientes.' : 'Contactar a la familia y acordar seguimiento de asistencia.'; }
}
