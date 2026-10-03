import { DecimalPipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { AcademicCatalog, ApiService, DashboardSummary } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [DecimalPipe, PageHeaderComponent],
  template: `
    <app-page-header title="Dashboard" description="Resumen del rendimiento académico del colegio." />

    <section class="filters" aria-label="Filtros del dashboard">
      <label>
        Grado
        <select [value]="filters()['grade_id'] ?? ''" (change)="setGrade($event)">
          <option value="">Todos los grados</option>
          @for (grade of catalog().grades; track grade.id) {
            <option [value]="grade.id">{{ grade.name }} {{ grade.level }}</option>
          }
        </select>
      </label>
      <label>
        Sección
        <select [value]="filters()['section_id'] ?? ''" (change)="setSection($event)" [disabled]="!filters()['grade_id']">
          <option value="">Todas las secciones</option>
          @if (filters()['grade_id']) {
            @for (section of catalog().sections; track section.id) {
              <option [value]="section.id">{{ section.name }}</option>
            }
          }
        </select>
      </label>
      <label>
        Curso
        <select [value]="filters()['course_id'] ?? ''" (change)="setFilter('course_id', $event)" [disabled]="!filters()['section_id']">
          <option value="">Todos los cursos</option>
          @if (filters()['section_id']) {
            @for (course of catalog().courses; track course.id) {
              <option [value]="course.id">{{ course.name }}</option>
            }
          }
        </select>
      </label>
      <label>
        Periodo
        <select [value]="filters()['period_id'] ?? ''" (change)="setFilter('period_id', $event)">
          <option value="">Todos los periodos</option>
          @for (period of catalog().periods; track period.id) {
            <option [value]="period.id" [selected]="filters()['period_id'] === period.id">{{ period.name }}</option>
          }
        </select>
      </label>
      <label>
        Mes
        <select [value]="filters()['month'] ?? ''" (change)="setFilter('month', $event)">
          <option value="">Todo el año</option>
          @for (month of months; track month.value) {
            <option [value]="month.value">{{ month.label }}</option>
          }
        </select>
      </label>
    </section>

    @if (loading()) {
      <p class="state" role="status">Cargando indicadores...</p>
    } @else if (error()) {
      <div class="state error" role="alert">
        <p>No se pudieron cargar los indicadores.</p>
        <button type="button" (click)="refresh()">Reintentar</button>
      </div>
    } @else {
      <section class="metrics" aria-label="Resumen académico">
        <article><span>Estudiantes</span><strong>{{ summary().total_students }}</strong></article>
        <article><span>Promedio del grupo</span><strong>{{ summary().average_score | number:'1.1-1' }}</strong></article>
        <article><span>Asistencia</span><strong>{{ summary().attendance_rate | number:'1.1-1' }}%</strong></article>
      </section>

      <section class="empty" role="status">
        <h2>Alertas automáticas aún no habilitadas</h2>
        <p>El Dashboard presenta datos académicos registrados. Los análisis de riesgo estarán disponibles cuando se implemente el módulo de Analítica e IA.</p>
      </section>
    }
  `,
  styles: [`
    .filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 20px; padding: 16px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; }
    label { display: grid; gap: 6px; color: var(--color-muted-text); font-size: .88rem; }
    select { width: 100%; min-height: 40px; padding: 8px 10px; color: var(--color-text); background: white; border: 1px solid var(--color-border); border-radius: 6px; font: inherit; }
    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 16px; }
    article, .empty { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: 22px; }
    article { display: grid; gap: 12px; }
    article span { color: var(--color-muted-text); font-size: .82rem; text-transform: uppercase; letter-spacing: .06em; }
    article strong { color: var(--color-primary); font-size: 2.2rem; }
    .state { padding: 24px; background: var(--color-surface); border: 1px solid var(--color-border); }
    .error { color: #a33a32; }
    button { border: 0; border-radius: 6px; padding: 9px 13px; background: var(--color-primary); color: white; cursor: pointer; font: inherit; }
    .empty { margin-top: 24px; }
    .empty { border-left: 4px solid var(--color-accent); }
    h2 { margin: 4px 0 16px; }
    p, small { color: var(--color-muted-text); line-height: 1.5; }
  `],
})
export class DashboardPage implements OnInit {
  private readonly api = inject(ApiService);
  protected readonly catalog = signal<AcademicCatalog>({
    grades: [],
    sections: [],
    courses: [],
    periods: [],
    students: [],
    literal_scale: [],
  });
  protected readonly filters = signal<Record<string, string>>({});
  protected readonly months = [
    { value: 1, label: 'Enero' }, { value: 2, label: 'Febrero' }, { value: 3, label: 'Marzo' },
    { value: 4, label: 'Abril' }, { value: 5, label: 'Mayo' }, { value: 6, label: 'Junio' },
    { value: 7, label: 'Julio' }, { value: 8, label: 'Agosto' }, { value: 9, label: 'Septiembre' },
    { value: 10, label: 'Octubre' }, { value: 11, label: 'Noviembre' }, { value: 12, label: 'Diciembre' },
  ];
  protected readonly summary = signal<DashboardSummary>({
    total_students: 0,
    active_students: 0,
    average_score: 0,
    attendance_rate: 0,
    at_risk_count: 0,
  });
  protected readonly loading = signal(true);
  protected readonly error = signal(false);

  ngOnInit(): void {
    this.api.getAcademicCatalog().subscribe({
      next: (catalog) => {
        this.catalog.set(catalog);
        const period = catalog.periods[0];
        if (period) this.filters.set({ period_id: period.id });
        this.refresh();
      },
      error: () => this.showError(),
    });
  }

  protected setGrade(event: Event): void {
    const value = this.eventValue(event);
    const filters = { ...this.filters() };
    delete filters['section_id'];
    delete filters['course_id'];
    if (value) filters['grade_id'] = value;
    else delete filters['grade_id'];
    this.filters.set(filters);
    this.loadCatalog(value ? { grade_id: value } : {});
  }

  protected setSection(event: Event): void {
    const value = this.eventValue(event);
    const filters = { ...this.filters() };
    delete filters['course_id'];
    if (value) filters['section_id'] = value;
    else delete filters['section_id'];
    this.filters.set(filters);
    const catalogFilters: Record<string, string> = {};
    if (filters['grade_id']) catalogFilters['grade_id'] = filters['grade_id'];
    if (value) catalogFilters['section_id'] = value;
    this.loadCatalog(catalogFilters);
  }

  protected setFilter(key: string, event: Event): void {
    const value = this.eventValue(event);
    const filters = { ...this.filters() };
    if (value) filters[key] = value;
    else delete filters[key];
    this.filters.set(filters);
    this.refresh();
  }

  protected refresh(): void {
    this.loading.set(true);
    this.error.set(false);
    this.api.getDashboardSummary(this.filters()).subscribe({
      next: (summary) => {
        this.summary.set(summary);
        this.loading.set(false);
      },
      error: () => this.showError(),
    });
  }

  private loadCatalog(filters: Record<string, string>): void {
    this.loading.set(true);
    this.api.getAcademicCatalog(filters).subscribe({
      next: (catalog) => {
        this.catalog.set(catalog);
        this.refresh();
      },
      error: () => this.showError(),
    });
  }

  private showError(): void {
    this.error.set(true);
    this.loading.set(false);
  }

  private eventValue(event: Event): string {
    return event.target instanceof HTMLSelectElement ? event.target.value : '';
  }
}
