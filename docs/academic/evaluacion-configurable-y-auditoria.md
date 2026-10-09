# Contexto técnico y plan de auditoría: evaluación configurable

## Estado y alcance autorizado

Requisito funcional incorporado por el responsable el 08/10/2026: **sistema de evaluación flexible y configurable por curso y periodo académico**.

Este documento es una referencia para futuras sesiones de Codex. En esta fase solo se documenta el requisito y su auditoría futura: no autoriza cambios funcionales, migraciones, importaciones reales ni modificaciones de calificaciones. Continúan siendo prioritarios el entorno colaborativo y el despliegue. Antes de implementar, auditar lo existente y conservar las implementaciones que funcionen, incluidas capacidades adicionales no enumeradas aquí.

## Contexto institucional y fuente de referencia

Actualmente todos los cursos utilizan el mismo formato Excel institucional y los mismos criterios predeterminados. Las calificaciones existentes están en Excel externos; cero calificaciones en PostgreSQL puede ser normal y no constituye por sí solo un error o evidencia de pérdida.

El formato institucional será la configuración predeterminada, pero no un límite rígido a la personalización autorizada. Las evaluaciones mantienen exámenes cada cuatro semanas y bimestres de ocho semanas. No deducir fechas de calendario, pesos, umbrales o reglas de cierre sin confirmación institucional.

La auditoría debe utilizar el **Excel real proporcionado por el responsable** para comprobar hojas, encabezados, celdas combinadas, nombres exactos de criterios, fórmulas, referencias, redondeos y estructura. No asumir otro formato ni convertir resúmenes previos en reglas verificadas. Ese archivo no se abrió ni validó en esta tarea documental. Su revisión posterior debe ser privada y no implica autorización para importar notas reales. Las pruebas versionadas utilizarán una réplica sintética de la estructura comprobada, sin identidades de estudiantes.

## Requisito funcional

Los docentes autorizados deben poder:

1. Agregar, editar, reordenar y desactivar competencias y criterios de evaluación.
2. Configurar los pesos o ponderaciones de cada criterio.
3. Personalizar las fórmulas de notas, promedios y resultados bimestrales.
4. Elegir la plantilla institucional predeterminada o una configuración personalizada para su curso y periodo académico.
5. Previsualizar los resultados de las fórmulas antes de guardar cambios de configuración.
6. Restablecer la configuración institucional cuando corresponda, respetando permisos e historial.
7. Importar Excel mediante la interfaz de arrastrar y soltar, respetando el formato institucional y las personalizaciones válidas del curso y periodo seleccionados.
8. Revisar y corregir las calificaciones importadas en una previsualización; revalidarlas y confirmar antes de persistirlas.
9. Consultar los resultados correctos después de guardar, con acceso autorizado a la configuración y los datos persistidos.

La previsualización de fórmulas/configuración y la revisión de calificaciones importadas son dos verificaciones necesarias; una no sustituye a la otra.

## Reglas y garantías

- **Organización académica:** respetar bloques de cuatro semanas y bimestres de ocho semanas, incluida la relación entre criterios, evaluaciones, curso y periodo.
- **Ponderaciones:** validar en el servidor y presentar reglas claras al docente. Confirmar antes de implementar la escala, la suma exigida o normalización, los pesos permitidos y el tratamiento de criterios opcionales o desactivados. No inventar una regla de suma igual a 1 o a 100 si no está confirmada.
- **Fórmulas seguras:** admitir únicamente expresiones y operaciones autorizadas y validadas. No ejecutar código arbitrario, `eval`/`exec`, macros o acceso al sistema mediante fórmulas. Auditar referencias inexistentes, ciclos, división por cero, resultados no finitos y límites de complejidad. Las reglas académicas para vacíos, ceros y redondeos deben comprobarse con el Excel y la institución.
- **Persistencia y aislamiento:** configuraciones almacenadas en PostgreSQL, disponibles para usuarios autorizados y asociadas al curso y periodo correspondientes. Un cambio no debe propagarse involuntariamente a otros cursos, periodos o usuarios.
- **Permisos institucionales:** validar autorización en backend, incluido el acceso al curso/sección y las restricciones del periodo. No basta con ocultar opciones en el frontend.
- **Trazabilidad y versiones:** registrar quién cambió qué y cuándo; conservar versiones de criterios, orden, ponderaciones y fórmulas. Auditar la asociación de cada resultado histórico con la configuración que le corresponde.
- **Historia académica:** cambios posteriores y restauraciones de plantilla no deben sobrescribir silenciosamente notas, resultados históricos o versiones anteriores. Cualquier recálculo histórico requiere un proceso explícito, autorizado y trazable; su política queda por confirmar.
- **Importación controlada:** adaptar/mapeear columnas contra la configuración válida seleccionada, permitir corrección en borrador y revalidar en backend. Cancelar o previsualizar no guarda notas; confirmar persiste con control transaccional y sin duplicados por reintentos.
- **Conservación funcional:** mantener filtros, pantallas, configuraciones adicionales y funciones existentes que estén verificadas. No reemplazar módulos completos por asumir que faltan estas capacidades.

