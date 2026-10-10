import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of } from 'rxjs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiService } from '../src/app/core/services/api.service';
import { ConfirmService } from '../src/app/core/services/confirm.service';
import { CoursesPage } from '../src/app/features/courses/courses.page';
import { PlaceholderPage } from '../src/app/features/imports/placeholder.page';
import { CohortManagerComponent } from '../src/app/features/courses/cohort-manager.component';

class TeacherCourses extends CoursesPage {
  async attemptWrites() {
    const course = { id: 'course', name: 'Curso', code: null, is_active: true };
    this.chooseCourse(course); this.saveCourse(); this.saveComponent(); this.assignCourse();
    await this.toggleCourse(course);
  }
}
class TeacherImports extends PlaceholderPage {
  modeName() { return this.mode(); }
  attemptStudents() { this.setMode('students'); this.importStudents(); }
  upload() {
    this.periodId = 'period'; this.courseId = 'course'; this.gradeId = 'grade'; this.sectionId = 'section'; this.bimestre = 3;
    this.schoolYear = 2026; this.blocks = { '1': { evaluation_name: 'Agosto', assessment_date: '2026-08-10' }, '2': { evaluation_name: 'Septiembre', assessment_date: '2026-09-10' } };
    this.lockContext(); this.select({ target: { files: [{ name: 'grades.xlsx' }] } } as unknown as Event);
  }
}
class ReadCohorts extends CohortManagerComponent {
  attemptWrites() { this.canManage = false; this.gradeName = '2°'; this.sectionGrade = 'grade'; this.sectionName = 'B'; this.saveGrade(); this.saveSection(); }
}
afterEach(() => vi.unstubAllGlobals());
function setup() {
  vi.stubGlobal('localStorage', { getItem: () => JSON.stringify({ role: 'teacher' }) });
  const write = vi.fn(() => of({})); const previewGradeImport = vi.fn(() => of({ total: 0, rows: [], columns: [], errors: [] }));
  const api = { listCourses: () => of([]), getAcademicCatalog: () => of({ courses: [], grades: [], sections: [], periods: [], students: [] }),
    listAcademicGrades: () => of([]), listAcademicSections: () => of([]), listAssessmentComponents: () => of([]), listCourseAssignments: () => of([]),
    createCourse: write, updateCourse: write, createAssessmentComponent: write, createCourseAssignment: write,
    createAcademicGrade: write, createAcademicSection: write, commitStudentRows: write, previewStudentImport: write, previewGradeImport };
  const ask = vi.fn(() => Promise.resolve(true));
  const injector = Injector.create({ providers: [{ provide: ApiService, useValue: api }, { provide: ConfirmService, useValue: { ask } }] });
  return { injector, write, ask, previewGradeImport };
}
describe('teacher academic access', () => {
  it('keeps courses and grade/section catalog read only', async () => {
    const { injector, write, ask } = setup();
    const courses = runInInjectionContext(injector, () => new TeacherCourses());
    const cohorts = runInInjectionContext(injector, () => new ReadCohorts());
    await courses.attemptWrites(); cohorts.attemptWrites();
    expect(write).not.toHaveBeenCalled(); expect(ask).not.toHaveBeenCalled();
  });
  it('starts in grades and cannot switch to pupil import', () => {
    const { injector, write, previewGradeImport } = setup();
    const page = runInInjectionContext(injector, () => new TeacherImports());
    expect(page.modeName()).toBe('grades'); page.attemptStudents();
    expect(page.modeName()).toBe('grades'); expect(write).not.toHaveBeenCalled();
    page.upload(); expect(previewGradeImport).toHaveBeenCalledOnce();
  });
});
