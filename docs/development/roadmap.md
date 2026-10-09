# Roadmap de Paideia

Actualizado: 09/10/2026, America/Lima. Rama de trabajo:
`dev/phase4b5-academic-stabilization`. Inicio verificado: `7984ad4`, Git limpio.

Fuentes: [README](../../README.md), [alcance](../../PROJECT_SCOPE.md),
[arquitectura](../../ARCHITECTURE.md), [matriz 4A](../academic/auditoria-fase4a-matriz.md),
[requisito configurable](../academic/evaluacion-configurable-y-auditoria.md),
[validación segunda laptop](../academic/validacion-segunda-laptop-fase4b.md).
No se encontraron ERS/backlog originales; los IDs REQ/HU proceden de la matriz y no
acreditan acceso a originales ausentes. No volver a pedir documentación que ya existe.

Estados: **probado** = evidencia ejecutada para el alcance indicado; **implementado** =
código sin ejecución suficiente; **parcial** = funcionalidad o validación incompleta;
**pendiente** = trabajo no realizado. Los resultados históricos de la matriz no
describen automáticamente el código posterior: se actualizan con evidencia focalizada.

## Orden y aceptación

| Tarea / fuentes | Estado real inicial | Prioridad / dependencia | Aceptación y pruebas necesarias |
| --- | --- | --- | --- |
| A. Importación institucional y cierre visual 4B.3–4B.5; REQ-39–44, EV-A–I, EX-A–E | PostgreSQL/API y recorrido esencial Playwright probados | P0; RAM y laboratorio saludables | Playwright: XLSX, corrección/confirmación, competencia/criterio/orden/estado/peso/fórmula/preview, borrador/publicación/restauración, matriz explícita, consulta e historia estable; conservar las 21 notas |
| B1. REQ-04/33: consultas/resúmenes/reportes/exportación por rol y ámbito | Probado en PG para endpoints corregidos; regresión UI por roles pendiente | P0; independiente si A bloqueada | Docente solo cursos de su sección asignada; coordinador/director lectura coherente con UI; alumno/apoderado solo vínculos; pruebas positivas/negativas de listas, agregados, XLSX y fichas |
| B2. REQ-15: integridad de UUID/componentes/fechas de notas | Probado en PG: relaciones/componentes/fechas manuales y PATCH | P0; B1 | Rechazo 404/422 de relación/fecha inválida sin cambiar notas/snapshot; PG/API con entidades válidas/ajenas/inexistentes |
| B3. HI-A/REQ-17: auditoría y conservación de historia | Snapshot/importación/versiones probados; cambios/borrados ordinarios parciales | P0; B1 y política de conservación | Registrar actor/antes/después sin datos sensibles públicos; no borrar historia por acciones ordinarias; pruebas transaccionales y permisos, migración aditiva si necesaria |
| C1. REQ-20/35/38: evidencia insuficiente y resúmenes coherentes | PG/API, Vitest, build y recorrido visual focalizado probados | P1; B1 | Distinguir falta de evidencia/cero válido; usar snapshots en ponderación existente; no inventar fórmula oficial; backend/frontend/exports con conjunto vacío y cero |
| C2. REQ-12/13, UX-A: matriz persistida y guardado claro | PG/API, Vitest, build y navegador de matriz probados | P1; A/B2 | Cargar contexto exacto sin sobrescribir borrador; reintento no duplica; filtros existentes + evaluación; pruebas API y navegador |
| C3. REQ-21: asistencia | Estados/periodos/idempotencia probados; tasas sin cambios | P1; B1 | Validar estados existentes, fechas/relaciones; PRESENT/ABSENT/LATE y atajos conservados; fixtures con repetición y rechazo de valores desconocidos |
| C4. REQ-07/22: grados, secciones, años y periodos | Catálogo probado; administración parcial/año fijo | P1; B1/B2 | CRUD autorizado y fechas coherentes sin regenerar códigos/identidades; migraciones aditivas solo si hacen falta; PG/API + UI focalizada |
| C5. REQ-02/05: usuarios y estado de cuenta | PG/API, Vitest, build y navegador de cuentas probados | P1; B1 | Desactivar/reactivar preserva relaciones; cuenta inactiva no autentica; no borrar usuarios con historia; pruebas JWT/roles/migración |
| C6. REQ-08: matrículas académicas | API/seed implementados; UI parcial | P2; C4/B1 | Asociación alumno/curso/periodo, acceso consistente; validar duplicados y matrícula activa sin matrícula financiera |
| C7. REQ-01/03/06: estudiantes/docentes/usuarios/roles | Flujos básicos probados; variantes parciales | P2; B1/C5 | Conservar seis roles, códigos/búsquedas/estado/asignaciones; no agregar documento personal sin requisito confirmado; pruebas de transiciones y ámbito |
| C8. REQ-16/18/19: observaciones/acuerdos/reuniones | Registro/atribución probados; cronología UI parcial | P2; B1/B3 | Mostrar fecha/autor/categoría autorizados; conservar edición y categorías; fixture historial y UI |
| C9. Portal estudiante/apoderado existente | Vínculos y lectura probados en 4A; regresión pendiente | P0 en seguridad / P2 UX; B1 | Sin acceso a alumno ajeno ni escritura de notas; conservar portal aunque alcance excluya portal completo; pruebas por vínculo |
| C10. REQ-34/36/37: ficha/grupo/XLSX/impresión | Admin probado; roles/paginación parciales | P1/P2; B1/C1 | Datos y ámbitos idénticos en pantalla/exportación; conservar PDF de navegador; no asumir requisito de endpoint PDF separado |
| D. REQ-11/23/42, UX-B: UX y accesibilidad | Parcial | P2; corregir primero fallos de A/B/C | Formularios, errores accionables, carga/vacíos, filtros/tablas/búsqueda/paginación, responsive/teclado; componentes existentes y tests por recorrido |
| E1. Dependencias y CI | Locks/entornos probados; auditoría dev y CI remoto parciales | P1/P2; hitos A–D | Builds seriales, tests focalizados e integración; revisar avisos conocidos sin audit fix --force; CI local validado, remoto sin push autorizado no comprobable |
| E2. Despliegue/backups/recuperación | Recuperación histórica probada; producción pendiente | P1; B/C/E1 y autorización externa | Secretos/TLS/servidor/backup cifrado/restauración/monitoreo/rollback verificados; no declarar producción lista por healthcheck |
| F. REQ-24–32: IA/BI | Interfaces informativas; procesamiento pendiente | P2 diferida; módulos principales estables | Refinar diseños existentes sin servicios externos, claves/costos o nuevas reglas; no habilitar ahora |

