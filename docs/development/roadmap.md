# Roadmap de Paideia

## Prioridad vigente: entrega BI/IA y consolidación

Solicitud integral posterior a `a6495ce`; sustituye la prioridad B3/C7 y la
prohibición anterior de push/merge. Respaldo local: `backup/pre-bi-ai-a6495ce`.
Fetch realizado: desarrollo remoto `3c3a87b`, main remoto `49a2f28`; 21 commits
locales anteriores preservados. No hay ERS originales disponibles.

| Bloque | Estado | Prioridad / dependencia | Aceptación / pruebas |
| --- | --- | --- | --- |
| REQ-24–28: BI con cobertura, filtros, tendencias y asistencia | PG/API, Angular y navegador probados; integración IA pendiente | P0; ámbito académico probado | API PG con cero/null/pesos históricos/ACL cruzada, Angular y navegador, sin alterar 32 notas |
| REQ-29–32: features históricas y datos demostrativos | Pendiente | P0; BI y aislamiento | Semilla determinista, cursos/periodos, sin datos personales ni fuga temporal, separación de alumnos |
| Modelo local experimental y evaluación | Pendiente | P0; dataset suficiente | Baseline/logística, métricas reales y limitaciones sintéticas; artefacto seguro, no entrenamiento pesado en request |
| Versiones, aprobación, activación y rollback | Pendiente | P0; modelo candidato | Persistencia PG, concurrencia, auditoría y permisos; modo institucional bloqueado sin validación |
| Panel IA e integración BI | Pendiente | P0; contratos anteriores | Demostración visible, estados honestos, cobertura/modelo/fecha, Playwright esencial |
| GitHub: auditoría, push, PR, CI y squash | Pendiente | P0; aceptación BI/IA completa | Revisar árbol e historial saliente; CI obligatorio; no squash con bloqueo; backup y main verificado |
| Auditoría ordinaria B3 y variantes secundarias | Diferido | P2 | Conservar funciones; no ampliar ERP antes de entrega principal |

Pendientes institucionales: objetivo/horizonte/umbrales de IA, calidad mínima,
criterios opcionales y precedencia de fórmulas/pesos. No se inventan políticas;
los resultados experimentales no habilitan decisiones oficiales.

Evidencia vigente: [BI/IA](../bi/validacion-bi-ia.md). BI: 7/7 PG, 46/46 Vitest,
build y Playwright esencial/móvil; 32 notas idénticas. Continuación: IA local
temporal demostrativa, versiones y aprobación, luego panel e integración BI.

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

