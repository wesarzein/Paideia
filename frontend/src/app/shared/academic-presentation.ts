/** Keep import provenance out of teacher observations without changing stored marks. */
export function academicNote(note: string | null | undefined, origin?: string): string {
  if (origin === 'synthetic' && /^(Dato sintético (?:del|basado en el) III bimestre;|Historia mensual simulada; calendario corregido\.)/.test(note ?? '')) {
    return '';
  }
  return note ?? '';
}

/** Friendly labels for the two original lab service accounts. */
export function accountDisplayName(name?: string): string {
  return ({
    'Administrador sintético': 'Administración',
    'Verificador sintético IA': 'Coordinación académica',
  } as Record<string, string>)[name ?? ''] ?? name ?? '';
}