## Decisiones institucionales

- Opcionales incompletos, parciales y precedencia de fórmulas/ponderaciones: pendientes.
  Fórmulas configurables permanecen en preview; no activar cálculo oficial ambiguo.
- Recálculo histórico y conservación/retención: aclarar antes de recalcular/eliminar.
- Campos personales adicionales y eventual PDF dedicado: requieren requisito preciso.
- Destino institucional/producción: respaldo y autorización separada; fuera del laboratorio.

## Ejecución y continuidad

1. Revisar solo evidencia/código de la siguiente tarea, verificar RAM y destino efectivo.
2. Trabajar en un alcance comprobable; pruebas destructivas en esquemas UUID.
3. Registrar resultados reales, limitaciones y commit. No repetir las 92 pruebas previas.
4. Actualizar estado y pasar a la siguiente tarea segura. Si A está bloqueada por RAM,
   avanzar B1 con pruebas ligeras; no bloquear tareas independientes por políticas ambiguas.

Laboratorio único: `config/local/phase4b3ui.env` + `docker-compose.environment.yml`.
Conservar 21 notas iniciales. `scripts/verify_academic_lab_api.py` valida su destino;
no ejecutar sus etapas iniciales import/configuration sobre datos ya poblados.

## Registro de esta ejecución

- Inicio: commits `b156d12` y `7984ad4`, Git limpio; servicios sintéticos saludables.
- RAM inicial: aproximadamente 2,29 GiB libres; cierre visual viable con una página Edge.
- A: el navegador detectó 422 al previsualizar con un criterio desactivado. Corregido
  filtrando muestras activas; 2/2 Vitest (incluye regresión real de componente) y build
  Angular aprobado en 21,501 s con caché, un trabajador y límite 768 MiB.
  `frontend/vitest.config.ts` permite decoradores Angular en la prueba JIT.