| Tarea / fuentes | Estado comprobado | Prioridad / dependencia | Aceptación y pruebas necesarias |
| --- | --- | --- | --- |
| A. Importación institucional y cierre visual 4B.3–4B.5; REQ-39–44, EV-A–I, EX-A–E | PostgreSQL/API y recorrido esencial Playwright probados | P0; RAM y laboratorio saludables | Playwright: XLSX, corrección/confirmación, competencia/criterio/orden/estado/peso/fórmula/preview, borrador/publicación/restauración, matriz explícita, consulta e historia estable; conservar las 21 notas |
| B1. REQ-04/33: consultas/resúmenes/reportes/exportación por rol y ámbito | PG/API y regresión visual por roles probados para alcance corregido | P0; independiente si A bloqueada | Docente solo cursos de su sección asignada; coordinador/director lectura coherente con UI; alumno/apoderado solo vínculos; pruebas positivas/negativas de listas, agregados, XLSX y fichas |
| B2. REQ-15: integridad de UUID/componentes/fechas de notas | Probado en PG: relaciones/componentes/fechas manuales y PATCH | P0; B1 | Rechazo 404/422 de relación/fecha inválida sin cambiar notas/snapshot; PG/API con entidades válidas/ajenas/inexistentes |
| B3. HI-A/REQ-17: auditoría y conservación de historia | Snapshot/importación/versiones probados; cambios/borrados ordinarios parciales | P0; B1 y política de conservación | Registrar actor/antes/después sin datos sensibles públicos; no borrar historia por acciones ordinarias; pruebas transaccionales y permisos, migración aditiva si necesaria |
| C1. REQ-20/35/38: evidencia insuficiente y resúmenes coherentes | PG/API, Vitest, build y recorrido visual focalizado probados | P1; B1 | Distinguir falta de evidencia/cero válido; usar snapshots en ponderación existente; no inventar fórmula oficial; backend/frontend/exports con conjunto vacío y cero |
| C2. REQ-12/13, UX-A: matriz persistida y guardado claro | PG/API, Vitest, build y navegador de matriz probados | P1; A/B2 | Cargar contexto exacto sin sobrescribir borrador; reintento no duplica; filtros existentes + evaluación; pruebas API y navegador |
| C3. REQ-21: asistencia | PG/API, Vitest, build y navegador probados para registro diario | P1; B1 | Validar estados existentes, fechas/relaciones; PRESENT/ABSENT/LATE y atajos conservados; errores/reintentos visibles, fechas independientes y observaciones conservadas |
| C4. REQ-07/22: grados, secciones, años y periodos | Periodos y altas/etiquetas de grados/secciones PG/UI probados; archivo/traslado pendientes | P1; B1/B2 | Gestión autorizada y fechas coherentes sin regenerar códigos/identidades; migraciones aditivas solo si hacen falta; PG/API + UI focalizada |
| C5. REQ-02/05: usuarios y estado de cuenta | PG/API, Vitest, build y navegador de cuentas probados | P1; B1 | Desactivar/reactivar preserva relaciones; cuenta inactiva no autentica; no borrar usuarios con historia; pruebas JWT/roles/migración |
| C6. REQ-08: matrículas académicas | Altas/consulta PG/API y UI probadas; edición de estado UI pendiente | P2; C4/B1 | Asociación alumno/curso/periodo, acceso consistente; validar duplicados y matrícula activa sin matrícula financiera |
| C7. REQ-01/03/06: estudiantes/docentes/usuarios/roles | Flujos básicos probados; variantes parciales | P2; B1/C5 | Conservar seis roles, códigos/búsquedas/estado/asignaciones; no agregar documento personal sin requisito confirmado; pruebas de transiciones y ámbito |
| C8. REQ-16/18/19: observaciones/acuerdos/reuniones | Fecha/autor/categorías PG y cronología UI probados; versiones de contenido B3 pendientes | P2; B1/B3 | Mostrar fecha/autor/categoría autorizados; conservar edición y categorías; fixture historial y UI |
| C9. Portal estudiante/apoderado existente | Vínculos, lectura y regresión visual por alumno/apoderado probados | P0 en seguridad / P2 UX; B1 | Sin acceso a alumno ajeno ni escritura de notas; conservar portal aunque alcance excluya portal completo; pruebas por vínculo |
| C10. REQ-34/36/37: ficha/grupo/XLSX/impresión | Admin probado; roles/paginación parciales | P1/P2; B1/C1 | Datos y ámbitos idénticos en pantalla/exportación; conservar PDF de navegador; no asumir requisito de endpoint PDF separado |
| D. REQ-11/23/42, UX-B: UX y accesibilidad | Parcial | P2; corregir primero fallos de A/B/C | Formularios, errores accionables, carga/vacíos, filtros/tablas/búsqueda/paginación, responsive/teclado; componentes existentes y tests por recorrido |
| E1. Dependencias y CI | Locks, comandos y YAML locales probados; auditoría dev y CI remoto pendientes | P1/P2; hitos A–D | Builds seriales, tests focalizados e integración; revisar avisos conocidos sin audit fix --force; CI local validado, remoto sin push autorizado no comprobable |
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
- B1/C9: Playwright pasó docente/coordinador/director/estudiante/apoderado. Docente
  ve exclusivamente las 11 notas del curso visual asignado; lectura y POST de curso
  ajeno rechazados. Coordinador/director consultan y descargan XLSX. Familias ven un
  alumno vinculado y sus notas; ficha de alumno ajeno/API usuarios rechazadas, ruta
  de administración redirige al portal. Cero errores JS y 32 notas exactas conservadas.
  Cuentas nuevas y vínculos exclusivamente sintéticos; asignación del curso controlado
  `SYN-UI-4B` se vinculó al docente sintético, sin sobrescribir asignaciones ajenas.
  Credenciales/estado privados: `academic-roles-ui.state.json`. Ámbitos cruzados de
  curso/sección siguen acreditados por las pruebas PG; el navegador no repite todas
  las combinaciones de esas fixtures.
