import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, throwError } from 'rxjs';
import { describe, expect, it } from 'vitest';

import { ApiService, RiskAlert } from '../src/app/core/services/api.service';
import { ReportsPage } from '../src/app/features/reports/reports.page';

class Reports extends ReportsPage {
  query() { this.gradeId = 'synthetic'; this.load(); }
  metrics() { return [this.average(), this.attendance()]; }
  failed() { return this.loadError(); }
}

function setup(rows: Partial<RiskAlert>[], failed = false) {
  const injector = Injector.create({ providers: [
    { provide: ApiService, useValue: {
      getAcademicCatalog: () => of({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] }),
      getStudentReports: () => failed ? throwError(() => new Error('Unavailable')) : of(rows),
    } },
  ] });
  const page = runInInjectionContext(injector, () => new Reports());
  page.query();
  return page;
}

describe('report evidence', () => {
  it('combines captured weights and attendance counts, excluding missing evidence', () => {
    const page = setup([
      { average_score: 10, grade_weight_sum: 3, attendance_rate: 100, attendance_count: 1 },
      { average_score: 20, grade_weight_sum: 1, attendance_rate: 0, attendance_count: 3 },
      { average_score: null, grade_weight_sum: 0, attendance_rate: null, attendance_count: 0 },
    ]);
    expect(page.metrics()).toEqual([12.5, 25]);
  });

  it('preserves measured zeros', () => {
    expect(setup([{ average_score: 0, grade_weight_sum: 1, attendance_rate: 0, attendance_count: 1 }]).metrics()).toEqual([0, 0]);
  });

  it('represents an empty set by nulls', () => {
    expect(setup([]).metrics()).toEqual([null, null]);
  });

  it('distinguishes a request failure from an empty successful report', () => {
    expect(setup([], true).failed()).toBe(true);
    expect(setup([]).failed()).toBe(false);
  });
});
