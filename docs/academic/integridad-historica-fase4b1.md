# Fase 4B.1: configuración histórica de calificaciones

Alcance autorizado: corregir el recálculo silencioso causado por cambios de ponderación. Referencias: [auditoría 4A](auditoria-fase4a.md), [matriz EV-I/REQ-35](auditoria-fase4a-matriz.md) y [evaluación configurable](evaluacion-configurable-y-auditoria.md). Los demás hallazgos permanecen pendientes. No se modifican el importador Excel, competencias, fórmulas configurables, IA/BI ni permisos.

## Causa comprobada

`GET /grades/monthly-summary` calculaba `sum(score * component.weight) / sum(component.weight)` mediante una unión con los componentes vigentes. Cinco notas 10, 10, 10, 10 y 20, con pesos 1, promediaban 12,00. Cambiar el primer peso a 3 daba 11,43, sin editar ninguna nota. La reproducción automatizada ejecuta esa consulta antigua y la nueva sobre los mismos registros sintéticos.

## Corrección

Cada `GradeRecord` conserva dos campos obligatorios y de solo lectura en la API:

- `assessment_weight`: peso utilizado por la consulta histórica.
- `assessment_config`: copia independiente con `schema_version=1`, algoritmo `weighted_mean_v1`, ID y nombre originales del componente, opcionalidad, peso y procedencia (`record_insert` o `legacy_migration`). El curso, periodo y fecha siguen asociados a la nota; `created_at` identifica el registro. No se afirma que exista ya una versión completa de configuración por curso/periodo.

`weighted_mean_v1` identifica la fórmula existente: suma de notas por sus pesos dividida entre suma de pesos, redondeada a dos decimales en la respuesta. Se conserva el comportamiento anterior cuando todos los pesos son cero, y la clasificación literal vigente; esta fase no inventa reglas académicas ni congela nuevas fórmulas o umbrales todavía no configurables.

El promedio mensual consulta exclusivamente `assessment_weight`, sin unir pesos vigentes. Renombrar, cambiar pesos/opcionalidad o desactivar un componente no cambia las notas existentes ni su copia de configuración. Las notas **nuevas** capturan el peso vigente al guardarse. Las notas sin componente conservan peso 1, como antes; un peso 0 se conserva como 0. Esto también protege las inserciones del importador sin cambiar su código ni resolver sus brechas de mapeo/idempotencia.

Un evento ORM captura la configuración en cada inserción y rechaza cambios posteriores. PostgreSQL añade un trigger que realiza la captura autoritativa, también para INSERT directo/bulk, y bloquea cambios a cualquiera de los dos campos históricos. La lectura del componente usa `FOR SHARE` para coordinarse con actualizaciones concurrentes. Todo ocurre en la misma transacción; un fallo no deja una nota parcialmente guardada.

Se conservan las correcciones explícitas de puntaje, fecha, texto y asociación al componente mediante los endpoints y permisos existentes. Cambiar la asociación **no sustituye el peso ni la configuración originales**: `component_id` refleja la asociación actual y `assessment_config.component_id` la base original del cálculo. Corregir puntajes, fechas o añadir notas puede cambiar deliberadamente el promedio; esta protección se refiere a cambios de configuración, no a congelar el conjunto completo de notas.

No existe un estado formal de consolidación/cierre en el modelo actual. Se protege toda nota guardada, sin inventar fechas de cierre. No se ofrece un endpoint para recapturar pesos históricos. Un futuro recálculo requerirá autorización, previsualización, actor/motivo y versiones de resultados que conserven el anterior. Al incorporar competencias/fórmulas deberá evolucionar `schema_version` y el evaluador, manteniendo la interpretación de `weighted_mean_v1` y las copias existentes.

## Migración y límites

Nueva revisión: `0012_grade_assessment_snapshot`, posterior a `0011_evidence_types`.

1. Añade campos inicialmente anulables.
2. Completa las notas existentes con el peso/configuración **disponibles al migrar**; usa una unión izquierda para incluir notas sin componente.
3. Declara los campos obligatorios y crea el trigger de protección.

No elimina filas ni modifica notas, IDs, relaciones o fechas de creación/modificación. Se verificó esa conservación con datos sintéticos de la revisión 0011. La migración y el backfill son transaccionales en PostgreSQL. Un segundo `upgrade head` no recaptura configuración.

**Límite histórico:** no hay evidencia para recuperar pesos originales que hayan cambiado antes de esta migración. `legacy_migration` distingue explícitamente esos registros; se congela el resultado consultable al momento de migrar, sin presentarlo como reconstrucción del pasado.

**Despliegue pendiente:** no se ejecutó la migración institucional ni se reconstruyeron/reiniciaron sus servicios. El backend nuevo requiere el esquema 0012; no desplegarlo sobre 0011. La migración puede bloquear escrituras mientras añade columnas y completa registros: requiere ventana coordinada, respaldo verificado y autorización separada. Revisar cantidad de notas, pesos existentes, revisión real y muestras autorizadas antes de aplicarla. Mantener el arranque sin migraciones automáticas. Tras migrar, reconstruir el backend y comparar notas/relaciones y promedios contra las evidencias previas.

