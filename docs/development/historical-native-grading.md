# Historial bimestral y evaluaciones del sistema

Solicitud del usuario: sustituir el trabajo en hojas de cálculo por la gestión
académica del sistema. Excel carga bimestres anteriores; las evaluaciones nuevas
se registran con nombre, fecha, criterios, competencias y pesos publicados.

- Administrador: cursos, aulas, alumnos, periodos, asignaciones y configuración.
- Docente: sus cursos y aulas asignados; registro y corrección de calificaciones,
  asistencia, seguimiento, analítica, IA y reportes dentro de su ámbito.
- La configuración del docente procede únicamente de una versión publicada.
  No se presentan borradores ni la plantilla predeterminada como competencias
  institucionales existentes. Computación todavía requiere configuración real
  del administrador; no se inventaron ni publicaron competencias del colegio.
- La interfaz de configuración permite competencias, criterios y pesos, sin
  expresiones de Excel. Las configuraciones nuevas usan cálculo ponderado.
  Las configuraciones existentes conservan su cálculo hasta una elección
  explícita del administrador. Los opcionales vacíos no entran en el denominador.

## Persistencia

Migración aditiva 0019: `record_kind` distingue `evaluation` de
`historical_bimester`; fecha nullable únicamente para registros históricos con
bimestre y bloque. El historial no captura la configuración del curso vigente
ni se asocia automáticamente con sus componentes actuales. Reimportación
estable por alumno/curso/periodo/bimestre/bloque/criterio, usando nombres internos
deterministas y fecha null. Cambios de notas existentes requieren revisión y token.

La API de evaluaciones nuevas conserva fechas obligatorias. Las correcciones
históricas solo permiten notas y observaciones. Historial sin fecha participa
en indicadores del periodo; no se le asigna un mes ficticio. El portal y los
reportes admiten fecha null. Las características IA solo consideran historial
de periodos cerrados anteriores al periodo objetivo.

No se reinterpretaron registros anteriores: todas las 250 filas y snapshots del
laboratorio conservaron exactamente sus campos anteriores. SHA256 antes y
después, excluyendo la nueva columna:
`83d72e49ad21ab20917a8af49e6d47b1e78c955adbd8e0e3afeef8c10d6ad476`.
Respaldo privado previo en LocalAppData/Paideia/audit-phase4b3/historical-before.dump.
Solo se migró y desplegó `paideia-dev-phase4b3ui`, dirección 127.0.0.1:14211.

Los promedios de seguimiento son referencias de las notas registradas con pesos
capturados. No se presentan como cierre oficial cuando falta una regla
institucional o evidencia pendiente. Las evaluaciones antiguas conservan sus
criterios al publicarse otra configuración.

## Verificación

- PostgreSQL con esquemas UUID: carga de 160 notas históricas sin fechas, segunda
  carga sin duplicados, corrección revisada, configuración actual diferente del
  Excel antiguo, evaluación docente con fecha y peso capturado, denegación a otro
  docente, indicadores con historial sin fecha y validación de opcionales.
- Regresiones: 14 casos de historial/correcciones/política, 35 de contexto,
  versiones e indicadores y 21 de formato institucional/historial/características
  IA. Los grupos se solapan; no constituyen un conteo de casos únicos.
- Frontend: publicación de competencias y cálculo automático; docente consulta
  solo versión publicada; historial sin fecha se hidrata y corrige por ID;
  revisión, confirmación, errores y permisos de importación.
- Angular compilado. Playwright: Excel real de 16 alumnos/160 notas, revisión
  real sin fechas ni checkbox, configuración sin editor de fórmulas. Vista docente
  y dos escrituras de evaluación nueva comprobadas con respuestas controladas;
  esas escrituras fueron interceptadas, no agregaron notas ficticias al colegio.
  Permisos y persistencia docente se comprobaron realmente en PostgreSQL UUID.
  Cero errores JavaScript y 250 registros conservados.

Recorrido reproducible: `scripts/verify_historical_grades_ui.py`. Capturas privadas
en LocalAppData/Paideia/audit-phase4b3/historical-ui. No se publicaron credenciales,
tokens ni datos de alumnos en el repositorio.
