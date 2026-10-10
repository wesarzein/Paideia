import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, Subject, throwError } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';
import { ApiService } from '../src/app/core/services/api.service';
import { AcademicHistoryComponent, AcademicChange } from '../src/app/features/students/academic-history.component';

class History extends AcademicHistoryComponent {
  select(id: string) { this.studentId = id; this.ngOnChanges(); }
  values() { return this.rows(); }
  failed() { return this.error(); }
  next() { this.page(1); }
}
function setup() {
  const getAcademicHistory = vi.fn(() => of([] as AcademicChange[]));
  const injector = Injector.create({ providers: [{ provide: ApiService, useValue: { getAcademicHistory } }] });
  return { page: runInInjectionContext(injector, () => new History()), getAcademicHistory };
}
describe('authorized academic history', () => {
  it('ignores stale responses after changing student', () => {
    const { page, getAcademicHistory } = setup(); const old = new Subject<AcademicChange[]>();
    getAcademicHistory.mockReturnValueOnce(old); page.select('old'); page.select('current');
    old.next([{ id: 'private-old' }] as AcademicChange[]);
    expect(page.values()).toEqual([]);
    expect(getAcademicHistory).toHaveBeenLastCalledWith('current', 0);
  });
  it('reports a failed authorization instead of an empty history', () => {
    const { page, getAcademicHistory } = setup();
    getAcademicHistory.mockReturnValueOnce(throwError(() => ({}))); page.select('student');
    expect(page.failed()).toContain('autorizado');
  });
  it('resets pagination when selecting another student', () => {
    const { page, getAcademicHistory } = setup(); page.select('first'); page.next();
    expect(getAcademicHistory).toHaveBeenLastCalledWith('first', 50);
    page.select('second'); expect(getAcademicHistory).toHaveBeenLastCalledWith('second', 0);
  });
});
