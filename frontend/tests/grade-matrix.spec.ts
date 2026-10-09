import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, Subject, throwError } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';

import { ApiService, EvaluationRevision, GradeRecord } from '../src/app/core/services/api.service';
import { ConfirmService } from '../src/app/core/services/confirm.service';
import { GradesPage } from '../src/app/features/grades/grades.page';

class Matrix extends GradesPage {
  configure(name = 'Contexto') {
    this.gradeId = 'grade'; this.sectionId = 'section'; this.courseId = 'course'; this.periodId = 'period';
    this.academicBimester = 1; this.evaluationBlock = 1; this.evaluationName = name; this.assessmentDate = '2026-04-01';
    this.activeRevision.set({ id: 'published', state: 'published', configuration: { criteria: [
      { key: 'first', name: 'Primero', weight: 9, block: 1, position: 1, is_active: true },
      { key: 'second', name: 'Segundo', weight: 1, block: 1, position: 2, is_active: true },
    ] } } as EvaluationRevision);
    this.loadMatrix();
  }
  score(key: string) { return this.scores[`student:${key}`]; }
  edit(key: string, value: number) { this.scores[`student:${key}`] = value; }
  save() { this.saveAll(); }
  refresh() { this.loadMatrix(); }
  averageScore() { return this.average('student'); }
  failed() { return this.matrixError(); }
}

const records = () => [
  { id: 'first-id', student_id: 'student', evaluation_criterion_key: 'first', score: 0, assessment_weight: 3, qualitative_note: 'Nota propia uno' },
  { id: 'second-id', student_id: 'student', evaluation_criterion_key: 'second', score: 20, assessment_weight: 1, qualitative_note: 'Nota propia dos' },
] as GradeRecord[];

function setup() {
  let stored = records();
  const listGrades = vi.fn(() => of(stored));
  const createGrade = vi.fn((payload) => {
    const created = { ...payload, id: 'new-id', assessment_weight: 9 } as GradeRecord;
    stored = [...stored, created]; return of(created);
  });
  const updateGrade = vi.fn((id, payload) => {
    stored = stored.map((record) => record.id === id ? { ...record, ...payload } : record);
    return of(stored.find((record) => record.id === id)!);
  });
  const injector = Injector.create({ providers: [
    { provide: ApiService, useValue: { listGrades, createGrade, updateGrade,
      getAcademicCatalog: () => of({ students: [{ id: 'student' }], grades: [], sections: [], courses: [], periods: [], literal_scale: [] }),
    } }, { provide: ConfirmService, useValue: {} },
  ] });
  return { page: runInInjectionContext(injector, () => new Matrix()), listGrades, createGrade, updateGrade,
    empty: () => { stored = []; } };
}

describe('persisted grade matrix', () => {
  it('hydrates zeros with captured weights and leaves unchanged notes untouched', () => {
    const { page, createGrade, updateGrade } = setup(); page.configure();
    expect(page.score('first')).toBe(0); expect(page.averageScore()).toBe(5);
    page.save(); page.save();
    expect(createGrade).not.toHaveBeenCalled(); expect(updateGrade).not.toHaveBeenCalled();
  });

  it('edits by ID, preserves each qualitative note and retries without duplicating', () => {
    const { page, createGrade, updateGrade } = setup(); page.configure();
    page.edit('second', 15); page.save(); page.save();
    expect(updateGrade).toHaveBeenCalledTimes(1);
    expect(updateGrade).toHaveBeenCalledWith('second-id', { score: 15, qualitative_note: undefined });
    expect(createGrade).not.toHaveBeenCalled();
  });

  it('does not overwrite a local edit when refreshing the same context', () => {
    const { page } = setup(); page.configure(); page.edit('first', 8); page.refresh();
    expect(page.score('first')).toBe(8);
  });

  it('retains a successful insert identity before a retry', () => {
    const { page, empty, createGrade, updateGrade } = setup(); empty(); page.configure();
    page.edit('first', 14); page.save(); page.save();
    expect(createGrade).toHaveBeenCalledTimes(1); expect(updateGrade).not.toHaveBeenCalled();
  });

  it('rejects stale responses from a different evaluation context', () => {
    const { page, listGrades } = setup();
    const old = new Subject<GradeRecord[]>(); const latest = new Subject<GradeRecord[]>();
    listGrades.mockReturnValueOnce(old).mockReturnValueOnce(latest);
    page.configure('Anterior'); page.configure('Actual'); latest.next([]); old.next(records());
    expect(page.score('first')).toBeUndefined();
  });

  it('blocks writes after a failed load instead of assuming an empty evaluation', () => {
    const { page, listGrades, createGrade } = setup();
    listGrades.mockReturnValueOnce(throwError(() => new Error('Unavailable')));
    page.configure(); page.edit('first', 15); page.save();
    expect(page.failed()).toBe(true); expect(createGrade).not.toHaveBeenCalled();
  });

  it('blocks an ambiguous stored criterion instead of choosing an arbitrary grade', () => {
    const { page, listGrades, updateGrade } = setup();
    listGrades.mockReturnValueOnce(of([records()[0], { ...records()[0], id: 'duplicate' }]));
    page.configure(); page.edit('first', 15); page.save();
    expect(page.failed()).toBe(true); expect(updateGrade).not.toHaveBeenCalled();
  });

  it('does not resurrect a removed grade with an unsaved local edit', () => {
    const { page, empty, createGrade } = setup(); page.configure(); page.edit('first', 15);
    empty(); page.refresh(); page.save();
    expect(page.failed()).toBe(true); expect(createGrade).not.toHaveBeenCalled();
  });

  it('retries only remaining writes after a partially successful batch', () => {
    const { page, empty, createGrade } = setup(); empty(); page.configure();
    const insert = createGrade.getMockImplementation()!;
    createGrade.mockImplementationOnce(insert).mockImplementationOnce(() => throwError(() => ({ error: { detail: 'Temporary failure' } })));
    page.edit('first', 14); page.edit('second', 15); page.save(); page.save();
    expect(createGrade.mock.calls.map(([payload]) => payload.evaluation_criterion_key)).toEqual(['first', 'second', 'second']);
  });
});
