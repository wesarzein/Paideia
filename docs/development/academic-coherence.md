# Consulta de notas y coherencia de interfaz — 10/10/2026

Las notas importadas estaban guardadas. La consulta anterior filtraba por el mes
actual y ocultaba los registros de agosto/septiembre. Además, Computación no tenía
componentes activos, por lo que la pantalla ocultaba la matriz y el listado aunque
existían notas con criterios y pesos capturados.

Calificaciones consulta todo el periodo seleccionado, ofrece las evaluaciones
guardadas por nombre/fecha/bimestre/bloque y carga automáticamente la más reciente.
La matriz recupera los criterios de las notas existentes cuando el curso no tiene
componentes configurados; cada celda conserva su ID, observación y peso histórico.
Se eliminaron los filtros de mes y tipo de evidencia técnico. Los campos de nombre,
fecha, bimestre y bloque solo aparecen al crear una evaluación nueva. El listado
completo del periodo queda dentro de un desplegable.

El catálogo incluye inicio y fin del periodo. Importación usa ese calendario y ya
no solicita el año por separado. Las fechas fuera del periodo se detectan antes de
cargar el Excel. El encabezado muestra nombre (o correo), rol traducido e icono.

El usuario eligió conservar asistencia por curso. Se añadió fecha destacada,
navegación anterior/siguiente y Hoy, propuesta de periodo según la fecha únicamente
si hay una coincidencia, selección automática de curso únicamente si hay uno, y
observación editable por alumno para permisos/retiros. Las observaciones se leen
del registro y se envían al upsert existente; refrescar el mismo contexto conserva
ediciones locales. No se añadieron estados ni se inventaron reglas para permisos.

Validación: 26 pruebas frontend (matriz, importación y asistencia), 30 pruebas
PostgreSQL (autorización, filtros exactos y asistencia diaria), compilación Angular.
Recorrido real de consulta en el laboratorio: 240 notas de Computación, tres
evaluaciones existentes, matriz de 16 alumnos/80 notas por evaluación, nombre/rol
en encabezado, 16 campos de observación y navegación de fecha. Viewport móvil
390 px; cero errores JavaScript y cero escrituras en ese recorrido. Durante la
sesión aparecieron 80 notas nuevas además de las 170 anteriores; no se borraron ni
se reinterpretaron. No presentar esas notas de fechas distintas como duplicados.
Backend y frontend actualizados únicamente en `paideia-dev-phase4b3ui`, puerto 14211.
