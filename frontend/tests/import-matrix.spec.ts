import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, throwError } from 'rxjs';
import { describe, expect, it } from 'vitest';
import { ApiService, ImportPreview } from '../src/app/core/services/api.service';
import { PlaceholderPage } from '../src/app/features/imports/placeholder.page';

class ImportMatrix extends PlaceholderPage {
  configure() {
    this.mode.set('grades'); this.courseId = 'course'; this.periodId = 'period';
    this.gradeId = 'grade'; this.sectionId = 'section'; this.schoolYear = 2026; this.bimestre = 2;
    this.blocks = { '1': { evaluation_name: 'Primero', assessment_date: '2026-04-01' }, '2': { evaluation_name: 'Segundo', assessment_date: '2026-04-29' } };
    this.preview.set({ total: 2, columns: [], errors: [],
      institutional: { template: 'institutional_v1', sheet: 'Notas', blank_inputs: 8, warning: '', derived: [], unsupported_formula_rows: [],
        students: [{ source_row: 6, student_code: '1SA001', name: 'Alumno' }], blocks: [] },
      rows: ['1', '2'].map(block => ({ source_row: 6, source_sheet: 'Notas', source_block: block, evaluation_type: 'Cuaderno', student_code: '1SA001', score: 0 }))
    } as ImportPreview);
  }
  corrections() { this.correctionsOnly = true; }
  noDates() { this.blocks = {}; }
  students() { return this.matrixStudents(); }
  rows() { return this.preview()!.rows; }
  resolve() { this.resolveMatrixStudent(6, '1SA002'); }
  confirmed() { return this.studentConfirmed(6); }
  edit(block: string, criterion: string, value: number | null) { this.editMatrixScore(6, block, criterion, value); }
  errors() { return this.rowErrors(); }
  reviewNow() { this.reviewGrades(); }
  ready() { return this.reviewReady(); }
  commit() { this.importGrades(); }
  prepare() { this.prepareGradeSave(); }
  confirm() { this.confirmSave(); }
  dialog() { return this.confirmOpen(); }
  notice() { return { text: this.message(), kind: this.noticeKind() }; }
  summary() { return this.confirmationSummary(); }
  changeGroup() { this.changeSelection(); }
}

function setup(state: 'identical' | 'different' | 'review-error' | 'commit-error' = 'identical') {
  const calls: unknown[][] = [];
  const injector = Injector.create({ providers: [{ provide: ApiService, useValue: {
    getAcademicCatalog: () => of({ students: [], grades: [], sections: [], courses: [], periods: [], literal_scale: [] }),
    reviewGradeRows: (rows: unknown[]) => state === 'review-error' ? throwError(() => ({ error: { detail: 'Alumno no asignado' } })) : of({ rows: rows.map((_, index) => ({ row: index + 1, status: state === 'different' ? 'different' : 'identical', component_id: null, review_token: 'token' })), errors: [] }),
    commitGradeRows: (...args: unknown[]) => { calls.push(args); return state === 'commit-error' ? throwError(() => ({ error: { detail: 'La nota cambió desde la revisión' } })) : of({ imported: 0, updated: state === 'different' ? 2 : 0, skipped: state === 'different' ? 0 : 2, rejected: 0 }); },
  } }] });
  const page = runInInjectionContext(injector, () => new ImportMatrix()); page.configure();
  return { page, calls };
}

describe('institutional import matrix', () => {
  it('loads historical grades without individual evaluation dates', () => {
    const { page, calls } = setup(); page.noDates(); page.prepare(); expect(page.errors()).toEqual([]);
    expect(page.dialog()).toBe(true); page.confirm(); expect(calls[0][4]).toBe(false);
    expect((calls[0][3] as { historical: boolean }).historical).toBe(true);
  });
  it('groups criteria by pupil and confirms every related mark once', () => {
    const { page } = setup(); expect(page.students()).toHaveLength(1);
    page.resolve(); expect(page.confirmed()).toBe(true);
    expect(page.rows().every(row => row['student_code'] === '1SA002')).toBe(true);
  });
  it('preserves zero and edits a blank without duplicating a cell', () => {
    const { page } = setup(); page.edit('1', 'Módulo', 0); page.edit('1', 'Módulo', 15);
    expect(page.rows()).toHaveLength(3); expect(page.errors()).toEqual([]);
    page.edit('1', 'Módulo', null); expect(page.rows()).toHaveLength(2);
  });
  it('invalidates consent after edits and commits with corrections only', () => {
    const { page, calls } = setup(); page.reviewNow(); expect(page.ready()).toBe(true);
    page.edit('1', 'Cuaderno', 12); expect(page.ready()).toBe(false);
    page.commit(); expect(calls).toHaveLength(0);
    page.corrections(); page.reviewNow(); page.commit(); expect(calls[0][4]).toBe(true);
    expect((calls[0][3] as { historical: boolean }).historical).toBe(true);
  });
  it('reviews differences from the save button and commits only after final confirmation', () => {
    const { page, calls } = setup('different');
    page.prepare(); expect(page.dialog()).toBe(true); expect(calls).toHaveLength(0);
    expect(page.summary()).toContain('2 notas se actualizarán');
    page.confirm(); expect(calls).toHaveLength(1);
    expect((calls[0][0] as Record<string, unknown>[]).every(row => row['decision'] === 'update' && row['review_token'] === 'token')).toBe(true);
    expect(page.notice().kind).toBe('success'); expect(page.notice().text).toContain('2 actualizadas');
  });
  it('explains invalid scores and never submits them', () => {
    const { page, calls } = setup(); page.edit('1', 'Cuaderno', 21); page.prepare();
    expect(page.dialog()).toBe(false); expect(page.notice().kind).toBe('error'); expect(calls).toHaveLength(0);
  });
  it('shows review and commit errors without announcing success', () => {
    const first = setup('review-error'); first.page.prepare();
    expect(first.page.notice().text).toContain('Alumno no asignado'); expect(first.page.dialog()).toBe(false); expect(first.calls).toHaveLength(0);
    const second = setup('commit-error'); second.page.prepare(); second.page.confirm();
    expect(second.page.notice().kind).toBe('error'); expect(second.page.notice().text).toContain('No se guardaron cambios');
  });
  it('clears the file and stale review when changing the selected group', () => {
    const { page, calls } = setup('different'); page.prepare(); page.changeGroup();
    expect(page.dialog()).toBe(false); expect(page.ready()).toBe(false); page.commit(); expect(calls).toHaveLength(0);
  });
});