- El frontend corregido está publicado únicamente en el laboratorio local. El
  reintento de Edge se bloqueó antes de arrancar por RAM menor a 1,5 GiB.
- Reanudación A: `config/local/browser-venv/Scripts/python.exe -B
  scripts/verify_academic_ui.py`; conserva evidencia privada y el curso `SYN-UI-4B`.
  Sus etapas editor/import/manual/history pueden reanudarse sin reset del laboratorio.
- Tarea activa independiente mientras A esté bloqueada: B1, predicados compartidos de
  ámbito y pruebas PostgreSQL con cursos/secciones cruzados y cuentas familiares.
- B1: 24/24 pruebas PostgreSQL en 41,28 s: nueve de autorización nuevas, siete de
  revisiones/API, siete de snapshots y una de importación docente. Esquemas UUID;
  no se escribieron datos de trabajo en public. Correlación curso+grado+sección en
  notas/asistencia/matrículas/dashboard/reportes; summary de alumno y XLSX limitados
  al ámbito; catálogos familiares limitados a vínculos; coordinador/director pueden
  leer los reportes que ya ofrece su navegación. Seguimientos sin filas duplicadas.
- Ruff completo pasó para servicio/tests nuevos; endpoints legados comprobados con
  exclusión explícita de B008/E501/E701/E702 preexistentes. No se afirma lint global.
- Siguiente independiente: B2, relaciones/fechas en creación y edición de notas.

- B2: 27/27 PostgreSQL en 48,27 s: 13 casos nuevos de contexto y 14 regresiones
  de historia/revisiones. Fechas inclusivas del periodo, UUID inexistentes, componentes
  ajenos/inactivos y null explícito rechazados sin escrituras; cero real y corrección
  de nota con componente archivado conservan snapshots. Sin migración nueva.

- C3: 22/22 PostgreSQL en 38,55 s: 13 casos de asistencia y nueve de autorización.
  PRESENT/ABSENT/LATE y normalización preservados; estados desconocidos y fechas
  ajenas al periodo rechazados sin modificar filas; reintentos conservan ID diario.
  No se cambió la definición institucional de porcentajes. Sin migración nueva.
- A sigue bloqueada: el nuevo intento se detuvo en la salvaguarda de RAM, antes
  de arrancar Edge. Se avanzó con C5 (REQ-02/05) mientras faltaban recursos.
- C5: 16/16 PG en 38,73 s (nueve casos de cuentas + siete de historia). Migración
  0015 verificada desde 0014 y ciclo en UUID; cuenta inactiva rechaza login y JWT,
  DELETE compatible desactiva preservando identidad/vínculos, PATCH reactiva y
  registra actor/acción. Dos desactivaciones concurrentes conservan un admin activo.
  Frontend: seis Vitest (cuatro de cuentas), build Angular 30,972 s, caché/cap 768 MiB.
  UI ofrece estado y Desactivar/Reactivar; recorrido visual específico pendiente.
  Aplicación de 0015 en public del laboratorio comparó las 16 tablas antes/después
  (solo columna nueva/versionado permitido): se conservaron las 21 notas. Evidencia
  privada `config/local/account-status-migration.result.json`. No downgrade en public.
- Incidencia de secuencia: copia de backend desde caché se solapó brevemente con
  compilación Angular; ambas terminaron sin error. Mantener operaciones seriales.
