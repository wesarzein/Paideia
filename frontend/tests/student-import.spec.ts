import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, throwError } from 'rxjs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiService } from '../src/app/core/services/api.service';
import { PlaceholderPage } from '../src/app/features/imports/placeholder.page';

class StudentImport extends PlaceholderPage {
  upload() {
    this.setMode('students');
    this.gradeId = 'grade'; this.sectionId = 'section';
    this.lockContext();
    this.select({ target: { files: [{ name: 'registro.xlsx' }] } } as unknown as Event);
  }
  errors() { return this.rowErrors(); }
  save() { this.importStudents(); }
  text() { return this.message(); }
}

function setup(fail = false) {
  vi.stubGlobal('localStorage', { getItem: () => JSON.stringify({ role: 'admin' }) });
  const getAcademicCatalog = vi.fn(() => of({ students: [], grades: [], sections: [], courses: [], periods: [], literal_scale: [] }));
  const commitStudentRows = vi.fn(() => of({ imported: 16, updated: 0, skipped: 0, rejected: 0 }));
  const previewStudentImport = vi.fn(() => fail ? throwError(() => ({ error: { detail: { missing_columns: ['first_name', 'last_name'] } } })) : of({
    total: 1, columns: ['student_code', 'full_name', 'last_name', 'first_name'], errors: [],
    rows: [{ student_code: '1SA001', full_name: 'APELLIDO SINTETICO ALUMNO UNO', last_name: 'APELLIDO SINTETICO', first_name: 'ALUMNO UNO' }],
  }));
  const injector = Injector.create({ providers: [{ provide: ApiService, useValue: { getAcademicCatalog, commitStudentRows, previewStudentImport } }] });
  return { page: runInInjectionContext(injector, () => new StudentImport()), getAcademicCatalog, commitStudentRows };
}

afterEach(() => vi.unstubAllGlobals());
describe('student workbook upload', () => {
  it('imports a full-name roster without leaving required fields empty', () => {
    const { page, commitStudentRows, getAcademicCatalog } = setup();
    page.upload(); expect(page.errors()).toEqual([]); page.save();
    expect(commitStudentRows).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({ first_name: 'ALUMNO UNO', last_name: 'APELLIDO SINTETICO' })]), 'grade', 'section');
    expect(getAcademicCatalog).toHaveBeenCalledTimes(3);
    expect(page.text()).toContain('Ya puedes cargar este mismo Excel');
  });
  it('shows missing column details from the API and prevents a commit', () => {
    const { page, commitStudentRows } = setup(true);
    page.upload(); expect(page.text()).toContain('Faltan columnas: first_name, last_name');
    page.save(); expect(commitStudentRows).not.toHaveBeenCalled();
  });
});
