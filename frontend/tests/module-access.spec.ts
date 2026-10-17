import { describe, expect, it } from 'vitest';
import { moduleRoles, roleLabels } from '../src/app/core/module-access';

const modulesFor = (role: string) => Object.keys(moduleRoles).filter(key => moduleRoles[key].includes(role));

describe('institutional module responsibilities', () => {
  it('gives teachers grading tools and administrators assignments', () => {
    expect(modulesFor('teacher')).toEqual(['dashboard', 'cursos', 'calificaciones', 'asistencia', 'analitica', 'reportes', 'importacion']);
    expect(modulesFor('admin')).toEqual(['dashboard', 'usuarios', 'estudiantes', 'grados-secciones', 'cursos', 'importacion']);
  });
  it('gives the academic area follow-up and analysis without editing academic records', () => {
    expect(modulesFor('coordinator')).toEqual(['dashboard', 'seguimiento', 'analitica', 'ia', 'reportes']);
    expect(modulesFor('director')).toEqual([]);
    expect(roleLabels['coordinator']).toBe('Área académica');
  });
});