El downgrade se rechaza expresamente: quitar estos campos destruiría evidencia histórica. Planificar la reversión antes del despliegue; restaurar un respaldo puede perder escrituras posteriores y requiere autorización. El código anterior tolera las columnas adicionales, pero su consulta mantiene el defecto: no constituye una solución de integridad.

## Validación aislada

Proyecto Docker exclusivo `paideia-phase4b1-tests`, imagen `paideia-phase4b1-tests-backend`. PostgreSQL 17 en tmpfs, red interna sin puertos publicados ni volumen institucional. La fixture valida host, usuario y nombre de base; cada prueba de persistencia migra un esquema sintético independiente. No usa alumnos ni notas reales.

Pruebas nuevas en `backend/tests/unit/test_grade_assessment_history.py`:

| Prueba | Evidencia esperada |
| --- | --- |
| Defecto original y evaluaciones nuevas | Consulta antigua 11,43; histórica corregida 12,00; nueva evaluación 11,43; renombrado/desactivación no alteran copias |
| Corrección explícita de nota/asociación | Cambia el puntaje solicitado; conserva el peso y configuración originales; campos extra del cliente no los sustituyen |
| Protección PostgreSQL y rollback | UPDATE directo de peso/JSON rechazado; transacción revertida y datos intactos |
| Protección ORM y rollback | Cambio de configuración rechazado sin guardar una modificación de puntaje realizada en la misma transacción |
| Ceros, notas sin componente e INSERT directo | Se guardan puntaje 0, peso 0 y peso 1 sin componente; trigger captura configuración |
| Permisos existentes | Docente no puede cambiar pesos; coordinador no puede registrar notas |
| Compatibilidad con registros 0011 | IDs, relaciones, puntajes y timestamps iguales; pesos 3/0/1 conservados; promedio 11,25 estable tras cambiar peso a 9 y repetir upgrade |

Se recrea la instancia API y sus conexiones para comprobar lectura persistente. **No equivale a reiniciar PostgreSQL**: el tmpfs perdería su contenido al detenerlo; no se presenta como prueba nueva de reinicio de servicios. La prueba con volumen sintético de 4A conserva su evidencia previa.

Resultado final ejecutado: **59 pruebas aprobadas** (52 previas y 7 nuevas), con 31 advertencias de deprecación de FastAPI/Starlette/Alembic, sin fallos. Además, **16 pruebas del padrón aprobadas en SQLite en memoria**, conservando la cobertura previa sin conectarse a PostgreSQL para ese ensayo. La cadena de migraciones desde una base vacía también terminó correctamente. Ruff pasó para la migración y ambas pruebas afectadas; `git diff --check` pasó. El primer intento de la prueba de reproducción tenía una unión SQLAlchemy ambigua; se corrigió el test y la ejecución completa posterior es la evidencia válida.

Protección institucional comprobada con `app.inspect_database` en transacción `REPEATABLE READ, READ ONLY`: las 15 tablas conservan conteos, huellas de contenido y esquema respecto de la referencia privada posterior a la recuperación. La revisión institucional sigue siendo `0011_evidence_types`. No se publicaron filas ni huellas individuales. Los commits locales `1d346eb` y `d013dba` permanecen conservados; no se hizo push ni merge.

Archivos modificados/añadidos:

- `backend/app/models/academic.py`: campos históricos y captura/protección ORM.
- `backend/app/endpoints/grades.py`: promedio mensual con pesos guardados.
- `backend/app/schemas/grades.py`: exposición de la base de cálculo en respuestas, sin campos de escritura.
- `backend/migrations/versions/0012_grade_assessment_snapshot.py`: backfill y protección PostgreSQL.
- `backend/tests/unit/test_grade_assessment_history.py`: siete pruebas focalizadas de integración/persistencia.
- `backend/tests/unit/test_roster_persistence.py`: fixture permite partir de revisión 0011 para ensayar compatibilidad; conserva sus controles de aislamiento y pruebas anteriores.
- `docs/academic/evaluacion-configurable-y-auditoria.md`: enlace de contexto a esta corrección.
- Este documento: causa, alcance, resultados, reproducción y condiciones de despliegue.

Reproducción desde la raíz del repositorio, eligiendo un nombre de proyecto nuevo si este ya contiene resultados:

```powershell
$env:PAIDEIA_TEST_IMAGE = 'paideia-phase4b1-tests-backend'
docker compose --env-file .env.test.example -p paideia-phase4b1-tests -f docker-compose.tests.yml build tests
docker compose --env-file .env.test.example -p paideia-phase4b1-tests -f docker-compose.tests.yml run migrate
docker compose --env-file .env.test.example -p paideia-phase4b1-tests -f docker-compose.tests.yml run tests
```

No usar `.env` institucional ni el Compose de producción para estos comandos. No se requieren borrados, reset, `down -v`, push o merge.

Quedan fuera de esta corrección: historial de ediciones/borrados de puntajes, mapeo Excel, homogeneizar promedios simples de reportes con promedios ponderados, validaciones de asociación ya señaladas en 4A, configuración completa por periodo y UI de versiones. Las vistas que ya calculaban promedios simples se conservan y no consultan pesos mutables.
