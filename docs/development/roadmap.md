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
| A. Importación institucional y cierre visual 4B.3–4B.5; REQ-39–44, EV-A–I, EX-A–E | PostgreSQL/API probado; Angular compilado; interfaz parcial | P0; RAM y laboratorio saludables | Playwright: XLSX, corrección/confirmación, competencia/criterio/orden/estado/peso/fórmula/preview, borrador/publicación/restauración, matriz explícita, consulta e historia estable; conservar las 21 notas |
| B1. REQ-04/33: consultas/resúmenes/reportes/exportación por rol y ámbito | Parcial; fugas documentadas en summary | P0; independiente si A bloqueada | Docente solo cursos de su sección asignada; coordinador/director lectura coherente con UI; alumno/apoderado solo vínculos; pruebas positivas/negativas de listas, agregados, XLSX y fichas |
| B2. REQ-15: integridad de UUID/componentes/fechas de notas | Parcial; fecha manual/PATCH pendiente | P0; B1 | Rechazo 404/422 de relación/fecha inválida sin cambiar notas/snapshot; PG/API con entidades válidas/ajenas/inexistentes |
| B3. HI-A/REQ-17: auditoría y conservación de historia | Snapshot/importación/versiones probados; cambios/borrados ordinarios parciales | P0; B1 y política de conservación | Registrar actor/antes/después sin datos sensibles públicos; no borrar historia por acciones ordinarias; pruebas transaccionales y permisos, migración aditiva si necesaria |
| C1. REQ-20/35/38: evidencia insuficiente y resúmenes coherentes | Parcial; faltantes aún pueden parecer cero/riesgo | P1; B1 | Distinguir falta de evidencia/cero válido; usar snapshots en ponderación existente; no inventar fórmula oficial; backend/frontend/exports con conjunto vacío y cero |
| C2. REQ-12/13, UX-A: matriz persistida y guardado claro | Lista probada, matriz parcial | P1; A/B2 | Cargar contexto exacto sin sobrescribir borrador; reintento no duplica; filtros existentes + evaluación; pruebas API y navegador |
| C3. REQ-21: asistencia | Registro/idempotencia diaria probados; estados/periodos parciales | P1; B1 | Validar estados existentes, fechas/relaciones; PRESENT/ABSENT/LATE y atajos conservados; fixtures con repetición y rechazo de valores desconocidos |
| C4. REQ-07/22: grados, secciones, años y periodos | Catálogo probado; administración parcial/año fijo | P1; B1/B2 | CRUD autorizado y fechas coherentes sin regenerar códigos/identidades; migraciones aditivas solo si hacen falta; PG/API + UI focalizada |
| C5. REQ-02/05: usuarios y estado de cuenta | Alta/login probados; desactivación parcial | P1; B1 | Desactivar/reactivar preserva relaciones; cuenta inactiva no autentica; no borrar usuarios con historia; pruebas JWT/roles/migración |
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
- Siguiente tarea activa: A, recorrer UI con fixture nueva, sin modificar las 21 notas.
