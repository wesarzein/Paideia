/** Navigation and route access share the same institutional responsibilities. */
export const moduleRoles: Record<string, string[]> = {
  dashboard: ['admin', 'teacher', 'coordinator'],
  usuarios: ['admin'],
  estudiantes: ['admin'],
  'grados-secciones': ['admin'],
  cursos: ['admin', 'teacher'],
  calificaciones: ['teacher'],
  asistencia: ['teacher'],
  seguimiento: ['coordinator'],
  analitica: ['teacher', 'coordinator'],
  ia: ['coordinator'],
  reportes: ['teacher', 'coordinator'],
  importacion: ['admin', 'teacher'],
};

export const roleLabels: Record<string, string> = {
  admin: 'Administrador', teacher: 'Docente', coordinator: 'Área académica',
};
