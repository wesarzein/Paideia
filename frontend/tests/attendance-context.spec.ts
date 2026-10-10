import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, Subject, throwError } from 'rxjs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiService, AttendanceRecord } from '../src/app/core/services/api.service';
import { AttendancePage } from '../src/app/features/attendance/attendance.page';

class Attendance extends AttendancePage {
  day(value = '2026-04-01') {
    this.gradeId = 'grade'; this.sectionId = 'section'; this.courseId = 'course'; this.periodId = 'period';
    this.attendanceDate = value; this.loadRecords();
  }
  score(id = 'a') { return this.status[id]; }
  edit(value: string) { this.status['a'] = value; }
  refresh() { this.loadRecords(); }
  save() { this.saveAll(); }
  failed() { return this.error(); }
  saved() { return this.message(); }
  blocked() { return this.busy(); }
  observation(value: string) { this.remarks['a'] = value; }
  savedObservation() { return this.remarks['a']; }
  nextDay() { this.moveDay(1); }
}
function setup(role = 'teacher') {
  vi.stubGlobal('localStorage', { getItem: () => JSON.stringify({ role }) });
  const listAttendance = vi.fn(() => of([] as AttendanceRecord[]));
  const createAttendance = vi.fn((payload) => of({ ...payload, id: payload.student_id }));
  const injector = Injector.create({ providers: [{ provide: ApiService, useValue: {
    getAcademicCatalog: () => of({ students: [{ id: 'a' }, { id: 'b' }], grades: [], sections: [], courses: [], periods: [], literal_scale: [] }),
    listAttendance, createAttendance,
  } }] });
  return { page: runInInjectionContext(injector, () => new Attendance()), listAttendance, createAttendance };
}
afterEach(() => vi.unstubAllGlobals());

describe('daily attendance workflow', () => {
  it('loads and submits permission remarks without losing local edits on refresh', () => {
    const { page, listAttendance, createAttendance } = setup();
    listAttendance.mockReturnValue(of([{ student_id: 'a', status: 'PRESENT', remarks: 'Permiso inicial' }] as AttendanceRecord[]));
    page.day(); expect(page.savedObservation()).toBe('Permiso inicial');
    page.observation('Retiro con permiso a las 11:30'); page.refresh();
    expect(page.savedObservation()).toBe('Retiro con permiso a las 11:30'); page.save();
    expect(createAttendance.mock.calls[0][0]).toHaveProperty('remarks', 'Retiro con permiso a las 11:30');
    page.nextDay(); expect(page.savedObservation()).toBe('Permiso inicial');
  });
  it('resets yesterday statuses and preserves local edits only within the same context', () => {
    const { page, listAttendance } = setup();
    listAttendance.mockReturnValueOnce(of([{ student_id: 'a', status: 'ABSENT' }] as AttendanceRecord[]));
    page.day(); expect(page.score()).toBe('ABSENT'); page.edit('LATE'); page.refresh();
    expect(page.score()).toBe('LATE'); page.day('2026-04-02'); expect(page.score()).toBe('PRESENT');
  });
  it('ignores responses for a previously selected date', () => {
    const { page, listAttendance } = setup(); const old = new Subject<AttendanceRecord[]>();
    listAttendance.mockReturnValueOnce(old); page.day(); page.day('2026-04-02');
    old.next([{ student_id: 'a', status: 'ABSENT' }] as AttendanceRecord[]);
    expect(page.score()).toBe('PRESENT'); expect(page.blocked()).toBe(false);
  });
  it('shows validation failures and stops before writing remaining students', () => {
    const { page, createAttendance } = setup(); page.day();
    createAttendance.mockReturnValueOnce(throwError(() => ({ error: { detail: 'Fecha fuera del periodo' } })));
    page.save(); expect(createAttendance).toHaveBeenCalledTimes(1);
    expect(page.failed()).toContain('Fecha fuera del periodo'); expect(page.failed()).toContain('0 de 2');
    expect(page.blocked()).toBe(false);
  });
  it('reports partial success and serializes requests while preventing a second save', () => {
    const { page, createAttendance } = setup(); page.day(); const first = new Subject<AttendanceRecord>();
    createAttendance.mockReturnValueOnce(first).mockReturnValueOnce(throwError(() => ({})));
    page.save(); page.save(); expect(createAttendance).toHaveBeenCalledTimes(1);
    first.next({ student_id: 'a', status: 'PRESENT' } as AttendanceRecord); first.complete();
    expect(createAttendance).toHaveBeenCalledTimes(2); expect(page.failed()).toContain('1 de 2');
    page.save(); expect(page.saved()).toContain('2 de 2'); expect(page.failed()).toBe('');
    expect(createAttendance.mock.calls[0][0]).toHaveProperty('remarks', null);
  });
  it('blocks writes after a failed read until a successful retry', () => {
    const { page, listAttendance, createAttendance } = setup();
    listAttendance.mockReturnValueOnce(throwError(() => ({}))); page.day(); page.save();
    expect(createAttendance).not.toHaveBeenCalled(); page.refresh(); page.save();
    expect(createAttendance).toHaveBeenCalledTimes(2);
  });
  it('keeps coordinator consultation read only and does not invent present records', () => {
    const { page, createAttendance } = setup('coordinator'); page.day(); page.save();
    expect(createAttendance).not.toHaveBeenCalled(); expect(page.score()).toBe('');
  });
});