- A: posteriormente la RAM permitió Edge. Pasaron editor, importación, registro manual
  y consulta tras recargar, publicación posterior, restauración e historial. Cero
  errores JavaScript. Se conservan las 21 notas iniciales y se añaden 11 exclusivamente
  al curso `SYN-UI-4B`: 32 en total. SHA-256 API final:
  `e911927a74824a9c870b05b138d44839faaa537139e4db1887b8abcc0d8fe500`.
  Se corrigió un selector del verificador (etiqueta de select incluye sus opciones);
  no fue un defecto del producto. Estado privado `academic-ui.state.json` completo.
- Siguiente: C1 (evidencia insuficiente/resúmenes); B3 conserva dependencia de política
  de retención/recalculo. No activar fórmulas como resultados oficiales. La seguridad
  de consultas está probada en API, pero falta regresión visual por rol y cuentas.
- Persistencia posterior a 0015 y al recorrido visual: reinicio exclusivo de PostgreSQL,
  inventario completo y 32 filas API idénticos. Diez notas originales conservan huella
  `062b5c8a74c0a6ce1dd400e2e875406382d658809fdf92c450cc372fba52f308`;
  inventario `cc557050beb465a21f51a42d1364657a6daee294fcc00eff62a8795172a79f40`.
  El verificador exige ahora head del backend en lugar de congelar 0014; el primer
  intento se rechazó antes del reinicio por ese guard antiguo, sin escribir datos.
- C1: 22/22 PG en 55,90 s (seis casos nuevos + permisos e historia), diez Vitest
  y build Angular 27,628 s. Promedios de referencia usan pesos capturados; falta
  de evidencia o denominador cero producen null, cero real sigue siendo cero.
  Conteos/pesos agregados alinean reporte grupal con backend; asistencia conserva
  la definición existente. Umbrales informativos de riesgo existentes se conservan;
  sin evidencia no se infiere ALTO/BAJO y evidencia parcial se marca INCOMPLETO
  salvo un factor observado que ya cumplía un umbral. Fórmulas siguen en preview.
  Reportes/XLSX/dashboard/summary probados; sin migraciones nuevas.
- Playwright de cuentas/reportes pasó: Desactivar/Reactivar, login inactivo denegado,
  Sin datos sin riesgo fabricado, error de red separado de vacío y reintento. Cero
  errores JS; 32 notas exactas conservadas. Cuenta sintética dedicada, credenciales
  solo en `config/local/reports-accounts-ui.state.json`; no perfil personal.
- Siguiente segura: C2, hidratación de matriz por contexto e identidad de edición;
  queda regresión visual de ámbitos por roles y política B3. No repetir builds
  ni recorridos aprobados salvo cambios que los afecten.
- C2: 26/26 PG en 44,37 s (cuatro consultas de contexto + permisos/contexto de escritura);
  19/19 Vitest, nueve de matriz, y build final 24,400 s. Contexto exacto de bimestre,
  bloque, nombre/tipo y fecha en GET; matriz hidrata notas, conserva peso histórico,
  edita por ID, omite cambios inexistentes y serializa guardado. Respuestas obsoletas,
  carga fallida, identidades ambiguas y eliminación con edición local bloquean escritura;
  reintento parcial conserva identidades ya insertadas. No reemplaza un borrador local
  al refrescar el mismo contexto. Observaciones de cada criterio se conservan salvo
  cambio explícito de la observación de fila. Sin migraciones nuevas.
- Playwright matrix pasó: carga de nota existente, dos PATCH al mismo ID (14→15→14),
  guardados sin cambios sin POST/PATCH, snapshot/revisión/observación estables y 31
  notas restantes exactas. Las 21 iniciales siguen intactas. Solo updated_at de la
  nota visual corregida cambió como consecuencia esperada; huella API actual:
  `e7998edc2fb51a66ea381f2e15207f45e6e7502df0ac29664dbe66e96f92a1b5`.
  El inventario anterior acredita el reinicio previo a esta corrección, no su timestamp nuevo.
- Siguiente P0: regresión visual por roles de B1/C9, sobre cuentas sintéticas y curso
  visual; no alterar notas iniciales. Después C4 (periodos/catálogos), con B3 aún sujeto
  a política de retención. Las reglas ambiguas de cálculo permanecen pendientes.