- Tarea activa: C4, eliminar el año fijo y permitir gestión de periodos con fechas
  coherentes y protección de notas/asistencias existentes. Grados/secciones y otras
  variantes de C4 siguen pendientes; no declarar el catálogo completo por este bloque.
- C4-periodos: 41/41 PG en 78,99 s (13 casos de calendario + relaciones/fechas de notas,
  asistencia y dos regresiones XLSX). Después 2/2 en 7,65 s: nuevo caso de edición de
  calendario concurrente con inserción de nota y repetición necesaria del caso de alta
  concurrente tras ajustar la prueba. Calendario editable por admin, legible por seis
  roles, nombres duplicados/fechas/null rechazados. Cambiar fechas no puede excluir
  notas/asistencias; nota/manual/Excel/asistencia toman bloqueo compartido de periodo
  para que una edición concurrente valide también sus escrituras ya confirmadas.
  Catálogo incluye periodos de otros años en orden cronológico, conservando identidades.
  Auditoría de altas/ediciones; no DELETE ni política de archivo nueva. Sin migración.
- Frontend C4: 22/22 Vitest, tres de periodos, build 25,253 s; operaciones seriales y
  caché/cap 768 MiB. Formulario admin en Cursos: fechas claras, errores accionables,
  carga/reintento, edición por ID, catálogo actualizado. Playwright period pasó:
  inversión rechazada antes de enviar, alta/edición sintética 2027, 422 al intentar
  excluir notas del calendario original y conservación de sus fechas y las 32 notas.
  Periodo nuevo/evidencia privados en `academic-ui.state.json`; no se aplicó ningún
  cambio al calendario original ni a la instalación institucional.
- Siguiente segura: C3/D, feedback de errores y guardado de asistencia en UI; la API
  ya valida fechas/estados pero el formulario existente omite los errores de POST.
  Después continuar grados/secciones de C4 y matrículas, sin declarar producción ni
  resolver por cuenta propia las decisiones institucionales pendientes de B3/fórmulas.
- C3/D completado para registro diario: 14/14 PG en 27,99 s, incluida observación
  conservada cuando el POST no envía `remarks` y borrado explícito solo con null.
  Angular tipa el registro confirmado, guarda secuencialmente, muestra errores y avance
  parcial, bloquea doble envío/carga fallida, ignora respuestas de fechas anteriores
  y distingue consulta sin registros de presencia. Coordinación/dirección solo lectura.
  28/28 Vitest (seis nuevas de asistencia), build 29,511 s con caché y cap 768 MiB.
  Primer build detectó contrato `unknown`; corregido y segundo build aprobado.
  Playwright attendance pasó: 422 visible sin escritura, tres estados, reintento con
  mismos IDs, fecha nueva sin arrastre, recarga y 32 notas idénticas. Se corrigieron
  dos selectores del verificador; intentos previos no se cuentan como evidencia válida.
  Cero errores JS; huella de notas `e7998edc2fb51a66ea381f2e15207f45e6e7502df0ac29664dbe66e96f92a1b5`.
