import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, throwError } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';

import { ApiService, AcademicPeriod, PeriodPayload } from '../src/app/core/services/api.service';
import { PeriodManagerComponent } from '../src/app/features/courses/period-manager.component';

class Periods extends PeriodManagerComponent {
  submit(form: PeriodPayload) { this.form = form; this.save(); }
  select(period: AcademicPeriod) { this.edit(period); }
  failed() { return this.error(); }
}
const valid = { name: 'Periodo 2027', starts_on: '2027-01-01', ends_on: '2027-12-31' };

function setup(fail = false) {
  const createPeriod = vi.fn(() => of({ id: 'new', ...valid }));
  const updatePeriod = vi.fn(() => fail ? throwError(() => ({ error: { detail: 'Las fechas excluirían notas o asistencias registradas' } })) : of({ id: 'existing', ...valid }));
  const injector = Injector.create({ providers: [
    { provide: ApiService, useValue: { listPeriods: () => of([]), createPeriod, updatePeriod } },
  ] });
  return { page: runInInjectionContext(injector, () => new Periods()), createPeriod, updatePeriod };
}
describe('calendar management', () => {
  it('rejects inverted dates locally', () => {
    const { page, createPeriod } = setup(); page.submit({ ...valid, starts_on: '2028-01-01' });
    expect(createPeriod).not.toHaveBeenCalled(); expect(page.failed()).toContain('orden cronológico');
  });
  it('creates a trimmed period and refreshes the catalog', () => {
    const { page, createPeriod } = setup(); const changed = vi.fn(); page.periodsChanged.subscribe(changed);
    page.submit({ ...valid, name: ' Periodo 2027 ' });
    expect(createPeriod).toHaveBeenCalledWith(valid); expect(changed).toHaveBeenCalledTimes(1);
  });
  it('updates an existing identity and shows historical-data protection errors', () => {
    const { page, createPeriod, updatePeriod } = setup(true); page.select({ id: 'existing', ...valid });
    page.submit(valid); expect(updatePeriod).toHaveBeenCalledWith('existing', valid);
    expect(createPeriod).not.toHaveBeenCalled(); expect(page.failed()).toContain('excluirían notas');
  });
});
