import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, throwError } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';
import { AcademicGrade, AcademicSection, ApiService } from '../src/app/core/services/api.service';
import { CohortManagerComponent } from '../src/app/features/courses/cohort-manager.component';

class Cohorts extends CohortManagerComponent {
  grade(name: string) { this.gradeName = name; this.saveGrade(); }
  section(name: string, grade = '') { this.sectionName = name; this.sectionGrade = grade; this.saveSection(); }
  selectGrade() { this.editGrade({ id: 'grade-id', name: '1°', level: 'Secundaria', is_active: true } as AcademicGrade); }
  selectSection() { this.editSection({ id: 'section-id', name: 'A', grade_id: 'grade-id', is_active: true } as AcademicSection); }
  failed() { return this.error(); }
}
function setup(failLoad = false) {
  const createAcademicGrade = vi.fn(() => of({}));
  const updateAcademicGrade = vi.fn(() => of({}));
  const createAcademicSection = vi.fn(() => of({}));
  const updateAcademicSection = vi.fn(() => throwError(() => ({ error: { detail: 'Debe conservar la letra' } })));
  const injector = Injector.create({ providers: [{ provide: ApiService, useValue: {
    listAcademicGrades: () => failLoad ? throwError(() => ({})) : of([]), listAcademicSections: () => of([]),
    createAcademicGrade, updateAcademicGrade, createAcademicSection, updateAcademicSection,
  } }] });
  return { page: runInInjectionContext(injector, () => new Cohorts()), createAcademicGrade, updateAcademicGrade, createAcademicSection, updateAcademicSection };
}
describe('academic cohort administration', () => {
  it('creates a trimmed label and notifies existing catalog consumers', () => {
    const { page, createAcademicGrade } = setup(); const changed = vi.fn(); page.catalogChanged.subscribe(changed);
    page.grade(' 2° '); expect(createAcademicGrade).toHaveBeenCalledWith({ name: '2°', level: 'Primaria' });
    expect(changed).toHaveBeenCalledOnce();
  });
  it('updates grade by ID without sending level or changing references', () => {
    const { page, createAcademicGrade, updateAcademicGrade } = setup(); page.selectGrade(); page.grade('1° grado');
    expect(updateAcademicGrade).toHaveBeenCalledWith('grade-id', '1° grado'); expect(createAcademicGrade).not.toHaveBeenCalled();
  });
  it('keeps section edit identity and shows prefix protection failures', () => {
    const { page, createAcademicSection, updateAcademicSection } = setup(); page.selectSection(); page.section('B', 'grade-id');
    expect(updateAcademicSection).toHaveBeenCalledWith('section-id', 'B'); expect(createAcademicSection).not.toHaveBeenCalled();
    expect(page.failed()).toContain('conservar la letra');
  });
  it('rejects missing parents and prevents writes after failed catalog loading', () => {
    const good = setup(); good.page.section('A'); expect(good.createAcademicSection).not.toHaveBeenCalled();
    expect(good.page.failed()).toContain('grado');
    const failed = setup(true); failed.page.grade('2°'); expect(failed.createAcademicGrade).not.toHaveBeenCalled();
  });
});