- Próxima verificación focalizada: carrera de dos POST diarios de asistencia; después
  continuar C4-grados/secciones, preservando códigos e identidades existentes.
- C3 concurrencia: las dos solicitudes simultáneas pasaron antes del cambio, pero
  el flujo consulta/INSERT todavía admitía una carrera de primera escritura. Ahora
  PostgreSQL serializa por identidad alumno/curso/fecha, coherente con la restricción
  única existente y sin incluir periodo en esa identidad. 4/4 PG en 10,97 s: creación
  y actualización concurrentes con mismo ID, observaciones conservadas y prueba
  determinista de espera por el bloqueo transaccional. Sin migración ni cambio UI;
  no se repitió el build ni el recorrido visual por este cambio exclusivo de API.
- Siguiente tarea segura: C4-grados/secciones; documentar validaciones de generación
  de códigos existentes y no regenerar códigos al editar etiquetas del catálogo.
- C4-grados/secciones: nueve casos PG distintos aprobados (8/8 en 16,17 s y nuevo
  caso de integración con códigos 1/1 en 5,87 s). Admin crea grados/secciones y edita
  etiquetas; otros cinco roles rechazados. Reutiliza `student_code_prefix`: niveles,
  número y letra compatibles con el generador actual. Una edición conserva el prefijo
  escolar y no mueve secciones entre grados ni modifica códigos/IDs del padrón.
  Altas duplicadas serializadas en PG; auditoría de actor e ID. Sin migración/DELETE.
  Integración probó alumno nuevo `2P001` y código estable tras editar etiqueta.
  No se definieron rangos institucionales nuevos ni reglas de traslado/archivo.
- UI C4: admin en Cursos, formulario de altas/etiquetas, carga/reintento y errores
  explícitos. 32/32 Vitest (cuatro nuevos del gestor), build 28,178 s, caché/cap 768 MiB.
  Playwright cohort pasó altas/ediciones, 409 al cambiar número escolar y recarga:
  padrón y 32 notas idénticos, cero errores JS. Fixture `99° sintético UI revisado` /
  `SYN-UI-REV` sin alumnos, asignaciones o notas; no representa oferta institucional.
  Estado privado permite reanudar sin recrear ni borrar esas entidades.
- Continuación prioritaria independiente: C6, gestión visible de matrículas existentes
  por alumno/curso/periodo y protección de duplicados concurrentes. Conservar alcance
  por docente/rol, identidades y notas; no añadir matrículas financieras ni borrado.
- C6: ocho casos PG nuevos aprobados. Primera ejecución 12/15 aprobados (incluye
  nueve regresiones de autorización); tres fallaron por elegir en la prueba una
  identidad ya matriculada o un curso autorizado. Corregidas las fixtures, esos tres
  pasaron 3/3 en 9,62 s. Después 3/3 en 10,34 s: dos casos nuevos de estado vacío/null
  rechazados y repetición de normalización de ACTIVE tras el cambio de esquema.
  Filtros alumno/curso/periodo conservan ámbito correlacionado; alta concurrente produce
  un 201 y un 409, identidad existente preservada. Normaliza espacios/mayúsculas,
  manteniendo los estados no vacíos existentes sin inventar enum institucional.
- C6 UI: ficha del alumno muestra matrículas, alta de asociación activa con curso/
  periodo explícitos, lectura para director y creación para roles autorizados por API;
  errores, carga/reintento, respuestas de ficha anterior ignoradas y duplicados locales
  bloqueados. Cursos archivados conservan su nombre en la consulta. Sin eliminación
  ni modificación de estados en este formulario; endpoints anteriores se conservan.
  37/37 Vitest (cinco nuevos), build 31,868 s con caché/cap 768 MiB. Playwright enrollment
  pasó alta/409/reload con mismo ID, padrón y 32 notas intactos, cero errores JS.
  Se añadió una matrícula exclusivamente sintética al alumno/curso del recorrido UI.
