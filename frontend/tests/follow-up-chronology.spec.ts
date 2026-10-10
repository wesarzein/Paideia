import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, Subject, throwError } from 'rxjs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiService, FollowUp } from '../src/app/core/services/api.service';
import { ConfirmService } from '../src/app/core/services/confirm.service';
import { PlaceholderPage } from '../src/app/features/follow-up/placeholder.page';

class Timeline extends PlaceholderPage {
  group(id = 'section') { this.gradeId = 'grade'; this.sectionId = id; this.loadCatalog(); }
  select() { this.edit({ id: 'existing', student_id: 'student', category: 'MEETING', action: 'Texto conservado', status: 'CLOSED' } as FollowUp); }
  saveNow() { this.save(); }
  failed() { return this.error(); }
  rows() { return this.items(); }
}
function setup(role = 'admin') {
  vi.stubGlobal('localStorage', { getItem: () => JSON.stringify({ role }) });
  const listFollowUps = vi.fn(() => of([] as FollowUp[]));
  const updateFollowUp = vi.fn(() => of({})); const createFollowUp = vi.fn(() => of({}));
  const injector = Injector.create({ providers: [
    { provide: ApiService, useValue: { listFollowUps, updateFollowUp, createFollowUp,
      getAcademicCatalog: () => of({ students: [{ id: 'student' }], grades: [], sections: [] }),
    } }, { provide: ConfirmService, useValue: {} },
  ] });
  return { page: runInInjectionContext(injector, () => new Timeline()), listFollowUps, updateFollowUp, createFollowUp };
}
afterEach(() => vi.unstubAllGlobals());
describe('follow-up chronology', () => {
  it('keeps an existing closed status when editing description or category', () => {
    const { page, updateFollowUp, createFollowUp } = setup(); page.group(); page.select(); page.saveNow();
    expect(updateFollowUp).toHaveBeenCalledWith('existing', expect.objectContaining({ status: 'CLOSED', student_id: 'student' }));
    expect(createFollowUp).not.toHaveBeenCalled();
  });
  it('shows API failures instead of silently losing the edit', () => {
    const { page, updateFollowUp } = setup(); page.group(); page.select();
    updateFollowUp.mockReturnValueOnce(throwError(() => ({ error: { detail: 'No tienes permiso' } })));
    page.saveNow(); expect(page.failed()).toContain('No tienes permiso');
  });
  it('ignores a previous group response and resets its edit context', () => {
    const { page, listFollowUps, updateFollowUp } = setup(); const old = new Subject<FollowUp[]>();
    listFollowUps.mockReturnValueOnce(old); page.group(); page.select(); page.group('new');
    old.next([{ id: 'old' }] as FollowUp[]); expect(page.rows()).toHaveLength(0);
    page.saveNow(); expect(updateFollowUp).not.toHaveBeenCalled();
  });
  it('does not mistake a failed timeline read for an empty writable group', () => {
    const { page, listFollowUps, updateFollowUp } = setup();
    listFollowUps.mockReturnValueOnce(throwError(() => ({}))); page.group(); page.select(); page.saveNow();
    expect(updateFollowUp).not.toHaveBeenCalled();
  });
  it('does not offer edits to a director whose API role only permits creation and reading', () => {
    const { page, updateFollowUp } = setup('director'); page.group(); page.select(); page.saveNow();
    expect(updateFollowUp).not.toHaveBeenCalled();
  });
});
