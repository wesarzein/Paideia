import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, Subject, throwError } from 'rxjs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiService, Enrollment, Student } from '../src/app/core/services/api.service';
import { EnrollmentManagerComponent } from '../src/app/features/students/enrollment-manager.component';

class Enrollments extends EnrollmentManagerComponent {
  profile(id = 'student') { this.student = { id, grade_id: 'grade', section_id: 'section' } as Student; this.ngOnChanges(); }
  saveNow() { this.courseId = 'course'; this.periodId = 'period'; this.save(); }
  failed() { return this.error(); }
  rows() { return this.records(); }
}
function setup(role = 'admin') {
  vi.stubGlobal('localStorage', { getItem: () => JSON.stringify({ role }) });
  const listEnrollments = vi.fn(() => of([] as Enrollment[]));
  const createEnrollment = vi.fn(payload => of({ id: 'id', ...payload, status: 'ACTIVE' } as Enrollment));
  const injector = Injector.create({ providers: [{ provide: ApiService, useValue: {
    getAcademicCatalog: () => of({ courses: [], periods: [] }), listCourses: () => of([]), listEnrollments, createEnrollment,
  } }] });
  return { page: runInInjectionContext(injector, () => new Enrollments()), listEnrollments, createEnrollment };
}
afterEach(() => vi.unstubAllGlobals());
describe('academic enrollment profile', () => {
  it('filters by student and prevents repeating a successful registration', () => {
    const { page, listEnrollments, createEnrollment } = setup(); page.profile(); page.saveNow(); page.saveNow();
    expect(listEnrollments).toHaveBeenCalledWith({ student_id: 'student' });
    expect(createEnrollment).toHaveBeenCalledOnce(); expect(page.rows()).toHaveLength(1);
    expect(createEnrollment).toHaveBeenCalledWith({ student_id: 'student', course_id: 'course', period_id: 'period' });
  });
  it('does not create a second enrollment when an existing inactive identity is present', () => {
    const { page, listEnrollments, createEnrollment } = setup();
    listEnrollments.mockReturnValueOnce(of([{ id: 'old', course_id: 'course', period_id: 'period', status: 'INACTIVE' }] as Enrollment[]));
    page.profile(); page.saveNow(); expect(createEnrollment).not.toHaveBeenCalled();
  });
  it('shows concurrent conflict errors and keeps prior records', () => {
    const { page, createEnrollment } = setup(); page.profile();
    createEnrollment.mockReturnValueOnce(throwError(() => ({ error: { detail: 'La matrícula ya existe' } })));
    page.saveNow(); expect(page.failed()).toContain('ya existe'); expect(page.rows()).toHaveLength(0);
  });
  it('ignores old profile responses and blocks submission after failed reads', () => {
    const { page, listEnrollments, createEnrollment } = setup(); const old = new Subject<Enrollment[]>();
    listEnrollments.mockReturnValueOnce(old); page.profile('old'); page.profile('current');
    old.next([{ id: 'old' }] as Enrollment[]); old.complete(); expect(page.rows()).toHaveLength(0);
    listEnrollments.mockReturnValueOnce(throwError(() => ({}))); page.profile(); page.saveNow();
    expect(createEnrollment).not.toHaveBeenCalled();
  });
  it('keeps director consultation read only', () => {
    const { page, createEnrollment } = setup('director'); page.profile(); page.saveNow();
    expect(createEnrollment).not.toHaveBeenCalled();
  });
});