- Siguiente tarea: C8/REQ-19, cronología visible con fecha y autor del seguimiento;
  conservar categorías, identidad y atribución. No ejecutar borrados ordinarios ni
  definir conservación/retención sin política. B3, fórmulas y producción siguen pendientes.
- C8/REQ-19: 14/14 PG en 30,38 s (cinco nuevos y nueve regresiones de ámbitos).
  DTO expone fecha original y nombre del usuario autor mediante join autorizado;
  filtro por alumno, orden cronológico y desempate estable. Cuatro categorías
  existentes probadas; edición conserva fecha y autor originales. Entrada legada
  sin autor permanece desconocida, sin atribución inventada; portal familiar no
  obtiene acceso nuevo al seguimiento. No se exponen email/credenciales del autor.
- C8 UI: fecha/autor legibles, carga/error/reintento del grupo, respuesta de grupo
  anterior ignorada y edición sin reabrir un estado existente cerrado. Edición fija
  el estudiante y conserva las categorías. Dirección no ofrece edición/borrado
  rechazados por su rol API; sus funciones de creación/consulta siguen disponibles.
  42/42 Vitest (cinco nuevos), build 25,808 s con caché/cap 768 MiB. Playwright followup
  pasó registro/fecha/autor/edición/recarga; mismo ID, fecha, atribución y estado.
  Entrada nueva exclusivamente sintética, sin borrados; 32 notas idénticas.
  Esto no acredita versiones del texto ni resuelve B3/retención por mostrar cronología.
- Siguiente bloque independiente: E1, comprobar que CI incorpora estas pruebas y
  versiones fijadas, con validación local focalizada y sin push/ejecución remota.
  B3 permanece pendiente: conservar antes/después es un alcance técnico posible;
  la política institucional debe definir archivo, borrado y duración de retención.
- E1: workflow frontend ejecuta los componentes antes del build, un trabajador y
  heap 512 MiB; conserva Node 24 y lockfile. Workflow backend añade lint de servicios,
  esquemas y diez archivos de regresión académica desde su directorio correcto.
  Ambos tokens CI solo necesitan lectura de contenido. YAML/orden/flags y comandos
  Ruff existentes/nuevos pasaron localmente; formato de una cadena SQL de prueba
  corregido sin cambio semántico. Los comandos frontend ya pasaron en el build 42/42;
  no se volvió a compilar ni ejecutar la suite de 92 por editar estos workflows.
  CI remoto no ejecutado: no hubo push/merge. La receta PostgreSQL de CI pertenece
  al runner remoto; no se levantó un segundo laboratorio ni su Compose en esta laptop.
- Recuento de evidencia: **110 casos PG distintos aprobados por bloques** (94 nuevos,
  16 regresiones de historia/revisiones/XLSX). `--collect-only` confirmó 110 en 4,92 s
  sin ejecutar otra vez los casos. No equivalen a una ejecución conjunta nueva de 110
  ni incluyen como extras los reintentos. Frontend final: 42/42 y build 25,808 s.
  Playwright pasó diez etapas académicas y los verificadores de cuentas/reportes y
  cinco roles. 32 notas actuales; las 21 iniciales y sus snapshots siguen idénticos.
- Punto de continuidad conservado al límite de esta ejecución: **B3**, diseñar e
  implementar captura aditiva de antes/después de correcciones ordinarias de notas
  y seguimiento, con actor y ámbito autorizados, pruebas PG en UUID y preservación
  de las 32 notas. No reconstruir valores previos desconocidos ni habilitar eliminación
  de historia o políticas de retención no confirmadas. Después C7/D (variantes por rol,
  estados/búsquedas/paginación), C10 y dependencias dev. El nombre de alumno inactivo
  en cronología aún puede caer al UUID por el catálogo activo; corregir sin ampliar
  ámbitos. Producción, CI remoto, archivo/traslados y reglas de cálculo siguen pendientes.
