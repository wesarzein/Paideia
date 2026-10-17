import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of } from 'rxjs';
import { describe, expect, it } from 'vitest';
import { ApiService, GradeRecord } from '../src/app/core/services/api.service';
import { ConfirmService } from '../src/app/core/services/confirm.service';
import { GradesPage } from '../src/app/features/grades/grades.page';
import { ReportsPage } from '../src/app/features/reports/reports.page';
import { academicNote } from '../src/app/shared/academic-presentation';

class Grades extends GradesPage {
  seed(rows: Partial<GradeRecord>[]) { this.grades.set(rows as GradeRecord[]); }
  averageAt(month: number) { return this.monthlyAverage('s', month); }
  simulatedAt(month: number) { return this.monthlySynthetic('s', month); }
}
class Reports extends ReportsPage {
  selection() { return [this.month, this.bimesterNumber()]; }
}
const catalog = { grades: [], sections: [], courses: [], students: [], literal_scale: [],
  periods: [{ id: 'period', name: '2026', starts_on: '2026-01-01', bimester_months: { '8': 3, '9': 3 } }] };
function injector() { return Injector.create({ providers: [
  { provide: ApiService, useValue: { getAcademicCatalog: () => of(catalog) } },
  { provide: ConfirmService, useValue: {} },
] }); }
describe('monthly historical evidence', () => {
  it('omits generated import annotations while preserving teacher observations', () => {
    const original = { data_origin: 'synthetic', qualitative_note: 'Historia mensual simulada; calendario corregido. No es una nota oficial.' };
    expect(academicNote(original.qualitative_note, original.data_origin)).toBe('');
    expect(academicNote('Dato sintético del III bimestre; no es una nota oficial.', 'synthetic')).toBe('');
    expect(academicNote('Dato sintético basado en el III bimestre; no es una nota oficial.', 'synthetic')).toBe('');
    expect(academicNote('Reforzar comprensión lectora.', 'synthetic')).toBe('Reforzar comprensión lectora.');
    expect(academicNote(original.qualitative_note, 'recorded')).toBe(original.qualitative_note);
    expect(original.qualitative_note).toContain('simulada');
  });
  it('keeps zero, captured weights and synthetic identity without inventing dates', () => {
    const page = runInInjectionContext(injector(), () => new Grades());
    page.seed([{ student_id: 's', academic_month: 8, score: 0, assessment_weight: 3, data_origin: 'excel' },
      { student_id: 's', academic_month: 8, score: 20, assessment_weight: 1, data_origin: 'synthetic' }]);
    expect(page.averageAt(8)).toBe(5); expect(page.simulatedAt(8)).toBe(true);
    expect(page.averageAt(7)).toBeNull();
  });
  it('opens the latest available report month and reads its recorded bimester', () => {
    const page = runInInjectionContext(injector(), () => new Reports());
    expect(page.selection()).toEqual(['2026-09', 3]);
  });
});
