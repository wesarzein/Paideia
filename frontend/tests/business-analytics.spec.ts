import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, Subject, throwError } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';
import { ApiService } from '../src/app/core/services/api.service';
import { AnalyticsPage } from '../src/app/features/analytics/analytics.page';
import { AnalyticsService, BusinessIndicators } from '../src/app/features/analytics/analytics.service';

class Page extends AnalyticsPage {
  select(course = '') { this.courseId = course; this.load(); }
  result() { return this.data(); }
  failed() { return this.error(); }
  chart(d: BusinessIndicators) { return this.points(d); }
}
function setup() {
  const get = vi.fn(() => of({ average: 0 } as BusinessIndicators));
  const injector = Injector.create({ providers: [
    { provide: AnalyticsService, useValue: { get } },
    { provide: ApiService, useValue: { getAcademicCatalog: () => of({ grades: [], sections: [], courses: [], periods: [], students: [] }) } },
  ] });
  return { page: runInInjectionContext(injector, () => new Page()), get };
}
describe('business analytics', () => {
  it('preserves zero and sends exact course scope filters', () => {
    const { page, get } = setup(); page.select('course');
    expect(get).toHaveBeenLastCalledWith({ course_id: 'course' });
    expect(page.result()?.average).toBe(0);
  });
  it('clears stale indicators on error and distinguishes failure from missing evidence', () => {
    const { page, get } = setup();
    get.mockReturnValueOnce(throwError(() => ({}))); page.select();
    expect(page.result()).toBeNull(); expect(page.failed()).toBe(true);
    get.mockReturnValueOnce(of({ average: null } as BusinessIndicators)); page.select();
    expect(page.failed()).toBe(false); expect(page.result()?.average).toBeNull();
  });
  it('ignores a late response for previous filters', () => {
    const { page, get } = setup(); const old = new Subject<BusinessIndicators>();
    get.mockReturnValueOnce(old); page.select('previous'); page.select('current');
    old.next({ average: 19 } as BusinessIndicators);
    expect(page.result()?.average).toBe(0);
  });
  it('does not plot missing averages as zero', () => {
    const { page } = setup();
    expect(page.chart({ months: [{ average: null }, { average: 0 }] } as BusinessIndicators)).toBe('580,140');
  });
});