## Plan de auditoría futura en tareas pequeñas

| Tarea | Verificación y evidencia esperada |
| --- | --- |
| A1. Inventario existente | Localizar UI, API, modelos, migraciones y pruebas de competencias, criterios, pesos y cálculos. Registrar ruta/línea y estado, sin dar por funcional una capacidad solo por encontrar código. |
| A2. Excel institucional | Revisar privadamente el archivo real, identificar nombres/fórmulas/estructura exactos y documentar únicamente información no personal. Crear posteriormente una réplica sintética equivalente para pruebas. |
| A3. Configuración y permisos | Verificar altas, edición, orden, desactivación, ámbito curso/periodo, plantilla predeterminada, personalización y restablecimiento con usuarios permitidos y denegados. |
| A4. Ponderaciones y fórmulas | Confirmar reglas pendientes; comprobar validación, previsualización, resultados, redondeos y rechazo de expresiones inseguras. Comparar la plantilla predeterminada con el Excel real. |
| A5. Persistencia y versiones | Comprobar PostgreSQL, lectura desde otra sesión autorizada, conservación tras reinicio, trazabilidad, versiones y ausencia de cambios involuntarios en otros cursos o historiales. |
| A6. Importación configurable | Probar arrastrar/soltar, identificación y mapeo de criterios institucionales y personalizados, revisión editable, revalidación, cancelación, confirmación, errores y duplicados. |
| A7. Consulta y regresión | Verificar que resultados guardados y consultas coincidan con la versión aplicable; conservar filtros y capacidades adicionales. Usar datos sintéticos en flujos completos. |
| A8. Brechas y correcciones | Entregar evidencia y un plan incremental para conservar, reparar o implementar solo lo necesario. Obtener autorización para la implementación y para cualquier uso de datos reales. |

Puntos de partida para A1, **pendientes de auditoría funcional de este requisito**:

- `backend/app/models/academic.py` y `backend/migrations/versions/`: persistencia académica y componentes de evaluación.
- `backend/app/endpoints/courses.py`, `grades.py` e `imports.py`: configuración, notas e importación.
- `backend/app/core/academic_rules.py` y `backend/app/services/evidence_types.py`: reglas y catálogo de evidencias.
- `frontend/src/app/features/courses/courses.page.ts`, `grades/grades.page.ts`, `imports/imports.page.ts` y `frontend/src/app/core/services/api.service.ts`: interfaz y contratos.
- `backend/tests/unit/` y `frontend/tests/`: cobertura existente que debe revisarse antes de ampliar pruebas.

No se afirma en este documento que competencias, reordenación, fórmulas personalizadas, versionado o importación adaptable estén implementados o hayan pasado pruebas.

## Entrega de la auditoría

La primera ejecución quedó registrada en [auditoria-fase4a.md](auditoria-fase4a.md), con [matriz de cumplimiento](auditoria-fase4a-matriz.md) y resultados de pruebas sintéticas. Esta referencia conserva el requisito original; los hallazgos no autorizan todavía correcciones, migraciones institucionales ni importaciones reales.

Para cada capacidad, registrar `VERIFICADO`, `PARCIAL`, `NO IMPLEMENTADO` o `NO VERIFICADO`, con evidencia, prueba ejecutada, limitaciones, decisiones institucionales pendientes y tarea de corrección pequeña. Separar lo comprobado en código de lo probado en ejecución. La auditoría y cualquier implementación posterior no incluyen IA ni BI salvo autorización independiente.
