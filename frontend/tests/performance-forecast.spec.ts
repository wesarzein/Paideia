import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, Subject, throwError } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';
import { ApiService } from '../src/app/core/services/api.service';
import { AcademicAiPage } from '../src/app/features/ai/academic-ai.page';
import { PerformanceForecast, PerformanceForecastService } from '../src/app/features/ai/performance-forecast.service';

class Page extends AcademicAiPage {
  select() { this.gradeId = 'grade'; this.sectionId = 'section'; this.periodId = 'period'; }
  run() { this.analyze(); }
  change() { this.invalidate(); }
  individual() { this.mode = 'student'; }
  bimester(n: number | null) { this.horizon = 'bimester'; this.throughBimester = n; }
  result() { return this.data(); }
  failed() { return this.error(); }
  refresh() { this.loadCatalog(); }
  ready() { return this.canAnalyze(); }
}
function setup() {
  const analyze = vi.fn(() => of({ rows: [] } as unknown as PerformanceForecast));
  const getAcademicCatalog = vi.fn(() => of({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] }));
  const injector = Injector.create({ providers: [
    { provide: ApiService, useValue: { getAcademicCatalog } },
    { provide: PerformanceForecastService, useValue: { analyze } },
  ] });
  const page = runInInjectionContext(injector, () => new Page());
  page.select();
  return { page, analyze, getAcademicCatalog };
}
describe('academic performance forecasts', () => {
  it('sends the classroom and period to the authorized API', () => {
    const { page, analyze } = setup(); page.run();
    expect(analyze).toHaveBeenCalledWith(expect.objectContaining({ section_id: 'section', period_id: 'period', horizon: 'exam' }));
  });
  it('requires an individual student and an explicitly completed bimester', () => {
    const { page, analyze } = setup(); page.individual(); page.run();
    expect(analyze).not.toHaveBeenCalled();
    const other = setup(); other.page.bimester(null); expect(other.page.ready()).toBe(false);
    other.page.bimester(2.5); expect(other.page.ready()).toBe(false);
    other.page.bimester(3); other.page.run();
    expect(other.analyze).toHaveBeenCalledWith(expect.objectContaining({ through_bimester: '3', horizon: 'bimester' }));
  });
  it('ignores a previous selection response', () => {
    const { page, analyze } = setup(); const pending = new Subject<PerformanceForecast>();
    analyze.mockReturnValueOnce(pending); page.run(); page.change();
    pending.next({ rows: [] } as unknown as PerformanceForecast);
    expect(page.result()).toBeNull();
  });
  it('shows failures and permits retry', () => {
    const { page, analyze } = setup();
    analyze.mockReturnValueOnce(throwError(() => ({ error: { detail: 'Modelo no disponible' } })));
    page.run(); expect(page.failed()).toBe('Modelo no disponible');
    page.run(); expect(page.result()).not.toBeNull(); expect(page.failed()).toBe('');
  });
  it('blocks analysis after a catalog failure until reload succeeds', () => {
    const { page, analyze, getAcademicCatalog } = setup();
    getAcademicCatalog.mockReturnValueOnce(throwError(() => ({})));
    page.refresh(); page.run(); expect(analyze).not.toHaveBeenCalled();
    page.refresh(); page.run(); expect(analyze).toHaveBeenCalledOnce();
  });
  it('prevents duplicate analysis requests while loading', () => {
    const { page, analyze } = setup(); analyze.mockReturnValueOnce(new Subject<PerformanceForecast>());
    page.run(); page.run(); expect(analyze).toHaveBeenCalledOnce();
  });
});
